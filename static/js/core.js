/**
 * WaifuCore - 业务逻辑核心（稳定增强版）
 * - 分段拼装（可维护）
 * - 风格 Profile（自动加权 / 负面 / 质量覆盖）
 * - Prompt 长度预算裁剪
 * - 不改变对外接口
 */

import { DB } from './data.js';
// —— 风格 → 最大可接受细节表达（系统级）——
const STYLE_REALISM_HINT = {
  // 偏写实 / 半写实
  realistic: "rendered with realistic fabric texture, natural folds, and physically coherent shading",
  cinematic: "rendered with realistic fabric texture, natural folds, and physically coherent shading",

  // 插画 / 二次元主流
  anime: "rendered with high-detail anime-style fabric textures and clean, expressive folds",
  illustration: "rendered with stylized yet highly detailed fabric textures consistent with the illustration style",

  // 设计型 / 平涂 / Pop
  pop: "rendered with bold, clean shapes and high-detail stylized fabric patterns consistent with the art style",
  graphic: "rendered with sharp, graphic fabric shapes and stylized folds consistent with the design language",

  // 默认兜底
  default: "rendered with maximum detail appropriate to the chosen art style"
};
// —— 二次元宇宙：存在方式模板 ——
// 只用于“世界如何理解这个角色”，不是职业/身份
const EXISTENCE_TEMPLATES = {
  NATURAL_FANTASY_BEING: {
    prompt:
      "a naturally existing being in this world, whose appearance and abilities are inherent rather than symbolic"
  },

  SYMBOLIC_COMBAT_ENTITY: {
    prompt:
      "a symbolic combat entity whose attire and equipment follow stylized rules rather than real-world practicality"
  },

  DESIGNED_ENTITY: {
    prompt:
      "a deliberately designed entity whose appearance emphasizes visual impact and thematic coherence"
  }
};

function resolveExistenceTemplate(form) {
  // 1) 先吃“显式字段”（未来你加 weapon/pose 也能直接用）
  const weapon = String(form.weapon || "");
  const pose = String(form.pose || "");

  // 2) 再吃“你系统真实存在的字段”
  const clothingText = form.clothing && DB.CLOTHING?.[form.clothing]?.prompt
    ? String(DB.CLOTHING[form.clothing].prompt)
    : "";

  const actionText = form.action && DB.actions?.[form.action]
    ? String(DB.actions[form.action])
    : "";

  const effectText = form.effect && DB.effects?.[form.effect]
    ? String(DB.effects[form.effect])
    : "";

  // 合并成一个可检索的语义池（这才是你现在“武器绑定姿态”的真实来源）
  const pool = `${weapon} ${pose} ${clothingText} ${actionText} ${effectText}`.toLowerCase();

  // —— 1️⃣ 明确战斗符号（最高优先级）——
  if (/(sniper|rifle|gun|firearm|weapon)/i.test(pool) && /(aim|aiming|snipe|combat|attack|shoot)/i.test(pool)) {
    return "SYMBOLIC_COMBAT_ENTITY";
  }
  
  // —— 1.5️⃣ 冷兵器 + 战斗姿态（符号化战斗存在）——
  if (
    /(katana|scythe|blade|blades|sword|dual blades)/i.test(pool) &&
    /(ready to strike|iaido|mid-swing|slash|strike|wielding|menacing|combat|battle|stance)/i.test(pool)
  ) {
  return "SYMBOLIC_COMBAT_ENTITY";
}

  // —— 2️⃣ 轻装 + 武器（典型反差）——
  if (/(bikini|swimsuit|micro|lingerie|minimal|exposed)/i.test(pool) && /(sniper|rifle|gun|weapon)/i.test(pool)) {
    return "SYMBOLIC_COMBAT_ENTITY";
  }

  // —— 3️⃣ 高设计感造型 —— 
  if (/(high fashion|couture|concept|designed|visual design)/i.test(pool)) {
    return "DESIGNED_ENTITY";
  }

  // —— 4️⃣ 幻想现象（默认自然存在）——
  if (/(magic|spell|fantasy|animal ears|beast|demon|elf|fox ears|cat ears)/i.test(pool)) {
    return "NATURAL_FANTASY_BEING";
  }

  return "NATURAL_FANTASY_BEING";
}

