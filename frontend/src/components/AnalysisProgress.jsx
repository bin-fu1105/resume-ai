import Spinner from "./ui/Spinner";

const STAGES = [
  "Uploading Resume...",
  "Parsing Resume...",
  "Running ATS Analysis...",
  "Generating Suggestions...",
];

function AnalysisProgress({ stageIndex }) {
  const progress = ((stageIndex + 1) / STAGES.length) * 100;

  return (
    <section
      className="panel-card animate-fade-up mt-6"
      aria-live="polite"
      aria-busy="true"
      aria-label="Analysis progress"
    >
      <div className="flex items-start gap-4">
        <Spinner className="h-6 w-6 text-accent" label="Analyzing" />
        <div className="min-w-0 flex-1">
          <p className="font-display text-sm font-semibold text-ink">
            Analyzing your resume
          </p>
          <p className="mt-1 text-sm text-muted">{STAGES[stageIndex]}</p>

          <div className="mt-4 h-2 overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
              style={{ width: `${progress}%` }}
              role="progressbar"
              aria-valuenow={Math.round(progress)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Analysis progress"
            />
          </div>

          <ol className="mt-5 space-y-2">
            {STAGES.map((stage, index) => {
              const isDone = index < stageIndex;
              const isActive = index === stageIndex;

              return (
                <li
                  key={stage}
                  className={`flex items-center gap-2 text-sm transition-colors ${
                    isActive
                      ? "font-medium text-ink"
                      : isDone
                        ? "text-accent"
                        : "text-muted/70"
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold ${
                      isDone
                        ? "bg-accent text-white"
                        : isActive
                          ? "bg-accent-soft text-accent"
                          : "bg-canvas text-muted"
                    }`}
                    aria-hidden="true"
                  >
                    {isDone ? (
                      <svg
                        className="h-3 w-3"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.704 5.29a1 1 0 010 1.42l-7.25 7.25a1 1 0 01-1.414 0l-3.25-3.25a1 1 0 011.414-1.42l2.543 2.544 6.543-6.544a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      index + 1
                    )}
                  </span>
                  {stage.replace("...", "")}
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </section>
  );
}

export { STAGES };
export default AnalysisProgress;
