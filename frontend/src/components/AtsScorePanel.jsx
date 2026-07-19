import { memo, useEffect, useState } from "react";
import { getScoreStatus } from "../utils/scoreStatus";
import EmptyState from "./ui/EmptyState";
import Skeleton from "./ui/Skeleton";

function AtsScorePanel({ score, explanation = "", loading = false }) {
  const [displayWidth, setDisplayWidth] = useState(0);

  useEffect(() => {
    if (score === null || score === undefined) {
      setDisplayWidth(0);
      return;
    }

    setDisplayWidth(0);
    const frame = requestAnimationFrame(() => {
      setDisplayWidth(score);
    });

    return () => cancelAnimationFrame(frame);
  }, [score]);

  if (loading) {
    return <Skeleton variant="score" />;
  }

  if (score === null || score === undefined) {
    return (
      <EmptyState
        icon="score"
        description="Upload and analyze your resume to see your ATS score."
      />
    );
  }

  const status = getScoreStatus(score);

  return (
    <div className="animate-fade-in text-center">
      <div
        className={`mx-auto inline-flex rounded-full px-3 py-1 text-xs font-semibold tracking-wide ${status.badgeClass}`}
      >
        {status.label}
      </div>

      <p
        className={`mt-4 font-display text-5xl font-semibold leading-none tracking-tight sm:text-6xl lg:text-7xl ${status.textClass}`}
        aria-label={`ATS score ${score} out of 100`}
      >
        {score}
      </p>

      <div className="mx-auto mt-5 h-2.5 max-w-xs overflow-hidden rounded-full bg-line">
        <div
          className={`h-full rounded-full transition-[width] duration-1000 ease-out ${status.barClass}`}
          style={{ width: `${displayWidth}%` }}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      <p className="mx-auto mt-4 max-w-sm text-sm leading-relaxed text-muted">
        {explanation || status.explanation}
      </p>
    </div>
  );
}

export default memo(AtsScorePanel);
