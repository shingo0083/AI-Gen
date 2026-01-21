/** Auto-generated aggregator. Original backed up as data.js.bak */
import { styles_master } from './data/styles/styles_master.js';
import { styles_studio } from './data/styles/styles_studio.js';
import { styles_unique } from './data/styles/styles_unique.js';
import { CLOTHING } from './data/catalog/clothing.js';
import { accessories } from './data/catalog/accessories.js';
import { actions } from './data/catalog/actions.js';
import { scenes } from './data/catalog/scenes.js';
import { effects } from './data/catalog/effects.js';

export const DB = {
  styles_master: styles_master,
  styles_studio: styles_studio,
  styles_unique: styles_unique,
  CLOTHING: CLOTHING,
  accessories: accessories,
  actions: actions,
  scenes: scenes,
  effects: effects,
  shots: {
                "特写 (Close-up)": "a close-up portrait focusing on the face and expression, cutting off at the shoulders",
                "半身 (Medium Shot)": "a medium shot capturing the character from the waist up",
                "全身 (Full Body)": "a wide full-body shot showing the character completely from head to toe, ensuring the shoes and feet are fully visible within the frame",
                "大远景 (Long Shot)": "a long shot with the character small in the frame, emphasizing the vast environment",
                "牛仔景别 (Cowboy Shot)": "a cowboy shot framing the character from mid-thigh up"
            },
  CUPS: {
            "A": {
                label: "A Cup",
                prompt: "Bust volume is small and close to the ribcage profile. Subtle curvature with minimal gravitational sag. Underbust boundary and shadow are faint. In most outfits, the silhouette change is modest."
            },
            "B": {
                label: "B Cup",
                prompt: "Bust volume is modest and clearly present. Stable contour in neutral posture with light gravitational influence. Underbust boundary is mild; shadow is soft."
            },
            "C": {
                label: "C Cup",
                prompt: "Bust volume is medium and balanced against the torso. Clear, natural contour with moderate gravitational influence. Underbust boundary becomes visible in many angles."
            },
            "D": {
                label: "D Cup",
                prompt: "Bust volume is medium-large and distinctly visible relative to the torso. Gravitational load produces a clearer underbust boundary and natural underbust shadow. The silhouette is visibly shaped by volume."
            },
            "E": {
                label: "E Cup",
                prompt: "Bust volume is large and immediately apparent. Underbust boundary and contact with the torso are more pronounced due to weight and volume. Fabric tension and shape-conforming behavior appear."
            },
            "F": {
                label: "F Cup",
                prompt: "Bust volume is very large and becomes a major contributor to upper-body silhouette. Gravitational influence is strong, creating a stable and clearly defined underbust boundary."
            },
            "G": {
                label: "G Cup",
                prompt: "Bust volume is extremely large and dominates the upper-body massing. Weight and volume significantly affect shape; the underbust boundary and natural shadow are consistently visible."
            }
            },
  SHAPES: {
            "Slender": {
                label: "Slender (女团腿)",
                prompt: "(slender idol physique:1.3), (A4 waist:1.2), flat tummy, slender long legs, delicate shoulders, streamlined body line, (feminine and fragile:1.1)"
            },
            "Athletic": {
                label: "Fit (瑜伽/马甲线)",
                prompt: "(fit yoga body:1.2), (11-line abs:1.2), toned but slender limbs, healthy skin glow, taut tummy, athletic chic, energetic vibe"
            },
            "Soft": {
                label: "Marshmallow (棉花糖/微胖)",
                prompt: "(soft marshmallow body:1.3), (fleshy thighs:1.2), (plump and curvy:1.2), soft skin texture, feminine curves, huggable body"
            },
            "Petite": {
                label: "Petite (二次元娇小)",
                prompt: "(petite and cute frame:1.3), short stature, (small head to body ratio:1.2), delicate joints, youthful proportions, kawaii aesthetic"
            }
        },
};
