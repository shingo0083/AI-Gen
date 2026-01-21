// static/js/domain/prompt.js
import { WaifuCore } from "../core.js";

// 用一个“单例 core”复用核心算法，避免 UI 直接依赖 core
const core = new WaifuCore();

export function buildFinalPrompt(form) {
  return core.assemblePrompt(form);
}
