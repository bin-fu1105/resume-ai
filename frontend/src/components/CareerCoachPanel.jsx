import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import Spinner from "./ui/Spinner";
import { API_BASE } from "../utils/uploadFile";
import { toFriendlyError } from "../utils/friendlyError";

const STARTER_QUESTIONS = [
  "Why is my ATS score low?",
  "How can I improve my Projects?",
  "Rewrite only my Summary.",
  "What interview questions should I expect?",
];

function TypingIndicator() {
  return (
    <div
      className="flex items-center gap-1 rounded-2xl rounded-tl-md bg-canvas px-4 py-3"
      role="status"
      aria-label="Coach is typing"
    >
      <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:-0.2s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:-0.1s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-accent" />
    </div>
  );
}

function CareerCoachPanel({
  filename,
  jobDescription,
  analysis,
  rewrite,
  enabled,
}) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  const sendMessage = async (rawMessage) => {
    const content = rawMessage.trim();
    if (!content || sending) return;

    if (!enabled || !filename) {
      setError("Upload a resume first to start coaching.");
      return;
    }

    const historyPayload = messages.map(({ role, content: text }) => ({
      role,
      content: text,
    }));

    const userMessage = { role: "user", content };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setError("");
    setSending(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filename,
          job_description: jobDescription || "",
          history: historyPayload,
          message: content,
          analysis: analysis || {},
          rewrite: rewrite || {},
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          toFriendlyError(
            data.detail || data.error || data,
            "The coach couldn't reply. Please try again."
          )
        );
      }

      const reply = String(data.reply || "").trim();
      if (!reply) {
        throw new Error("The coach returned an empty reply.");
      }

      setMessages((current) => [
        ...current,
        { role: "assistant", content: reply },
      ]);
    } catch (err) {
      const message = toFriendlyError(
        err,
        "The coach couldn't reply. Please try again."
      );
      setError(message);
    } finally {
      setSending(false);
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(draft);
    }
  };

  return (
    <aside
      id="coach"
      className="panel-card flex h-[min(80vh,720px)] min-h-[28rem] flex-col overflow-hidden lg:sticky lg:top-24 lg:h-[calc(100vh-7.5rem)]"
      aria-label="AI Career Coach"
    >
      <div className="border-b border-line pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
          Coach
        </p>
        <h2 className="mt-1 font-display text-lg font-semibold tracking-tight text-ink">
          AI Career Coach
        </h2>
        <p className="mt-1 text-sm text-muted">
          Ask follow-up questions. I already know your ATS score, gaps, and
          rewrite when available.
        </p>
      </div>

      <div
        className="mt-4 flex-1 space-y-3 overflow-y-auto pr-1"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
      >
        {messages.length === 0 && (
          <div className="rounded-xl border border-dashed border-line bg-canvas/50 px-4 py-5">
            <p className="text-sm font-medium text-ink">
              Start with a question
            </p>
            <p className="mt-1 text-sm text-muted">
              {enabled
                ? "Pick a starter or type your own. Shift+Enter adds a new line."
                : "Upload a resume to unlock coaching."}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {STARTER_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  disabled={!enabled || sending}
                  onClick={() => sendMessage(question)}
                  className="rounded-full border border-line bg-white px-3 py-1.5 text-left text-xs font-medium text-ink transition hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, index) => {
          const isUser = message.role === "user";
          return (
            <div
              key={`${message.role}-${index}`}
              className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed sm:max-w-[85%] ${
                  isUser
                    ? "rounded-tr-md bg-accent text-white"
                    : "rounded-tl-md bg-canvas text-ink"
                }`}
              >
                {isUser ? (
                  <p className="whitespace-pre-wrap break-words">
                    {message.content}
                  </p>
                ) : (
                  <div className="chat-markdown break-words">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {sending && (
          <div className="flex justify-start">
            <TypingIndicator />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="mt-3 text-xs text-red-700" role="alert">
          {error}
        </p>
      )}

      {messages.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-line pt-3">
          {STARTER_QUESTIONS.map((question) => (
            <button
              key={`follow-${question}`}
              type="button"
              disabled={!enabled || sending}
              onClick={() => sendMessage(question)}
              className="rounded-full border border-line bg-white px-2.5 py-1 text-xs font-medium text-muted transition hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              {question}
            </button>
          ))}
        </div>
      )}

      <form
        className="mt-3 border-t border-line pt-3"
        onSubmit={(event) => {
          event.preventDefault();
          sendMessage(draft);
        }}
      >
        <label htmlFor="career-coach-input" className="sr-only">
          Message the career coach
        </label>
        <textarea
          id="career-coach-input"
          ref={textareaRef}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          disabled={!enabled || sending}
          placeholder={
            enabled
              ? "Ask about your ATS score, projects, summary, interviews..."
              : "Upload a resume to start chatting"
          }
          className="w-full resize-none rounded-xl border border-line bg-canvas/50 px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-muted/70 focus:border-accent focus:bg-white focus:ring-2 focus:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-60"
        />
        <div className="mt-2 flex items-center justify-between gap-3">
          <p className="text-[11px] text-muted">
            Enter to send · Shift+Enter for newline
          </p>
          <button
            type="submit"
            disabled={!enabled || sending || !draft.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-60"
            aria-label="Send message"
          >
            {sending ? (
              <>
                <Spinner className="h-4 w-4 text-white" label="Sending" />
                Sending
              </>
            ) : (
              "Send"
            )}
          </button>
        </div>
      </form>
    </aside>
  );
}

export default CareerCoachPanel;
