function SkeletonBlock({ className = "" }) {
  return <div className={`skeleton-block ${className}`} aria-hidden="true" />;
}

function Skeleton({ variant = "card", className = "" }) {
  if (variant === "score") {
    return (
      <div
        className={`animate-fade-up space-y-4 py-2 ${className}`}
        role="status"
        aria-label="Loading ATS score"
      >
        <div className="flex justify-center">
          <SkeletonBlock className="h-6 w-20 rounded-full" />
        </div>
        <div className="flex justify-center">
          <SkeletonBlock className="h-16 w-24 rounded-xl" />
        </div>
        <SkeletonBlock className="mx-auto h-2.5 w-full max-w-xs rounded-full" />
        <SkeletonBlock className="mx-auto h-4 w-full max-w-sm rounded-lg" />
        <SkeletonBlock className="mx-auto h-4 w-48 max-w-full rounded-lg" />
      </div>
    );
  }

  if (variant === "bars") {
    return (
      <div
        className={`animate-fade-up space-y-4 ${className}`}
        role="status"
        aria-label="Loading match breakdown"
      >
        {[1, 2, 3, 4].map((row) => (
          <div key={row} className="space-y-2">
            <div className="flex justify-between gap-3">
              <SkeletonBlock className="h-4 w-24 rounded" />
              <SkeletonBlock className="h-4 w-10 rounded" />
            </div>
            <SkeletonBlock className="h-2 w-full rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "chips") {
    return (
      <div
        className={`animate-fade-up space-y-3 ${className}`}
        role="status"
        aria-label="Loading skills"
      >
        {[1, 2, 3].map((row) => (
          <div key={row} className="space-y-2 rounded-xl bg-canvas/50 p-3">
            <SkeletonBlock className="h-6 w-28 rounded-full" />
            <SkeletonBlock className="h-3 w-full rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "list") {
    return (
      <div
        className={`animate-fade-up space-y-3 ${className}`}
        role="status"
        aria-label="Loading suggestions"
      >
        {[1, 2, 3].map((row) => (
          <div key={row} className="space-y-2 rounded-xl bg-canvas/50 p-3">
            <SkeletonBlock className="h-4 w-56 max-w-full rounded" />
            <SkeletonBlock className="h-3 w-full rounded" />
            <SkeletonBlock className="h-3 w-40 max-w-full rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "rewrite") {
    return (
      <div
        className={`animate-fade-up space-y-4 ${className}`}
        role="status"
        aria-label="Loading optimized resume"
      >
        <div className="flex flex-wrap gap-2">
          <SkeletonBlock className="h-8 w-36 rounded-lg" />
          <SkeletonBlock className="h-8 w-36 rounded-lg" />
          <SkeletonBlock className="h-8 w-28 rounded-lg" />
        </div>
        {[1, 2, 3].map((row) => (
          <div key={row} className="space-y-3 rounded-xl border border-line p-4">
            <SkeletonBlock className="h-4 w-40 rounded" />
            <SkeletonBlock className="h-3 w-full rounded" />
            <SkeletonBlock className="h-3 w-5/6 max-w-full rounded" />
            <SkeletonBlock className="h-3 w-2/3 max-w-full rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className={`animate-fade-up space-y-3 ${className}`}
      role="status"
      aria-label="Loading"
    >
      <SkeletonBlock className="h-4 w-2/3 rounded" />
      <SkeletonBlock className="h-4 w-full rounded" />
      <SkeletonBlock className="h-4 w-5/6 rounded" />
    </div>
  );
}

export { SkeletonBlock };
export default Skeleton;
