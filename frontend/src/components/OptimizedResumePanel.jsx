import { memo, useState } from "react";
import RewriteSectionCard from "./RewriteSectionCard";
import EmptyState from "./ui/EmptyState";
import ErrorState from "./ui/ErrorState";
import Skeleton from "./ui/Skeleton";
import Spinner from "./ui/Spinner";
import {
  downloadTextFile,
  rewrittenResumeToMarkdown,
  rewrittenResumeToPlainText,
} from "../utils/resumeMarkdown";

function getSummary(rewrite) {
  return rewrite?.summary || rewrite?.professional_summary || "";
}

function BulletList({ items }) {
  return (
    <ul className="space-y-2.5 text-sm leading-relaxed text-ink">
      {items.map((item, index) => (
        <li key={index} className="flex gap-2.5">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
          <span className="min-w-0 break-words">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function OptimizedResumePanel({
  rewrite,
  analysisSummary,
  rewriting,
  rewriteError,
  onRetry,
  loading = false,
}) {
  const [copyAllLabel, setCopyAllLabel] = useState("Copy Entire Resume");

  if (loading) {
    return <Skeleton variant="rewrite" />;
  }

  if (rewriting) {
    return (
      <div
        className="flex items-center gap-3 rounded-xl bg-canvas/70 px-4 py-6 text-sm text-muted"
        role="status"
        aria-live="polite"
      >
        <Spinner label="Rewriting resume" />
        Rewriting your resume with Claude...
      </div>
    );
  }

  if (rewriteError) {
    return (
      <ErrorState
        title="Rewrite failed"
        message={rewriteError}
        onRetry={onRetry}
        retryLabel="Retry rewrite"
      />
    );
  }

  if (!rewrite) {
    return (
      <div className="space-y-3">
        {analysisSummary ? (
          <div className="animate-fade-in rounded-xl bg-canvas/70 px-4 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Analysis summary
            </p>
            <p className="mt-2 text-sm leading-relaxed text-ink whitespace-pre-wrap">
              {analysisSummary}
            </p>
          </div>
        ) : null}
        <EmptyState
          icon="rewrite"
          description="Generate an optimized version after analysis."
        />
      </div>
    );
  }

  const summary = getSummary(rewrite);
  const experience = rewrite.experience || [];
  const projects = rewrite.projects || [];
  const skills = rewrite.skills || [];
  const education = rewrite.education || [];

  const handleCopyAll = async () => {
    try {
      await navigator.clipboard.writeText(rewrittenResumeToPlainText(rewrite));
      setCopyAllLabel("Copied");
    } catch {
      setCopyAllLabel("Failed");
    }
    setTimeout(() => setCopyAllLabel("Copy Entire Resume"), 1600);
  };

  const handleDownloadMarkdown = () => {
    downloadTextFile(
      "ai-optimized-resume.md",
      rewrittenResumeToMarkdown(rewrite),
      "text/markdown"
    );
  };

  const handleDownloadTxt = () => {
    downloadTextFile(
      "ai-optimized-resume.txt",
      rewrittenResumeToPlainText(rewrite),
      "text/plain"
    );
  };

  return (
    <div className="animate-fade-in space-y-4">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Resume export actions">
        <button
          type="button"
          onClick={handleCopyAll}
          className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Copy entire optimized resume"
        >
          {copyAllLabel}
        </button>
        <button
          type="button"
          onClick={handleDownloadMarkdown}
          className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Download optimized resume as Markdown"
        >
          Download Markdown
        </button>
        <button
          type="button"
          onClick={handleDownloadTxt}
          className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Download optimized resume as text"
        >
          Download TXT
        </button>
      </div>

      <RewriteSectionCard title="Professional Summary" copyText={summary}>
        <p className="text-sm leading-relaxed break-words text-ink whitespace-pre-wrap">
          {summary}
        </p>
      </RewriteSectionCard>

      <RewriteSectionCard
        title="Experience"
        copyText={experience.map((item) => `• ${item}`).join("\n")}
      >
        {experience.length > 0 ? (
          <BulletList items={experience} />
        ) : (
          <p className="text-sm text-muted">No experience items generated.</p>
        )}
      </RewriteSectionCard>

      <RewriteSectionCard
        title="Projects"
        copyText={projects.map((item) => `• ${item}`).join("\n")}
      >
        {projects.length > 0 ? (
          <BulletList items={projects} />
        ) : (
          <p className="text-sm text-muted">No project items generated.</p>
        )}
      </RewriteSectionCard>

      <RewriteSectionCard title="Skills" copyText={skills.join(", ")}>
        {skills.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {skills.map((skill, index) => (
              <span
                key={`${skill}-${index}`}
                className="rounded-lg bg-accent-soft px-3 py-1 text-xs font-medium text-accent-strong"
              >
                {skill}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No skills generated.</p>
        )}
      </RewriteSectionCard>

      <RewriteSectionCard
        title="Education"
        copyText={education.map((item) => `• ${item}`).join("\n")}
      >
        {education.length > 0 ? (
          <BulletList items={education} />
        ) : (
          <p className="text-sm text-muted">No education items generated.</p>
        )}
      </RewriteSectionCard>
    </div>
  );
}

export default memo(OptimizedResumePanel);
