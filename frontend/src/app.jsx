import React, { useEffect, useMemo, useRef, useState } from "react";
import { chatParse } from "./chatapi"; // keep this matching your actual filename
import { generateZip } from "./api";

function Badge({ children }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 10px",
        borderRadius: 999,
        background: "rgba(255,255,255,0.75)",
        border: "1px solid rgba(255,255,255,0.55)",
        fontSize: 12,
        color: "#1f2937",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
      }}
    >
      {children}
    </span>
  );
}

function SoftButton({ children, onClick, disabled, variant = "primary" }) {
  const isPrimary = variant === "primary";
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "12px 14px",
        borderRadius: 14,
        border: isPrimary ? "1px solid rgba(17, 24, 39, 0.2)" : "1px solid rgba(17, 24, 39, 0.15)",
        background: disabled
          ? "rgba(255,255,255,0.65)"
          : isPrimary
          ? "linear-gradient(135deg, #111827, #0f172a)"
          : "rgba(255,255,255,0.75)",
        color: disabled ? "#111827" : isPrimary ? "#fff" : "#111827",
        cursor: disabled ? "not-allowed" : "pointer",
        fontWeight: 700,
        boxShadow: disabled
          ? "none"
          : isPrimary
          ? "0 12px 30px rgba(2, 6, 23, 0.22)"
          : "0 10px 24px rgba(2, 6, 23, 0.10)",
        transition: "transform 120ms ease, box-shadow 120ms ease",
      }}
      onMouseDown={(e) => {
        if (disabled) return;
        e.currentTarget.style.transform = "translateY(1px)";
      }}
      onMouseUp={(e) => {
        e.currentTarget.style.transform = "translateY(0px)";
      }}
    >
      {children}
    </button>
  );
}

function ResultCard({ item, onDownload }) {
  const title =
    item.part === "screw"
      ? `Screw · ${item.family}`
      : `Nut · ${item.family}`;

  const subtitle =
    item.part === "screw"
      ? `${item.size} · ${item.length_mm ?? ""} mm`
      : `${item.size}`;

  return (
    <div
      style={{
        borderRadius: 16,
        padding: 12,
        background: "rgba(255,255,255,0.85)",
        border: "1px solid rgba(255,255,255,0.7)",
        boxShadow: "0 10px 30px rgba(2, 6, 23, 0.10)",
        marginTop: 10,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 800, color: "#0f172a" }}>{title}</div>
          <div style={{ marginTop: 4, color: "#475569", fontSize: 13, fontWeight: 600 }}>{subtitle}</div>
          <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Badge>Standard: {item.fastener_type}</Badge>
            <Badge>Size: {item.size}</Badge>
            {item.part === "screw" ? <Badge>Length: {Math.round(Number(item.length_mm))}mm</Badge> : null}
          </div>
        </div>
        <div style={{ minWidth: 160 }}>
          <SoftButton onClick={() => onDownload(item)} variant="primary">
            Download STEP + STL
          </SoftButton>
          <div style={{ marginTop: 8, color: "#64748b", fontSize: 12, lineHeight: 1.2 }}>
            You’ll get a ZIP with both files.
          </div>
        </div>
      </div>
    </div>
  );
}

