import React, { useEffect, useMemo, useState } from "react";
import { fetchCatalog, generateZip } from "./api";

const STYLES = {
  screw: [
    { family: "SocketHeadCapScrew", label: "Socket Head Cap Screw" },
    { family: "HexHeadScrew", label: "Hex Head Screw" },
    { family: "CounterSunkScrew", label: "Countersunk Screw" },
    { family: "PanHeadScrew", label: "Pan Head Screw" },
  ],
  nut: [{ family: "HexNut", label: "Hex Nut" }],
};

// Reasonable defaults (you can expand later)
const DEFAULT_TYPES = {
  HexNut: "iso4032",
  SocketHeadCapScrew: "iso4762",
  HexHeadScrew: "iso4017",
  CounterSunkScrew: "iso10642",
  PanHeadScrew: "iso1580",
};

export default function App() {
  const [catalog, setCatalog] = useState(null);
  const [part, setPart] = useState("screw");
  const [family, setFamily] = useState("SocketHeadCapScrew");
  const [fastenerType, setFastenerType] = useState(DEFAULT_TYPES["SocketHeadCapScrew"]);
  const [size, setSize] = useState("M6-1");
  const [lengthMm, setLengthMm] = useState(20);
  const [simple, setSimple] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCatalog().then(setCatalog).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    // keep family valid for part
    const first = STYLES[part][0].family;
    setFamily(first);
  }, [part]);

  useEffect(() => {
    setFastenerType(DEFAULT_TYPES[family] ?? "");
  }, [family]);

  const showLength = part === "screw";

  async function onGenerate() {
    setError("");
    setBusy(true);
    try {
      const payload = {
        part,
        family,
        fastener_type: fastenerType,
        size,
        length_mm: showLength ? Number(lengthMm) : null,
        simple,
      };

      const blob = await generateZip(payload);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fastener_${part}_${size}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif", padding: 24, maxWidth: 720, margin: "0 auto" }}>
      <h1 style={{ margin: 0, fontSize: 28 }}>Fastener Generator</h1>
      <p style={{ marginTop: 8, color: "#555" }}>
        Generate a parametric screw or nut and download STEP + STL.
      </p>

      <div style={{ display: "grid", gap: 12, padding: 16, border: "1px solid #e5e5e5", borderRadius: 12 }}>
        <label>
          Part
          <select value={part} onChange={(e) => setPart(e.target.value)} style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }}>
            <option value="screw">Screw</option>
            <option value="nut">Nut</option>
          </select>
        </label>

        <label>
          Style
          <select value={family} onChange={(e) => setFamily(e.target.value)} style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }}>
            {STYLES[part].map((s) => (
              <option key={s.family} value={s.family}>{s.label}</option>
            ))}
          </select>
        </label>

        <label>
          Standard type (example)
          <input value={fastenerType} onChange={(e) => setFastenerType(e.target.value)} placeholder="e.g. iso4762" style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }} />
          <div style={{ color: "#777", fontSize: 12, marginTop: 6 }}>
            Tip: cq_warehouse supports many types per family (e.g. ISO/ASME).
          </div>
        </label>

        <label>
          Size
          <input value={size} onChange={(e) => setSize(e.target.value)} placeholder="e.g. M6-1" style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }} />
        </label>

        {showLength && (
          <label>
            Length (mm)
            <input type="number" value={lengthMm} onChange={(e) => setLengthMm(e.target.value)} min={1} step={1}
              style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }} />
          </label>
        )}

        <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input type="checkbox" checked={simple} onChange={(e) => setSimple(e.target.checked)} />
          Simple geometry (no helical threads — faster)
        </label>

        {error && <div style={{ color: "crimson" }}>{error}</div>}

        <button
          onClick={onGenerate}
          disabled={busy}
          style={{
            padding: 12,
            borderRadius: 10,
            border: "1px solid #111",
            background: busy ? "#eee" : "#111",
            color: busy ? "#111" : "#fff",
            cursor: busy ? "not-allowed" : "pointer",
            fontWeight: 600
          }}
        >
          {busy ? "Generating…" : "Generate & Download"}
        </button>
      </div>

      <div style={{ marginTop: 14, color: "#666", fontSize: 13 }}>
        Backend: <code>http://localhost:8000</code> • Frontend: <code>http://localhost:5173</code>
      </div>
    </div>
  );
}

