export async function fetchCatalog() {
  const res = await fetch("http://localhost:8000/api/catalog");
  if (!res.ok) throw new Error("Failed to load catalog");
  return res.json();
}

export async function generateZip(payload) {
  const res = await fetch("http://localhost:8000/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? "Generation failed");
  }
  return res.blob();
}
