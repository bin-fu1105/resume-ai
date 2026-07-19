function ErrorState({
  title = "Something went wrong",
  message = "Please try again.",
  onRetry,
  retryLabel = "Try again",
  className = "",
}) {
  return (
    <div
      className={`animate-fade-up rounded-xl border border-red-200 bg-red-50/90 px-4 py-5 ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-red-600 shadow-sm">
          <svg
            className="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
              clipRule="evenodd"
            />
          </svg>
        </div>

        <div className="min-w-0 flex-1">
          <p className="font-display text-sm font-semibold text-red-900">
            {title}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-red-800/90">
            {message}
          </p>

          {typeof onRetry === "function" && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-4 inline-flex items-center justify-center rounded-xl border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-800 shadow-sm transition hover:border-red-300 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
              aria-label={retryLabel}
            >
              {retryLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ErrorState;
