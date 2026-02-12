const DEFAULT_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`;
const BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL;

export async function chatParse(text) {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? "Chat failed");
  }
  return res.json();
}
