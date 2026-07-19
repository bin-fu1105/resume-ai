import ResultCard from "./ResultCard";
import AtsScorePanel from "./AtsScorePanel";
import ResumeMatchPanel from "./ResumeMatchPanel";
import MissingSkillsPanel from "./MissingSkillsPanel";
import SuggestionsPanel from "./SuggestionsPanel";
import OptimizedResumePanel from "./OptimizedResumePanel";

function ResultsSection({
  loading,
  rewriting,
  hasResults,
  score,
  atsExplanation,
  dimensions,
  strengths,
  missingSkills,
  suggestions,
  optimizedSummary,
  rewrittenResume,
  rewriteError,
  onRetryRewrite,
  resultsRef,
}) {
  return (
    <section id="results" ref={resultsRef} className="mt-2 scroll-mt-24">
      <div className="mb-5">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-accent">
          Insights
        </p>
        <h2 className="font-display text-xl font-semibold tracking-tight text-ink sm:text-2xl">
          Analysis Results
        </h2>
        <p className="mt-1 text-sm text-muted">
          {loading
            ? "Generating your ATS insights..."
            : hasResults
              ? "Your personalized ATS insights are ready."
              : "Run analysis to unlock scored insights and suggestions."}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:gap-5 md:grid-cols-2 xl:grid-cols-3">
        <ResultCard
          title="ATS Score"
          description="Overall resume readiness for applicant tracking systems."
          animate={hasResults || loading}
          delay={0}
        >
          <AtsScorePanel
            score={hasResults ? score : null}
            explanation={hasResults ? atsExplanation : ""}
            loading={loading}
          />
        </ResultCard>

        <ResultCard
          title="Resume Match"
          description="How well your experience aligns with the target role."
          animate={hasResults || loading}
          delay={80}
        >
          <ResumeMatchPanel
            dimensions={hasResults ? dimensions : {}}
            loading={loading}
          />
          {hasResults && !loading && strengths.length > 0 && (
            <div className="mt-5 border-t border-line pt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
                Strengths
              </p>
              <ul className="space-y-3 text-sm text-muted">
                {strengths.map((item, index) => {
                  const title =
                    typeof item === "string"
                      ? item
                      : item?.title || item?.strength || "";
                  const reason =
                    typeof item === "string" ? "" : item?.reason || "";

                  return (
                    <li key={index} className="leading-relaxed">
                      <p className="font-medium text-ink">{title}</p>
                      {reason && <p className="mt-1 break-words">{reason}</p>}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </ResultCard>

        <ResultCard
          title="Missing Skills"
          description="Skills and keywords that may be absent from your resume."
          animate={hasResults || loading}
          delay={160}
          className="md:col-span-2 xl:col-span-1"
        >
          <MissingSkillsPanel
            items={hasResults ? missingSkills : []}
            loading={loading}
          />
        </ResultCard>

        <ResultCard
          title="Suggestions"
          description="Actionable edits to improve clarity and impact."
          className="md:col-span-2 xl:col-span-3"
          animate={hasResults || loading}
          delay={240}
        >
          <SuggestionsPanel
            items={hasResults ? suggestions : []}
            loading={loading}
          />
        </ResultCard>

        <ResultCard
          title="AI Optimized Resume"
          description="Claude-rewritten summary, experience, projects, and skills."
          className="md:col-span-2 xl:col-span-3"
          animate={hasResults || rewriting || loading}
          delay={320}
        >
          <OptimizedResumePanel
            rewrite={rewrittenResume}
            analysisSummary={hasResults ? optimizedSummary : ""}
            rewriting={rewriting}
            rewriteError={rewriteError}
            onRetry={onRetryRewrite}
            loading={loading && !rewriting}
          />
        </ResultCard>
      </div>
    </section>
  );
}

export default ResultsSection;