export class WaifuCore {
  constructor(options = {}) {
    // ===== Prompt 长度软预算 =====
    this.maxChars = Number.isFinite(options.maxChars)
      ? options.maxChars
      : 2800;

    // ===== 基础质量词 =====
    this.qualityTagsBase = [
      "Masterpiece",
      "best quality",
      "ultra-detailed",
      "4k wallpaper",
      "intricate details",
      "professional lighting",
      "ray tracing"
    ];

    this.qualityTagsCloseUp = [
      "beautiful detailed eyes",
      "detailed eyelashes",
      "moist lips",
      "skin texture"
    ];

    // ===== 基础负面词 =====
    this.negativeTags = [
      "low quality",
      "bad anatomy",
      "worst quality",
      "text",
      "watermark",
      "blurry details",
      "mutated hands",
      "extra digits",
      // —— 单主体约束（关键）——
      "multiple people",
      "duplicate character",
      "extra person",
      "multiple characters",
      "split view",
      "inset portrait",
      "character repetition"
    ];

    // ===== 风格 Profile =====
    this.styleProfiles = {
      // 分类级（按 styles_*）
      category: {
        unique: {
          extraPositive: [
            "highly stylized",
            "strong art direction",
            "clean composition"
          ],
          negativeAdd: [
            "overexposed highlights",
            "washed out colors"
          ]
        },
        studio: {
          extraPositive: [
            "high production quality",
            "key animation feel",
            "consistent lineart"
          ],
          negativeAdd: [
            "inconsistent line weight"
          ]
        },
        master: {
          extraPositive: [
            "authorial style fidelity",
            "signature linework",
            "era-accurate rendering"
          ],
          negativeAdd: [
            "style mismatch"
          ]
        }
      },

      // 精确 key（优先级最高）
      exact: {
        "像素风 (Pixel Art)": {
          qualityOverride: [
            "pixel art",
            "16-bit",
            "limited palette",
            "dithering",
            "crisp pixels"
          ],
          extraPositive: [
            "sprite-like readability",
            "strong silhouette",
            "no anti-aliasing"
          ],
          negativeAdd: [
            "photorealistic",
            "ray tracing",
            "lens flare",
            "depth of field",
            "soft blur",
            "high-res textures"
          ]
        },

        "虚幻引擎5 (UE5 Render)": {
          qualityOverride: [
            "8k",
            "photorealistic",
            "cinematic lighting",
            "global illumination",
            "high dynamic range",
            "sharp focus"
          ],
          extraPositive: [
            "photorealistic",
            "cinematic lighting",
            "sharp details"
          ],
          negativeAdd: [
            "anime lineart",
            "cel shading",
            "flat colors"
          ]
        },

        "水墨画 (Ink Wash)": {
          qualityOverride: [
            "traditional ink wash painting",
            "sumi-e",
            "expressive brush strokes",
            "paper texture"
          ],
          extraPositive: [
            "minimalism",
            "negative space",
            "elegant composition"
          ],
          negativeAdd: [
            "3d render",
            "photorealistic skin",
            "ray tracing",
            "hard outlines",
            "neon lights"
          ]
        },

        "蒸汽波 (Vaporwave)": {
          extraPositive: [
            "vaporwave palette",
            "retro glow",
            "80s aesthetic",
            "soft gradients"
          ],
          negativeAdd: [
            "muddy colors",
            "color banding",
            "low contrast"
          ]
        },

        "厚涂 (Impasto)": {
          extraPositive: [
            "visible brush strokes",
            "paint texture",
            "impasto thickness"
          ],
          negativeAdd: [
            "flat shading",
            "smooth plastic skin"
          ]
        }
      }
    };
  }

  // ======================================================
  // 核心入口
  // ======================================================
  assemblePrompt(form) {
    const segments = [];
    const styleProfile = this.getStyleProfile(form.style);

    // 1. 风格 + 比例（关键）
    segments.push(this.buildStyleAndRatio(form, styleProfile));

    // 2. 镜头（关键）
    const shot = this.buildShot(form);
    if (shot) segments.push(shot);

    // 3. 主体（关键）
    segments.push(this.buildSubject(form));

    // 4. 服装与配饰（重要）
    const attire = this.buildAttire(form);
    if (attire) segments.push(attire);

    // 5. 动作 / 场景 / 特效（可裁剪）
    const action = this.buildAction(form);
    if (action) segments.push(action);

    const scene = this.buildScene(form);
    if (scene) segments.push(scene);

    const effect = this.buildEffect(form);
    if (effect) segments.push(effect);

    // 6. 用户补充（可裁剪）
    const custom = this.buildCustom(form);
    if (custom) segments.push(custom);

    // 7. 质量 & 负面（关键）
    segments.push(this.buildQuality(form, styleProfile));
    segments.push(this.buildNegative(styleProfile));

    // 预算裁剪
    const pruned = this.pruneByBudget(segments, this.maxChars);

    return pruned.join(" ").replace(/\s+/g, " ").trim();
  }

  // ======================================================
  // Style Profile helpers
  // ======================================================
  getStyleCategory(styleKey) {
    if (!styleKey || styleKey === "none") return "";
    if (DB.styles_unique?.[styleKey]) return "unique";
    if (DB.styles_studio?.[styleKey]) return "studio";
    if (DB.styles_master?.[styleKey]) return "master";
    return "";
  }

