// In dev, requests go to "/api/*" and Vite proxies them to the backend.
// In production, set VITE_API_URL to the deployed backend origin.
export const API_BASE = import.meta.env.VITE_API_URL || "/api";

/** Extract a human-readable message from a FastAPI error response. */
async function errorDetail(res) {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return data.detail[0].msg;
  } catch {
    // fall through to a generic message
  }
  return `Upload failed (HTTP ${res.status}).`;
}

/** GET /health → returns the status string ("ok"). */
export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.status;
}

/** POST /documents with a PDF file. Resolves to the document payload. */
export async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/documents`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

/** POST /documents with raw text. Resolves to the document payload. */
export async function uploadText(text) {
  const form = new FormData();
  form.append("text", text);
  const res = await fetch(`${API_BASE}/documents`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

/** POST /ask — resolves to { interaction_id, answer, source_passage, ... }. */
export async function askQuestion(documentId, question) {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, question }),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

/** POST /feedback — attach a 👍/👎 ("up" | "down") to an interaction. */
export async function sendFeedback(interactionId, feedback) {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interaction_id: interactionId, feedback }),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

/** GET /stats — dashboard metrics. */
export async function getStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
