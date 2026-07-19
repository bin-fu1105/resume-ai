import { memo } from "react";
import EmptyState from "./ui/EmptyState";
import Skeleton from "./ui/Skeleton";

function CheckIcon() {
  return (
    <span
      className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent"
      aria-hidden="true"
    >
      <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
        <path
          fillRule="evenodd"
          d="M16.704 5.29a1 1 0 010 1.42l-7.25 7.25a1 1 0 01-1.414 0l-3.25-3.25a1 1 0 011.414-1.42l2.543 2.544 6.543-6.544a1 1 0 011.414 0z"
          clipRule="evenodd"
        />
      </svg>
    </span>
  );
}

function normalizeSuggestion(item) {
  if (typeof item === "string") {
    return {
      reason: item,
      example: "",
      impact: "",
    };
  }

  return {
    reason: item?.reason || "",
    example: item?.example || "",
    impact: item?.impact || "",
  };
}

function SuggestionsPanel({ items, loading = false }) {
  if (loading) {
    return <Skeleton variant="list" />;
  }

  if (!items?.length) {
    return (
      <EmptyState
        icon="suggestions"
        description="Upload and analyze your resume to unlock actionable improvement ideas."
      />
    );
  }

  return (
    <ul className="animate-fade-in space-y-3">
      {items.map((item, index) => {
        const suggestion = normalizeSuggestion(item);

        return (
          <li
            key={`${suggestion.reason}-${index}`}
            className="animate-fade-up rounded-xl bg-canvas/70 px-3 py-3 sm:px-4"
            style={{ animationDelay: `${index * 70}ms` }}
          >
            <div className="flex items-start gap-3">
              <CheckIcon />
              <div className="min-w-0 space-y-2 text-sm leading-relaxed text-ink">
                <p>
                  <span className="font-semibold text-ink">Reason: </span>
                  {suggestion.reason}
                </p>
                {suggestion.example && (
                  <p>
                    <span className="font-semibold text-ink">Example: </span>
                    {suggestion.example}
                  </p>
                )}
                {suggestion.impact && (
                  <p>
                    <span className="font-semibold text-ink">Impact: </span>
                    {suggestion.impact}
                  </p>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export default memo(SuggestionsPanel);