  getStyleProfile(styleKey) {
    const category = this.getStyleCategory(styleKey);
    const exact = styleKey ? this.styleProfiles.exact?.[styleKey] : null;
    const cat = category ? this.styleProfiles.category?.[category] : null;

    return {
      category,
      extraPositive: [
        ...(cat?.extraPositive || []),
        ...(exact?.extraPositive || [])
      ],
      negativeAdd: [
        ...(cat?.negativeAdd || []),
        ...(exact?.negativeAdd || [])
      ],
      qualityOverride: exact?.qualityOverride || null
    };
  }

  // ======================================================
  // Builders
  // ======================================================
  buildStyleAndRatio(form, styleProfile) {
    const ratioDesc =
      form.aspectRatio === "3:4"
        ? "tall vertical 3:4 aspect ratio"
        : "wide cinematic 16:9 aspect ratio";
  
    // 是否强调 anime（某些非二次元宇宙将来可以关掉）
    const visualLanguage = styleProfile?.qualityOverride
      ? "visual rendering"
      : "anime-style visual rendering";
  
    let base =
      `A scene depicted through a high-quality ${visualLanguage}, ` +
      `with a ${ratioDesc}`;
  
    if (form.style && form.style !== "none") {
      const styleDesc =
        DB.styles_master?.[form.style] ||
        DB.styles_studio?.[form.style] ||
        DB.styles_unique?.[form.style];
  
      if (styleDesc) {
        base += `, rendered in a style heavily inspired by ${styleDesc}`;
      }
    }
  
    // 句号 + 过渡，后面所有 buildXXX 都是 scene 的组成部分
    base += ".";
  
    return base;
  }  

  buildShot(form) {
    if (form.shot && DB.shots?.[form.shot]) {
      return `The image uses ${DB.shots[form.shot]}.`;
    }
    return "";
  }

  buildSubject(form) {
    // —— 自动推导：存在方式（仅二次元宇宙先用）——
    // resolveExistenceTemplate(form) 和 EXISTENCE_TEMPLATES 需要在 core.js 顶部定义（下面会讲）
    const existenceType = resolveExistenceTemplate(form);
    let existencePrompt = EXISTENCE_TEMPLATES?.[existenceType]?.prompt || "";
    existencePrompt = String(existencePrompt).trim();
  
    let subject = "The main subject is a female character";
  
    // 把“存在方式”作为世界事实插入到主体定义句（只插一句，别展开）
    if (existencePrompt && !/[.,;:!?]$/.test(existencePrompt)) {
      existencePrompt += ",";
    }
    
    if (existencePrompt) {
      subject += `, ${existencePrompt}`;
    }
  
    if (form.body && DB.SHAPES?.[form.body]?.prompt) {
      subject += ` with a ${DB.SHAPES[form.body].prompt}`;
    }
  
    if (form.cup && DB.CUPS?.[form.cup]?.prompt) {
      subject += `. ${DB.CUPS[form.cup].prompt}`;
    }
  
    return subject.endsWith(".") ? subject : `${subject}.`;
  }  

  buildAttire(form) {
    if (!form.clothing && !form.accessory) return "";
  
    // —— 取当前风格 prompt（用于判断可接受的“写实上限”）——
    // // 注意：styles_master / styles_studio / styles_unique 的值有时是字符串，有时是对象（含 prompt）
    // // 所以这里做一次统一抽取，避免只覆盖 unique
    let stylePrompt = "";
    if (form.style && form.style !== "none") {
      const raw =
      DB.styles_master?.[form.style] ??
      DB.styles_studio?.[form.style] ??
      DB.styles_unique?.[form.style];
      
      if (raw) {
        stylePrompt = typeof raw === "string" ? raw : String(raw.prompt || "");
      }
    }
  
    let realismHint = STYLE_REALISM_HINT.default;
  
    if (/mika pikazo|pop|geometric|graphic/i.test(stylePrompt)) {
      realismHint = STYLE_REALISM_HINT.pop;
    } else if (/anime|illustration|digital painting/i.test(stylePrompt)) {
      realismHint = STYLE_REALISM_HINT.anime;
    } else if (/realistic|cinematic|photoreal/i.test(stylePrompt)) {
      realismHint = STYLE_REALISM_HINT.realistic;
    }

    let attire = "She is";

    if (form.clothing && DB.CLOTHING?.[form.clothing]?.prompt) {
      let clothingPrompt = String(DB.CLOTHING[form.clothing].prompt).trim();
    
      // —— 系统级：成人 sailor 风格 去“school/未成年”语义锚点 ——
      // 任何包含 school / seifuku / school uniform 的服装描述，自动改写为成人 sailor 风格
      if (/school uniform|seifuku|school\b/i.test(clothingPrompt)) {
        clothingPrompt = clothingPrompt
          .replace(/school uniform/ig, "sailor-style outfit")
          .replace(/seifuku/ig, "adult sailor-inspired outfit")
          .replace(/\bschool\b/ig, "")
          .replace(/\s{2,}/g, " ")
          .trim();
    
        // 明确成人语义（关键：防止模型回退到学生分布）
        if (!/adult/i.test(clothingPrompt)) {
          clothingPrompt += ", worn by an adult woman";
        }
      }
    
      attire += ` ${clothingPrompt}`;
    } else {
      attire += " wearing casual clothes";
    }    

    if (form.accessory && DB.accessories?.[form.accessory]) {
      // accessories 的 value 是 prompt 字符串：不要截断括号内容，避免丢失物理细节（材质/形态）
      const accPrompt = String(DB.accessories[form.accessory]).trim();
      if (accPrompt) attire += `, paired with ${accPrompt}`;
    }    

    return `${attire}. Clothing textures and folds are ${realismHint}.`;

  }

