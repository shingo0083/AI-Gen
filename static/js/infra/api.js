// static/js/infra/api.js
// 只负责“怎么请求后端”，不负责 UI、不负责业务规则

export async function apiInit() {
  const res = await fetch("/api/init");
  // init 一般不会失败，但我们还是保险一点
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(t || `Init failed: ${res.status}`);
  }
  return await res.json();
}

export async function apiGenerate(payload) {
  // 这里返回 Response，让上层决定如何处理 bad response
  return await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
