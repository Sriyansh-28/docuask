import { useEffect, useRef, useState } from "react";
import { askQuestion, sendFeedback } from "./api";

// A single turn. Assistant turns carry the source passage so it can be shown
// under the answer. `pending` marks the in-flight assistant bubble.
function makeMessage(role, text, extra = {}) {
  return { id: crypto.randomUUID(), role, text, ...extra };
}

export default function Chat({ doc, onReset }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;

    setMessages((m) => [...m, makeMessage("user", q)]);
    setQuestion("");
    setBusy(true);
    try {
      const res = await askQuestion(doc.document_id, q);
      setMessages((m) => [
        ...m,
        makeMessage("assistant", res.answer, {
          source: res.source_passage,
          interactionId: res.interaction_id,
          feedback: null,
          generated: res.generated,
        }),
      ]);
    } catch (err) {
      setMessages((m) => [...m, makeMessage("error", err.message)]);
    } finally {
      setBusy(false);
    }
  }

  async function rate(messageId, interactionId, value) {
    // Optimistically reflect the choice; revert if the request fails.
    setMessages((m) =>
      m.map((msg) => (msg.id === messageId ? { ...msg, feedback: value } : msg)),
    );
    try {
      await sendFeedback(interactionId, value);
    } catch {
      setMessages((m) =>
        m.map((msg) => (msg.id === messageId ? { ...msg, feedback: null } : msg)),
      );
    }
  }

  return (
    <div className="flex h-[70vh] flex-col rounded-2xl bg-white shadow-lg ring-1 ring-slate-200">
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-800">
            {doc.filename || "Pasted text"}
          </p>
          <p className="text-xs text-slate-400">{doc.num_chunks} chunks indexed</p>
        </div>
        <button
          onClick={onReset}
          className="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-500 ring-1 ring-slate-200 transition hover:bg-slate-50"
        >
          New document
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {messages.length === 0 && (
          <p className="mt-10 text-center text-sm text-slate-400">
            Ask a question about this document to get started.
          </p>
        )}

        {messages.map((m) => {
          if (m.role === "user") {
            return (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-slate-800 px-4 py-2 text-sm text-white">
                  {m.text}
                </div>
              </div>
            );
          }
          if (m.role === "error") {
            return (
              <div key={m.id} className="flex justify-start">
                <div className="max-w-[80%] rounded-2xl bg-red-50 px-4 py-2 text-sm text-red-700 ring-1 ring-red-200">
                  ⚠ {m.text}
                </div>
              </div>
            );
          }
          return (
            <div key={m.id} className="flex flex-col items-start gap-1">
              <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-2 text-sm text-slate-800">
                {m.text}
              </div>
              {m.generated && (
                <span className="pl-1 text-[11px] font-medium text-emerald-600">
                  ✨ AI answer · grounded in the source below
                </span>
              )}
              {m.source && (
                <details className="max-w-[85%] rounded-lg bg-emerald-50 px-3 py-2 text-xs text-slate-600 ring-1 ring-emerald-100">
                  <summary className="cursor-pointer font-medium text-emerald-700">
                    Source passage
                  </summary>
                  <p className="mt-1 whitespace-pre-wrap leading-relaxed">{m.source}</p>
                </details>
              )}
              {m.interactionId && (
                <div className="flex items-center gap-1.5 pl-1">
                  <span className="text-xs text-slate-400">Helpful?</span>
                  <FeedbackButton
                    active={m.feedback === "up"}
                    dimmed={m.feedback === "down"}
                    activeClass="bg-emerald-100 text-emerald-700 ring-emerald-200"
                    label="Yes, helpful"
                    onClick={() => rate(m.id, m.interactionId, "up")}
                  >
                    👍
                  </FeedbackButton>
                  <FeedbackButton
                    active={m.feedback === "down"}
                    dimmed={m.feedback === "up"}
                    activeClass="bg-red-100 text-red-700 ring-red-200"
                    label="Not helpful"
                    onClick={() => rate(m.id, m.interactionId, "down")}
                  >
                    👎
                  </FeedbackButton>
                </div>
              )}
            </div>
          );
        })}

        {busy && (
          <div className="flex justify-start">
            <div className="flex gap-1 rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-3">
              <Dot /> <Dot delay="150ms" /> <Dot delay="300ms" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={send} className="flex gap-2 border-t border-slate-200 p-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm outline-none transition focus:border-slate-400 focus:bg-white"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Ask
        </button>
      </form>
    </div>
  );
}

function Dot({ delay = "0ms" }) {
  return (
    <span
      className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400"
      style={{ animationDelay: delay }}
    />
  );
}

function FeedbackButton({ active, dimmed, activeClass, label, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={active}
      className={`rounded-md px-1.5 py-0.5 text-sm ring-1 transition ${
        active
          ? activeClass
          : `ring-transparent hover:bg-slate-100 ${dimmed ? "opacity-40" : ""}`
      }`}
    >
      {children}
    </button>
  );
}