  buildAction(form) {
    if (!form.action || !DB.actions?.[form.action]) return "";
  
    let actionText = String(DB.actions[form.action]);
  
    // --- 物理/构图一致性：全身镜头时，避免动作文本强迫近景细节 ---
    // 你的 shots 文案里如果包含 “full-body / head to toe / shoes and feet” 这类语义，
    // 就认为用户想要全身镜头。
    const shotText = form.shot && DB.shots?.[form.shot] ? String(DB.shots[form.shot]) : "";
    const isFullBodyShot = /full-?body|head to toe|shoes and feet/i.test(shotText);
  
    if (isFullBodyShot) {
      // 把会诱发“特写补一份”的描述降级成“动作清晰可见”
      actionText = actionText
        .replace(/focus on fingers/ig, "hands clearly visible")
        .replace(/close-?up/ig, "clear")
        .replace(/macro/ig, "clear")
        .replace(/detailed fingers/ig, "hands clearly visible");
    }
  
    return `The character is performing a pose: ${actionText}.`;
  }  

  buildScene(form) {
    if (form.scene && DB.scenes?.[form.scene]) {
      return `The background depicts ${DB.scenes[form.scene]}, rendered in the aforementioned art style.`;
    }
    return "";
  }

  buildEffect(form) {
    if (!form.effect || !DB.effects?.[form.effect]) return "";
  
    const effectText = String(DB.effects[form.effect]);
    let line = `The atmosphere is enhanced with ${effectText}.`;
  
    // --- 物理状态强时，轻量护栏：避免“并置视角/重复主体”来表达湿感细节 ---
    if (/wet|soaked|water droplets|sweating|shiny skin/i.test(effectText)) {
      line += " Single character only, single view, no inset portrait, no duplicate character.";
    }
  
    return line;
  }  

  buildCustom(form) {
    const t = (form.customText || "").trim();
    if (!t) return "";
    return `Additional details: ${t.replace(/[。.!?]+$/g, "")}.`;
  }

  buildQuality(form, styleProfile) {
    let tags = styleProfile?.qualityOverride
      ? [...styleProfile.qualityOverride]
      : [...this.qualityTagsBase];

    if (styleProfile?.extraPositive?.length) {
      tags.push(...styleProfile.extraPositive);
    }

    if (!styleProfile?.qualityOverride &&
        form.shot === "特写 (Close-up)") {
      tags.push(...this.qualityTagsCloseUp);
    }

    return `${tags.join(", ")}.`;
  }

  buildNegative(styleProfile) {
    const merged = [...this.negativeTags];

    if (styleProfile?.negativeAdd?.length) {
      merged.push(...styleProfile.negativeAdd);
    }

    const seen = new Set();
    const uniq = merged.filter(v => {
      const k = String(v).toLowerCase().trim();
      if (!k || seen.has(k)) return false;
      seen.add(k);
      return true;
    });

    return `Avoid: ${uniq.join(", ")}.`;
  }

  // ======================================================
  // Budget pruning
  // ======================================================
  pruneByBudget(segments, maxChars) {
    if (segments.join(" ").length <= maxChars) return segments;

    const optionalPrefixes = [
      "Additional details:",
      "The atmosphere is enhanced with",
      "The background depicts",
      "The character is performing a pose:"
    ];

    const kept = [...segments];

    for (let i = kept.length - 1; i >= 0; i--) {
      if (optionalPrefixes.some(p => kept[i]?.startsWith(p))) {
        kept.splice(i, 1);
        if (kept.join(" ").length <= maxChars) break;
      }
    }

    let joined = kept.join(" ");
    if (joined.length > maxChars) {
      joined = joined.slice(0, maxChars - 1) + "…";
      return [joined];
    }

    return kept;
  }
}