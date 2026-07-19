import { memo, useEffect, useState } from "react";
import EmptyState from "./ui/EmptyState";
import Skeleton from "./ui/Skeleton";

function MatchBar({ label, value, delay }) {
  const [width, setWidth] = useState(0);
  const percent = Math.max(0, Math.min(100, Number(value) || 0));

  useEffect(() => {
    setWidth(0);
    const timer = setTimeout(() => setWidth(percent), 80 + delay);
    return () => clearTimeout(timer);
  }, [percent, delay]);

  return (
    <div className="animate-fade-up" style={{ animationDelay: `${delay}ms` }}>
      <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-ink">{label}</span>
        <span className="tabular-nums text-muted" aria-hidden="true">
          {percent}%
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-line">
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-700 ease-out"
          style={{ width: `${width}%` }}
          role="progressbar"
          aria-label={`${label} match`}
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}

function ResumeMatchPanel({ dimensions, loading = false }) {
  const entries = Object.entries(dimensions || {});

  if (loading) {
    return <Skeleton variant="bars" />;
  }

  if (entries.length === 0) {
    return (
      <EmptyState
        icon="match"
        description="Upload and analyze your resume to see dimension-by-dimension match scores."
      />
    );
  }

  return (
    <div className="animate-fade-in space-y-4">
      {entries.map(([key, value], index) => (
        <MatchBar
          key={key}
          label={key.charAt(0).toUpperCase() + key.slice(1)}
          value={value}
          delay={index * 90}
        />
      ))}
    </div>
  );
}

export default memo(ResumeMatchPanel);
