import { useMemo, useState } from "react";
import EmptyState from "./ui/EmptyState";
import ErrorState from "./ui/ErrorState";
import Skeleton from "./ui/Skeleton";
import Spinner from "./ui/Spinner";
import { getScoreStatus } from "../utils/scoreStatus";
import { toFriendlyError } from "../utils/friendlyError";
import { API_BASE } from "../utils/uploadFile";

const MAX_JOBS = 5;

function emptyJob(index = 0) {
  return {
    id: `${Date.now()}-${index}-${Math.random().toString(36).slice(2, 7)}`,
    company: "",
    job_description: "",
  };
}

function JobCard({ result, isBest, rank }) {
  const status = getScoreStatus(result.score ?? 0);
  const topStrength = result.strengths?.[0] || "No standout strength listed.";
  const topMissing = result.missing_skills?.[0] || "No major gaps listed.";

  return (
    <article
      className={`panel-card animate-fade-up transition duration-300 ${
        isBest
          ? "border-accent ring-2 ring-accent/25 shadow-md"
          : "hover:border-accent/30"
      }`}
      style={{ animationDelay: `${rank * 60}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-lg font-semibold text-ink">
              {result.company}
            </h3>
            {isBest && (
              <span className="rounded-full bg-accent px-2.5 py-0.5 text-[11px] font-semibold text-white">
                Best match
              </span>
            )}
          </div>
          <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted">
            Rank #{rank + 1}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">
            ATS Score
          </p>
          <p className={`font-display text-3xl font-semibold ${status.textClass}`}>
            {result.score ?? 0}
          </p>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-1.5 flex items-center justify-between text-xs">
          <span className="font-semibold text-muted">Resume Match</span>
          <span className="font-semibold text-ink">
            {result.resume_match ?? 0}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-line/80">
          <div
            className={`h-full rounded-full transition-[width] duration-700 ease-out ${status.barClass}`}
            style={{ width: `${result.resume_match ?? 0}%` }}
          />
        </div>
      </div>

      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
            Top strength
          </dt>
          <dd className="mt-1 leading-relaxed text-ink">{topStrength}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
            Top missing skill
          </dt>
          <dd className="mt-1 leading-relaxed text-ink">{topMissing}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
            Recommendation
          </dt>
          <dd className="mt-1 leading-relaxed text-ink">
            {result.recommendation || status.explanation}
          </dd>
        </div>
      </dl>

      {result.summary && (
        <p className="mt-4 border-t border-line pt-3 text-sm leading-relaxed text-muted">
          {result.summary}
        </p>
      )}
    </article>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4" aria-label="Comparing jobs">
      <div className="panel-card">
        <Skeleton variant="score" />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[1, 2, 3].map((key) => (
          <div key={key} className="panel-card">
            <Skeleton variant="list" />
          </div>
        ))}
      </div>
    </div>
  );
}

function JobCompareView({ filename, enabled }) {
  const [jobs, setJobs] = useState([emptyJob(0), emptyJob(1)]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sortBy, setSortBy] = useState("score"); // score | company | match
  const [payload, setPayload] = useState(null);

  const sortedResults = useMemo(() => {
    const results = [...(payload?.results || [])];
    if (sortBy === "company") {
      results.sort((a, b) =>
        String(a.company).localeCompare(String(b.company), undefined, {
          sensitivity: "base",
        })
      );
    } else if (sortBy === "match") {
      results.sort(
        (a, b) => (b.resume_match ?? 0) - (a.resume_match ?? 0)
      );
    } else {
      results.sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
    }
    return results;
  }, [payload, sortBy]);

  const updateJob = (id, field, value) => {
    setJobs((current) =>
      current.map((job) =>
        job.id === id ? { ...job, [field]: value } : job
      )
    );
  };

  const addJob = () => {
    if (jobs.length >= MAX_JOBS) return;
    setJobs((current) => [...current, emptyJob(current.length)]);
  };

  const removeJob = (id) => {
    setJobs((current) =>
      current.length <= 1 ? current : current.filter((job) => job.id !== id)
    );
  };

  const runCompare = async () => {
    if (!enabled || !filename) {
      setError("Upload a resume first to compare jobs.");
      return;
    }

    const cleaned = jobs
      .map((job, index) => ({
        company: job.company.trim() || `Job ${index + 1}`,
        job_description: job.job_description.trim(),
      }))
      .filter((job) => job.job_description);

    if (cleaned.length < 1) {
      setError("Add at least one job description.");
      return;
    }

    if (cleaned.length > MAX_JOBS) {
      setError(`Compare up to ${MAX_JOBS} jobs at a time.`);
      return;
    }

    setLoading(true);
    setError("");
    setPayload(null);

    try {
      const response = await fetch(`${API_BASE}/compare-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename,
          jobs: cleaned,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          toFriendlyError(
            data.detail || data.error || data,
            "We couldn't compare these jobs. Please try again."
          )
        );
      }

      if (!Array.isArray(data.results) || data.results.length === 0) {
        throw new Error("No comparison results were returned.");
      }

      setPayload(data);
      setSortBy("score");
    } catch (err) {
      setError(
        toFriendlyError(
          err,
          "We couldn't compare these jobs. Please try again."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  if (!enabled) {
    return (
      <section id="jobs" className="panel-card scroll-mt-24">
        <EmptyState
          icon="match"
          title="Job Comparison"
          description="Upload a resume to compare it against up to five job descriptions."
        />
      </section>
    );
  }

  return (
    <section id="jobs" className="space-y-4 scroll-mt-24" aria-label="Job comparison">
      <div className="panel-card animate-fade-up">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
          Job Match
        </p>
        <h2 className="mt-2 font-display text-xl font-semibold tracking-tight text-ink">
          Multiple Job Description Comparison
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Run the same ATS engine against up to five roles and see which company
          is the strongest fit for your resume.
        </p>

        <div className="mt-5 space-y-4">
          {jobs.map((job, index) => (
            <div
              key={job.id}
              className="rounded-2xl border border-line bg-canvas/40 p-4 transition hover:border-accent/25"
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-ink">
                  Job {index + 1}
                </p>
                {jobs.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeJob(job.id)}
                    className="text-xs font-semibold text-muted transition hover:text-rose-700"
                  >
                    Remove
                  </button>
                )}
              </div>
              <label className="block text-xs font-semibold uppercase tracking-wide text-muted">
                Company
                <input
                  type="text"
                  value={job.company}
                  onChange={(event) =>
                    updateJob(job.id, "company", event.target.value)
                  }
                  placeholder="e.g. Amazon"
                  className="mt-1.5 w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20"
                />
              </label>
              <label className="mt-3 block text-xs font-semibold uppercase tracking-wide text-muted">
                Job description
                <textarea
                  value={job.job_description}
                  onChange={(event) =>
                    updateJob(job.id, "job_description", event.target.value)
                  }
                  rows={4}
                  placeholder="Paste the job description..."
                  className="mt-1.5 w-full resize-y rounded-xl border border-line bg-white px-3 py-2.5 text-sm leading-relaxed text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20"
                />
              </label>
            </div>
          ))}
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <button
            type="button"
            onClick={runCompare}
            disabled={loading}
            className="btn-primary"
          >
            {loading ? (
              <>
                <Spinner className="h-4 w-4 text-white" label="Comparing" />
                Comparing jobs...
              </>
            ) : (
              "Compare jobs"
            )}
          </button>
          <button
            type="button"
            onClick={addJob}
            disabled={loading || jobs.length >= MAX_JOBS}
            className="btn-secondary"
          >
            Add job ({jobs.length}/{MAX_JOBS})
          </button>
        </div>
      </div>

      {error && (
        <ErrorState
          title="Job comparison failed"
          message={error}
          onRetry={runCompare}
          retryLabel="Retry comparison"
        />
      )}

      {loading && <LoadingSkeleton />}

      {!loading && payload && (
        <>
          <div className="panel-card animate-fade-up border-accent/30 bg-gradient-to-br from-accent-soft/50 to-white">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
              Best Match
            </p>
            <h3 className="mt-2 font-display text-2xl font-semibold text-ink">
              {payload.best_match}
            </h3>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
              <span className="font-semibold text-ink">Reason</span>
              <br />
              {payload.reason}
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted">
              {sortedResults.length} role
              {sortedResults.length === 1 ? "" : "s"} ranked
            </p>
            <label className="inline-flex items-center gap-2 text-sm text-muted">
              Sort by
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value)}
                className="rounded-lg border border-line bg-white px-2.5 py-1.5 text-sm font-semibold text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              >
                <option value="score">ATS score</option>
                <option value="match">Resume match</option>
                <option value="company">Company</option>
              </select>
            </label>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {sortedResults.map((result, index) => (
              <JobCard
                key={`${result.company}-${index}`}
                result={result}
                isBest={result.company === payload.best_match}
                rank={index}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export default JobCompareView;