function Bubble({ role, children }) {
  const isUser = role === "user";
  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
      <div
        style={{
          maxWidth: "780px",
          width: "fit-content",
          whiteSpace: "pre-wrap",
          padding: "12px 14px",
          borderRadius: 18,
          lineHeight: 1.4,
          background: isUser
            ? "linear-gradient(135deg, #111827, #0f172a)"
            : "rgba(255,255,255,0.80)",
          color: isUser ? "#fff" : "#0f172a",
          border: isUser ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(255,255,255,0.7)",
          boxShadow: isUser ? "0 14px 34px rgba(2, 6, 23, 0.18)" : "0 10px 26px rgba(2, 6, 23, 0.08)",
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
        }}
      >
        {children}
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! Tell me what fastener you want 😊\n\nExamples:\n• “M6 socket head screw 20mm and a nut that fits it”\n• “M8 hex bolt 30mm”",
      result: null,
    },
  ]);

  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const scrollRef = useRef(null);

  useEffect(() => {
    // auto-scroll to bottom when messages change
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length]);

  async function send() {
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    setError("");
    setBusy(true);

    setMessages((m) => [...m, { role: "user", content: trimmed, result: null }]);
    setText("");

    try {
      const parsed = await chatParse(trimmed);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: parsed.message,
          result: parsed,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `Hmm, I couldn’t understand that. (${e.message})`, result: null },
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
      a.download = `${item.part}_${item.size}${item.part === "screw" ? "_" + Math.round(Number(item.length_mm)) + "mm" : ""}.zip`;
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
    <div
      style={{
        minHeight: "100vh",
        width: "100%",
        background:
          "radial-gradient(1200px 800px at 20% 10%, rgba(236, 72, 153, 0.18), transparent 60%)," +
          "radial-gradient(900px 700px at 80% 20%, rgba(59, 130, 246, 0.18), transparent 55%)," +
          "radial-gradient(1000px 800px at 50% 100%, rgba(34, 197, 94, 0.12), transparent 55%)," +
          "linear-gradient(180deg, #f8fafc, #f1f5f9)",
        fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif',
        color: "#0f172a",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <div style={{ padding: "18px 18px 10px" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 900, letterSpacing: -0.2 }}>Fastener Finder</div>
            <div style={{ marginTop: 3, color: "#64748b", fontSize: 13, fontWeight: 600 }}>
              Describe what you need — get downloadable CAD files.
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <Badge>STEP + STL</Badge>
            <Badge>Metric fasteners</Badge>
            <Badge>Chat-based</Badge>
          </div>
        </div>
      </div>

      {/* Main card */}
      <div style={{ flex: 1, padding: "0 18px 18px", display: "flex" }}>
        <div style={{ maxWidth: 1080, width: "100%", margin: "0 auto", display: "flex", flexDirection: "column" }}>
          <div
            style={{
              flex: 1,
              borderRadius: 20,
              border: "1px solid rgba(255,255,255,0.7)",
              background: "rgba(255,255,255,0.55)",
              boxShadow: "0 18px 60px rgba(2, 6, 23, 0.12)",
              backdropFilter: "blur(12px)",
              WebkitBackdropFilter: "blur(12px)",
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
            }}
          >
            {/* Messages */}
            <div
              ref={scrollRef}
              style={{
                padding: 14,
                overflowY: "auto",
                flex: 1,
                display: "grid",
                gap: 12,
              }}
            >
              {messages.map((msg, idx) => (
                <div key={idx}>
                  <Bubble role={msg.role}>
                    {msg.content}
                    {msg.result?.items?.length ? (
                      <div style={{ marginTop: 10 }}>
                        {msg.result.items.map((item, i) => (
                          <ResultCard key={i} item={item} onDownload={download} />
                        ))}
                      </div>
                    ) : null}
                  </Bubble>
                </div>
              ))}
            </div>

            {/* Composer */}
            <div style={{ padding: 14, borderTop: "1px solid rgba(15, 23, 42, 0.06)", background: "rgba(255,255,255,0.6)" }}>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => (e.key === "Enter" ? send() : null)}
                  placeholder='Try: “M6 socket head screw 20mm + matching nut”'
                  disabled={busy}
                  style={{
                    flex: 1,
                    padding: "13px 14px",
                    borderRadius: 14,
                    border: "1px solid rgba(15, 23, 42, 0.12)",
                    background: "rgba(255,255,255,0.85)",
                    outline: "none",
                    fontSize: 14,
                    boxShadow: "0 10px 26px rgba(2, 6, 23, 0.06)",
                  }}
                />
                <SoftButton onClick={send} disabled={busy} variant="primary">
                  {busy ? "Sending…" : "Send"}
                </SoftButton>
              </div>

              {error ? <div style={{ marginTop: 10, color: "#be123c", fontWeight: 700 }}>{error}</div> : null}

              <div style={{ marginTop: 10, color: "#64748b", fontSize: 12 }}>
                Tip: include size (M6/M8), head style (socket/hex), and length (mm).{" "}
                <span style={{ opacity: 0.8 }}>Backend: http://localhost:8000</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
