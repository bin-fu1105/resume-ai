import Spinner from "./ui/Spinner";

function RewriteButton({ loading, disabled, onClick, disabledReason }) {
  const isDisabled = disabled || loading;
  const showTooltip = isDisabled && !loading && Boolean(disabledReason);

  return (
    <div className="group relative w-full sm:w-auto">
      <button
        type="button"
        onClick={onClick}
        disabled={isDisabled}
        aria-describedby={showTooltip ? "rewrite-disabled-tooltip" : undefined}
        aria-busy={loading}
        aria-label={loading ? "Rewriting resume" : "Rewrite resume"}
        className="btn-secondary"
      >
        {loading ? (
          <Spinner className="h-4 w-4 text-accent" label="Rewriting" />
        ) : (
          <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
            <path d="M18.375 2.625a2.121 2.121 0 113 3L12 15l-4 1 1-4 9.375-9.375z" />
          </svg>
        )}
        {loading ? "Rewriting..." : "Rewrite Resume"}
      </button>

      {showTooltip && (
        <div
          id="rewrite-disabled-tooltip"
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-white opacity-0 shadow-md transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
        >
          {disabledReason}
          <span
            className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-ink"
            aria-hidden="true"
          />
        </div>
      )}
    </div>
  );
}

export default RewriteButton;
