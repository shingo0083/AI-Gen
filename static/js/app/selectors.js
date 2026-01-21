import { buildFinalPrompt } from "../domain/prompt.js";
export function selectViewModel(state) {
  const history = Array.isArray(state.history) ? state.history : [];

  return {
    loading: !!state.loading,
    errorMsg: state.error || "",
    history: history.map(normalizeHistoryItem),
    finalPrompt: buildFinalPrompt(state.form || {}),
  };
}

function normalizeHistoryItem(item) {
  // 容错：避免某些字段缺失导致 UI 报错
  const safe = item && typeof item === "object" ? item : {};
  return {
    ...safe,
    url: safe.url || "",
    filename: safe.filename || "",
    prompt: safe.prompt || safe.final_prompt || "",
    metadata: safe.metadata || null,
  };
}
