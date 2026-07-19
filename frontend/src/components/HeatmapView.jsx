import { useEffect, useState } from "react";
import EmptyState from "./ui/EmptyState";
import Spinner from "./ui/Spinner";
import { getScoreStatus } from "../utils/scoreStatus";
import { getSectionHeat, SECTION_META } from "../utils/sectionScore";

const SEVERITY_STYLES = {
  high: "bg-rose-100 text-rose-800",
  medium: "bg-amber-100 text-amber-900",
  low: "bg-sky-100 text-sky-800",
};

function AnimatedBar({ value, barClass }) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    setWidth(0);
    const frame = requestAnimationFrame(() => setWidth(value));
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return (
    <div className="h-2.5 overflow-hidden rounded-full bg-white/80">
      <div
        className={`h-full rounded-full transition-[width] duration-1000 ease-out ${barClass}`}
        style={{ width: `${width}%` }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
      />
    </div>
  );
}

function DetailList({ title, items }) {
  if (!items?.length) {
    return (
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
          {title}
        </p>
        <p className="mt-1 text-sm text-muted">None listed.</p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">
        {title}
      </p>
      <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-ink">
        {items.map((item, index) => (
          <li key={`${title}-${index}`} className="flex gap-2">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SectionCard({
  meta,
  section,
  expanded,
  onToggle,
  onRewriteSection,
  rewriting,
  rewriteSection,
}) {
  const score = section?.score ?? 0;
  const heat = getSectionHeat(score);
  const isRewritingThis = rewriting && rewriteSection === meta.id;

  return (
    <article
      className={`group overflow-hidden rounded-2xl border shadow-sm transition duration-300 ${heat.cardClass}`}
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full px-4 py-4 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        aria-expanded={expanded}
        title={heat.tooltip}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-display text-base font-semibold text-ink">
                {meta.title}
              </h3>
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${heat.badgeClass}`}
              >
                {heat.label}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">{meta.description}</p>
          </div>
          <p className={`font-display text-3xl font-semibold ${heat.textClass}`}>
            {score}
          </p>
        </div>

        <div className="mt-4">
          <AnimatedBar value={score} barClass={heat.barClass} />
        </div>

        <p className="mt-3 text-xs font-medium text-muted transition group-hover:text-ink">
          {expanded ? "Hide details" : "View strengths, issues, and fixes"}
        </p>
      </button>

      <div
        className={`grid transition-all duration-300 ease-out ${
          expanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden">
          <div className="space-y-4 border-t border-black/5 px-4 py-4">
            <DetailList title="Strengths" items={section?.strengths || []} />
            <DetailList title="Weaknesses" items={section?.weaknesses || []} />

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Issues
              </p>
              {(section?.issues || []).length === 0 ? (
                <p className="mt-1 text-sm text-muted">No major issues flagged.</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {section.issues.map((issue, index) => (
                    <li
                      key={`${meta.id}-issue-${index}`}
                      className="rounded-xl bg-white/70 px-3 py-2 text-sm"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink">
                          {issue.type || "issue"}
                        </span>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ${
                            SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.medium
                          }`}
                        >
                          {issue.severity || "medium"}
                        </span>
                      </div>
                      <p className="mt-1 leading-relaxed text-muted">
                        {issue.description}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <DetailList
              title="Suggested improvements"
              items={section?.suggested_improvements || []}
            />

            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onRewriteSection(meta.id);
              }}
              disabled={rewriting}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-60"
              aria-label={`Rewrite ${meta.title} section`}
            >
              {isRewritingThis ? (
                <>
                  <Spinner className="h-4 w-4 text-white" label="Rewriting section" />
                  Rewriting {meta.title}...
                </>
              ) : (
                `Rewrite this section`
              )}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

function HeatmapView({
  enabled,
  overallScore,
  atsExplanation,
  sections,
  onRewriteSection,
  rewriting,
  rewriteSection,
}) {
  const [expandedId, setExpandedId] = useState(null);
  const status = getScoreStatus(overallScore ?? 0);

  if (!enabled) {
    return (
      <section id="heatmap" className="panel-card scroll-mt-24">
        <EmptyState
          icon="score"
          description="Run analysis to unlock the ATS heatmap breakdown."
        />
      </section>
    );
  }

  return (
    <section id="heatmap" className="space-y-4 scroll-mt-24" aria-label="ATS heatmap">
      <div className="panel-card animate-fade-up">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
          Heatmap
        </p>
        <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold tracking-tight text-ink">
              ATS Section Breakdown
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-muted">
              {atsExplanation || status.explanation}
            </p>
          </div>
          <div className="text-left sm:text-right">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Overall ATS Score
            </p>
            <p className={`font-display text-5xl font-semibold ${status.textClass}`}>
              {overallScore ?? 0}
            </p>
          </div>
        </div>
        <div className="mt-4">
          <AnimatedBar
            value={overallScore ?? 0}
            barClass={status.barClass}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {SECTION_META.map((meta) => (
          <SectionCard
            key={meta.id}
            meta={meta}
            section={sections?.[meta.id] || { score: 0, issues: [] }}
            expanded={expandedId === meta.id}
            onToggle={() =>
              setExpandedId((current) => (current === meta.id ? null : meta.id))
            }
            onRewriteSection={onRewriteSection}
            rewriting={rewriting}
            rewriteSection={rewriteSection}
          />
        ))}
      </div>
    </section>
  );
}

export default HeatmapView;
