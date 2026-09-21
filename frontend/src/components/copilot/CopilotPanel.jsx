import { useEffect, useRef, useState } from "react";
import { Loader2, MessageCircle, Send, X, ExternalLink } from "lucide-react";
import { endpoints } from "../../lib/api";

export default function CopilotPanel({ enabled, testId = "copilot-panel" }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const feedRef = useRef(null);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [messages, busy]);

  const suggestions = [
    "Why did the last delivery take so long?",
    "Which agent is at highest risk right now?",
    "Explain auction-based task allocation briefly.",
    "How does the swarm recover from an agent failure?",
  ];

  const send = async (q) => {
    const question = (q ?? input).trim();
    if (!question || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: question, ts: Date.now() }]);
    setBusy(true);
    try {
      const res = await endpoints.copilotAsk({ question });
      setMessages((m) => [
        ...m,
        {
          role: "analyst",
          text: res.answer || "No answer.",
          citations: res.citations || [],
          model: res.model,
          ts: Date.now(),
        },
      ]);
    } catch (e) {
      setMessages((m) => [...m, { role: "analyst", text: "Analyst is unavailable right now.", ts: Date.now() }]);
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button
        className="copilot-fab"
        onClick={() => setOpen(true)}
        data-testid="copilot-open-button"
        disabled={!enabled}
        title={enabled ? "Open Mission Copilot" : "Copilot is offline"}
      >
        <MessageCircle size={18} />
        <span>Mission Copilot</span>
      </button>
    );
  }

  return (
    <aside className="copilot-drawer" data-testid={testId}>
      <header className="copilot-head">
        <div>
          <span className="panel-kicker">Mission Copilot · Perplexity</span>
          <h3>Ask the analyst</h3>
        </div>
        <button className="btn ghost" onClick={() => setOpen(false)} data-testid="copilot-close-button"><X size={14} /></button>
      </header>

      <div className="copilot-feed" ref={feedRef} data-testid="copilot-feed">
        {messages.length === 0 && (
          <div className="copilot-empty">
            <p>Get grounded, web-cited answers about the live swarm state.</p>
            <div className="copilot-suggestions">
              {suggestions.map((s) => (
                <button
                  key={s}
                  className="pill muted"
                  onClick={() => send(s)}
                  data-testid={`copilot-suggestion-${s.slice(0, 12).replace(/\s+/g, "-")}`}
                >{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={m.ts + "-" + i} className={`copilot-msg ${m.role}`} data-testid={`copilot-msg-${i}`}>
            <div className="copilot-msg-role">{m.role === "user" ? "OPERATOR" : "ANALYST"}</div>
            <div className="copilot-msg-body">{m.text}</div>
            {m.citations && m.citations.length > 0 && (
              <ul className="copilot-cites" data-testid={`copilot-citations-${i}`}>
                {m.citations.slice(0, 6).map((c, j) => (
                  <li key={c.url + j}>
                    <a href={c.url} target="_blank" rel="noreferrer" data-testid={`copilot-citation-${i}-${j}`}>
                      <ExternalLink size={12} />
                      <span>{c.title || c.url}</span>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {busy && (
          <div className="copilot-msg analyst pending" data-testid="copilot-loading">
            <div className="copilot-msg-role">ANALYST</div>
            <div className="copilot-msg-body"><Loader2 size={14} className="spin" /> researching…</div>
          </div>
        )}
      </div>

      <form
        className="copilot-input"
        onSubmit={(e) => { e.preventDefault(); send(); }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about the current mission…"
          disabled={busy || !enabled}
          data-testid="copilot-input"
        />
        <button className="btn primary" type="submit" disabled={busy || !enabled || !input.trim()} data-testid="copilot-send-button">
          <Send size={14} />
        </button>
      </form>
      {!enabled && <div className="copilot-offline" data-testid="copilot-offline">Copilot is offline — server has no Perplexity key.</div>}
    </aside>
  );
}
