import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import EmptyState from "./ui/EmptyState";
import ErrorState from "./ui/ErrorState";
import Spinner from "./ui/Spinner";
import { getScoreStatus } from "../utils/scoreStatus";
import { toFriendlyError } from "../utils/friendlyError";
import { API_BASE } from "../utils/uploadFile";

function TypingIndicator({ label = "Evaluating answer" }) {
  return (
    <div
      className="flex items-center gap-1 rounded-2xl bg-canvas px-4 py-3"
      role="status"
      aria-label={label}
    >
      <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:-0.2s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:-0.1s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-accent" />
      <span className="ml-2 text-xs font-medium text-muted">{label}...</span>
    </div>
  );
}

function ProgressBar({ value, max }) {
  const percent = max > 0 ? Math.round((value / max) * 100) : 0;

  return (
    <div className="h-2.5 overflow-hidden rounded-full bg-line/80">
      <div
        className="h-full rounded-full bg-accent transition-[width] duration-700 ease-out"
        style={{ width: `${percent}%` }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      />
    </div>
  );
}

function BulletList({ title, items, tone = "default" }) {
  if (!items?.length) return null;

  const dotClass =
    tone === "good"
      ? "bg-emerald-500"
      : tone === "warn"
        ? "bg-amber-500"
        : tone === "bad"
          ? "bg-rose-500"
          : "bg-accent";

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">
        {title}
      </p>
      <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-ink">
        {items.map((item, index) => (
          <li key={`${title}-${index}`} className="flex gap-2">
            <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${dotClass}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ScoreChip({ score }) {
  const status = getScoreStatus(score ?? 0);
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${status.badgeClass}`}
    >
      {score ?? 0}
    </span>
  );
}

function InterviewView({ filename, jobDescription, enabled }) {
  const [phase, setPhase] = useState("idle"); // idle | starting | active | summarizing | summary
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState("main"); // main | followup
  const [activeQuestion, setActiveQuestion] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [latestResult, setLatestResult] = useState(null);
  const [turns, setTurns] = useState([]);
  const [scoreHistory, setScoreHistory] = useState([]);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const answerRef = useRef(null);
  const feedbackRef = useRef(null);

  const total = questions.length;
  const current = questions[currentIndex] || null;
  const progressValue =
    phase === "summary" ? total : Math.min(currentIndex + (latestResult ? 1 : 0), total);

  const averageScore = useMemo(() => {
    if (!scoreHistory.length) return null;
    const sum = scoreHistory.reduce((acc, item) => acc + item.score, 0);
    return Math.round(sum / scoreHistory.length);
  }, [scoreHistory]);

  useEffect(() => {
    if (latestResult) {
      feedbackRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [latestResult]);

  const resetSession = () => {
    setPhase("idle");
    setQuestions([]);
    setCurrentIndex(0);
    setDraft("");
    setMode("main");
    setActiveQuestion("");
    setEvaluating(false);
    setLatestResult(null);
    setTurns([]);
    setScoreHistory([]);
    setSummary(null);
    setError("");
  };

  const startInterview = async () => {
    if (!enabled || !filename) {
      setError("Upload a resume first to start the interview.");
      return;
    }

    setPhase("starting");
    setError("");
    setQuestions([]);
    setCurrentIndex(0);
    setDraft("");
    setMode("main");
    setActiveQuestion("");
    setLatestResult(null);
    setTurns([]);
    setScoreHistory([]);
    setSummary(null);

    try {
      const response = await fetch(`${API_BASE}/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename,
          job_description: jobDescription || "",
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          toFriendlyError(
            data.detail || data.error || data,
            "We couldn't start the interview. Please try again."
          )
        );
      }

      const list = Array.isArray(data.questions) ? data.questions : [];
      if (list.length < 1) {
        throw new Error("No interview questions were generated.");
      }

      setQuestions(list);
      setActiveQuestion(list[0].question);
      setMode("main");
      setPhase("active");
      requestAnimationFrame(() => answerRef.current?.focus());
    } catch (err) {
      setError(
        toFriendlyError(
          err,
          "We couldn't start the interview. Please try again."
        )
      );
      setPhase("idle");
    }
  };

  const submitAnswer = async () => {
    const answer = draft.trim();
    if (!answer || evaluating || !activeQuestion) return;

    setEvaluating(true);
    setError("");

    const historyPayload = turns.map((turn) => ({
      question: turn.question,
      answer: turn.answer,
      score: turn.score,
    }));

    try {
      const response = await fetch(`${API_BASE}/interview/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          history: historyPayload,
          question: activeQuestion,
          answer,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          toFriendlyError(
            data.detail || data.error || data,
            "We couldn't evaluate that answer. Please try again."
          )
        );
      }

      const result = {
        score: data.score ?? 0,
        feedback: data.feedback || {
          strengths: [],
          weaknesses: [],
          improvements: [],
        },
        follow_up: data.follow_up || "",
      };

      const turn = {
        questionId: current?.id,
        category: current?.category || "Behavioral",
        question: activeQuestion,
        answer,
        score: result.score,
        feedback: result.feedback,
        follow_up: result.follow_up,
        isFollowUp: mode === "followup",
      };

      setTurns((prev) => [...prev, turn]);
      setScoreHistory((prev) => [
        ...prev,
        {
          label:
            mode === "followup"
              ? `Q${currentIndex + 1} follow-up`
              : `Q${currentIndex + 1}`,
          score: result.score,
        },
      ]);
      setLatestResult(result);
      setDraft("");
    } catch (err) {
      setError(
        toFriendlyError(
          err,
          "We couldn't evaluate that answer. Please try again."
        )
      );
    } finally {
      setEvaluating(false);
    }
  };

  const answerFollowUp = () => {
    if (!latestResult?.follow_up) return;
    setMode("followup");
    setActiveQuestion(latestResult.follow_up);
    setLatestResult(null);
    setDraft("");
    requestAnimationFrame(() => answerRef.current?.focus());
  };

  const finishInterview = async (finalTurns) => {
    setPhase("summarizing");
    setError("");

    try {
      const response = await fetch(`${API_BASE}/interview/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename,
          job_description: jobDescription || "",
          turns: finalTurns.map((turn) => ({
            question: turn.question,
            answer: turn.answer,
            score: turn.score,
            feedback: turn.feedback,
          })),
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          toFriendlyError(
            data.detail || data.error || data,
            "We couldn't generate the final report. Please try again."
          )
        );
      }

      setSummary(data);
      setPhase("summary");
    } catch (err) {
      setError(
        toFriendlyError(
          err,
          "We couldn't generate the final report. Please try again."
        )
      );
      setPhase("active");
    }
  };

  const goNextQuestion = async () => {
    const nextIndex = currentIndex + 1;
    if (nextIndex >= total) {
      await finishInterview(turns);
      return;
    }

    setCurrentIndex(nextIndex);
    setActiveQuestion(questions[nextIndex].question);
    setMode("main");
    setLatestResult(null);
    setDraft("");
    requestAnimationFrame(() => answerRef.current?.focus());
  };

  if (!enabled) {
    return (
      <section id="interview" className="panel-card scroll-mt-24">
        <EmptyState
          icon="suggestions"
          title="Interview Simulator"
          description="Upload a resume to unlock AI interview practice tailored to your background and target role."
        />
      </section>
    );
  }

  if (phase === "idle") {
    return (
      <section id="interview" className="space-y-4 scroll-mt-24">
        <div className="panel-card animate-fade-up">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
            Interview
          </p>
          <h2 className="mt-2 font-display text-xl font-semibold tracking-tight text-ink">
            AI Interview Simulator
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
            Practice 8–10 behavioral and technical questions grounded in your
            resume and job description. Get scored feedback, follow-ups, and a
            final coaching report.
          </p>
          <button
            type="button"
            onClick={startInterview}
            className="btn-primary mt-5"
          >
            Start Interview
          </button>
          {error && (
            <div className="mt-4">
              <ErrorState
                title="Could not start interview"
                message={error}
                onRetry={startInterview}
                retryLabel="Try again"
              />
            </div>
          )}
        </div>
      </section>
    );
  }

  if (phase === "starting" || phase === "summarizing") {
    return (
      <section id="interview" className="panel-card scroll-mt-24">
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <Spinner className="h-8 w-8 text-accent" label="Loading interview" />
          <p className="font-display text-base font-semibold text-ink">
            {phase === "starting"
              ? "Generating interview questions..."
              : "Building your final report..."}
          </p>
          <p className="text-sm text-muted">
            Claude is preparing personalized coaching.
          </p>
        </div>
      </section>
    );
  }

  if (phase === "summary" && summary) {
    const status = getScoreStatus(summary.overall_score ?? averageScore ?? 0);

    return (
      <section id="interview" className="space-y-4 scroll-mt-24">
        <div className="panel-card animate-fade-up">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
            Final Report
          </p>
          <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="font-display text-xl font-semibold text-ink">
                Interview Summary
              </h2>
              <p className="mt-1 text-sm text-muted">
                Completed {total} questions with {scoreHistory.length} scored
                responses.
              </p>
            </div>
            <div className="text-left sm:text-right">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Overall Score
              </p>
              <p className={`font-display text-5xl font-semibold ${status.textClass}`}>
                {summary.overall_score ?? averageScore ?? 0}
              </p>
            </div>
          </div>
          <div className="mt-4">
            <ProgressBar value={total} max={total} />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="panel-card animate-fade-up">
            <BulletList
              title="Strengths"
              items={summary.strengths}
              tone="good"
            />
          </div>
          <div className="panel-card animate-fade-up">
            <BulletList
              title="Weaknesses"
              items={summary.weaknesses}
              tone="bad"
            />
          </div>
          <div className="panel-card animate-fade-up md:col-span-2">
            <BulletList
              title="Top 5 improvements"
              items={summary.improvements}
              tone="warn"
            />
          </div>
          <div className="panel-card animate-fade-up md:col-span-2">
            <BulletList
              title="Recommended learning topics"
              items={summary.learning_topics}
            />
          </div>
        </div>

        {scoreHistory.length > 0 && (
          <div className="panel-card animate-fade-up">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Score history
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {scoreHistory.map((item, index) => (
                <span
                  key={`${item.label}-${index}`}
                  className="inline-flex items-center gap-2 rounded-xl border border-line bg-canvas/60 px-3 py-1.5 text-xs font-medium text-ink"
                >
                  {item.label}
                  <ScoreChip score={item.score} />
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <button type="button" onClick={resetSession} className="btn-primary">
            Practice again
          </button>
        </div>
      </section>
    );
  }

  const waitingForAnswer = !latestResult && !evaluating;
  const showingFeedback = Boolean(latestResult) && !evaluating;

  return (
    <section id="interview" className="space-y-4 scroll-mt-24" aria-label="Interview simulator">
      <div className="panel-card animate-fade-up">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
              Interview in progress
            </p>
            <h2 className="mt-1 font-display text-lg font-semibold text-ink">
              Question {Math.min(currentIndex + 1, total)} / {total}
            </h2>
          </div>
          {averageScore !== null && (
            <p className="text-sm text-muted">
              Session avg <ScoreChip score={averageScore} />
            </p>
          )}
        </div>
        <div className="mt-4">
          <ProgressBar value={progressValue} max={total || 1} />
        </div>
        {scoreHistory.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {scoreHistory.map((item, index) => (
              <span
                key={`${item.label}-${index}`}
                className="inline-flex items-center gap-1.5 rounded-lg bg-canvas px-2.5 py-1 text-[11px] font-semibold text-muted"
              >
                {item.label}
                <ScoreChip score={item.score} />
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="panel-card animate-fade-up">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-accent-soft px-2.5 py-0.5 text-[11px] font-semibold text-accent-strong">
            {mode === "followup" ? "Follow-up" : current?.category || "Question"}
          </span>
          {mode === "main" && current && (
            <span className="text-xs text-muted">#{current.id}</span>
          )}
        </div>
        <h3 className="mt-3 font-display text-lg font-semibold leading-snug text-ink">
          {activeQuestion}
        </h3>

        {waitingForAnswer && (
          <div className="mt-5">
            <label htmlFor="interview-answer" className="sr-only">
              Your answer
            </label>
            <textarea
              id="interview-answer"
              ref={answerRef}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              rows={6}
              placeholder="Type your answer. Use STAR where you can: Situation, Task, Action, Result."
              className="w-full resize-y rounded-xl border border-line bg-white px-4 py-3 text-sm leading-relaxed text-ink shadow-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
            <div className="mt-3 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={submitAnswer}
                disabled={!draft.trim() || evaluating}
                className="btn-primary"
              >
                Submit answer
              </button>
              {mode === "followup" && (
                <button
                  type="button"
                  onClick={goNextQuestion}
                  className="btn-secondary"
                >
                  Skip follow-up
                </button>
              )}
            </div>
          </div>
        )}

        {evaluating && (
          <div className="mt-5">
            <TypingIndicator label="Scoring your answer" />
          </div>
        )}

        {showingFeedback && (
          <div ref={feedbackRef} className="mt-5 space-y-4 animate-fade-in">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line bg-canvas/70 px-4 py-3">
              <p className="text-sm font-semibold text-ink">AI Feedback</p>
              <ScoreChip score={latestResult.score} />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <BulletList
                title="Strengths"
                items={latestResult.feedback?.strengths}
                tone="good"
              />
              <BulletList
                title="Weaknesses"
                items={latestResult.feedback?.weaknesses}
                tone="bad"
              />
              <BulletList
                title="Improvements"
                items={latestResult.feedback?.improvements}
                tone="warn"
              />
            </div>

            {latestResult.follow_up && mode === "main" && (
              <div className="rounded-xl border border-accent/20 bg-accent-soft/40 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-accent-strong">
                  Follow-up question
                </p>
                <div className="chat-markdown mt-2 text-sm text-ink">
                  <ReactMarkdown>{latestResult.follow_up}</ReactMarkdown>
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              {latestResult.follow_up && mode === "main" && (
                <button
                  type="button"
                  onClick={answerFollowUp}
                  className="btn-primary"
                >
                  Answer follow-up
                </button>
              )}
              <button
                type="button"
                onClick={goNextQuestion}
                className={
                  latestResult.follow_up && mode === "main"
                    ? "btn-secondary"
                    : "btn-primary"
                }
              >
                {currentIndex + 1 >= total ? "View final report" : "Next question"}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4">
            <ErrorState
              title="Interview step failed"
              message={error}
              onRetry={
                evaluating || latestResult ? undefined : () => submitAnswer()
              }
              retryLabel="Retry"
            />
          </div>
        )}
      </div>
    </section>
  );
}

export default InterviewView;
