import React, { useMemo, useState } from "react";
import { chatParse } from "./chatApiT";
import { generateZip } from "./api";

function ResultCard({ item, onDownload }) {
  const title =
    item.part === "screw"
      ? `Screw · ${item.family} · ${item.size} · ${item.length_mm ?? ""}mm`
      : `Nut · ${item.family} · ${item.size}`;

  return (
    <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 12, marginTop: 10 }}>
      <div style={{ fontWeight: 700 }}>{title}</div>
      <div style={{ marginTop: 6, color: "#555", fontSize: 13 }}>
        <div><b>Standard:</b> {item.fastener_type}</div>
        <div><b>Simple geometry:</b> {String(item.simple)}</div>
      </div>
      <button
        onClick={() => onDownload(item)}
        style={{
          marginTop: 10,
          padding: "10px 12px",
          borderRadius: 10,
          border: "1px solid #111",
          background: "#111",
          color: "#fff",
          cursor: "pointer",
          fontWeight: 600
        }}
      >
        Download STEP + STL
      </button>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Describe what you need. Example:\n“M6 socket head screw 20mm and a nut that fits it”",
      result: null,
    },
  ]);

  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function send() {
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    setError("");
    setBusy(true);

    // push user message
    setMessages((m) => [...m, { role: "user", content: trimmed, result: null }]);
    setText("");

    try {
      const parsed = await chatParse(trimmed);

      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: parsed.message,
          result: parsed, // includes items
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `Sorry — I couldn’t parse that. (${e.message})`, result: null },
      ]);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function download(item) {
    setError("");
    setBusy(true);
    try {
      const payload = {
        part: item.part,
        family: item.family,
        fastener_type: item.fastener_type,
        size: item.size,
        length_mm: item.part === "screw" ? Number(item.length_mm) : null,
        simple: Boolean(item.simple),
      };

      const blob = await generateZip(payload);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${item.part}_${item.size}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
      alert(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif", background: "#fafafa", minHeight: "100vh" }}>
      <div style={{ maxWidth: 860, margin: "0 auto", padding: 18 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>Fastener Chat (no AI yet)</h1>
        <div style={{ color: "#666", marginTop: 6, fontSize: 13 }}>
          Type what you want, I’ll convert it into generator specs.
        </div>

        <div style={{ marginTop: 14, background: "#fff", border: "1px solid #e8e8e8", borderRadius: 14, padding: 14 }}>
          <div style={{ display: "grid", gap: 12 }}>
            {messages.map((msg, idx) => (
              <div key={idx} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
                <div
                  style={{
                    maxWidth: "80%",
                    whiteSpace: "pre-wrap",
                    padding: "10px 12px",
                    borderRadius: 14,
                    background: msg.role === "user" ? "#111" : "#f3f3f3",
                    color: msg.role === "user" ? "#fff" : "#111",
                    lineHeight: 1.35,
                  }}
                >
                  {msg.content}

                  {msg.result?.items?.length ? (
                    <div style={{ marginTop: 10 }}>
                      {msg.result.items.map((item, i) => (
                        <ResultCard key={i} item={item} onDownload={download} />
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 14, display: "flex", gap: 10 }}>
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => (e.key === "Enter" ? send() : null)}
              placeholder='Try: "M8 hex bolt 30mm and nut"'
              style={{
                flex: 1,
                padding: 12,
                borderRadius: 12,
                border: "1px solid #ddd",
                outline: "none",
              }}
              disabled={busy}
            />
            <button
              onClick={send}
              disabled={busy}
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                border: "1px solid #111",
                background: busy ? "#eee" : "#111",
                color: busy ? "#111" : "#fff",
                cursor: busy ? "not-allowed" : "pointer",
                fontWeight: 700,
              }}
            >
              {busy ? "…" : "Send"}
            </button>
          </div>

          {error ? <div style={{ color: "crimson", marginTop: 10 }}>{error}</div> : null}
          <div style={{ marginTop: 10, color: "#777", fontSize: 12 }}>
            Backend: <code>http://localhost:8000</code>
          </div>
        </div>
      </div>
    </div>
  );
}
