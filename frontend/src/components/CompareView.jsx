import { useEffect, useMemo, useState } from "react";
import EmptyState from "./ui/EmptyState";
import ErrorState from "./ui/ErrorState";
import Spinner from "./ui/Spinner";
import { API_BASE } from "../utils/uploadFile";
import { toFriendlyError } from "../utils/friendlyError";

const TOKEN_STYLES = {
  equal: "bg-transparent text-ink",
  added: "bg-emerald-100 text-emerald-900",
  removed: "bg-red-100 text-red-900 line-through",
  changed: "bg-amber-100 text-amber-950",
};

function matchesSearch(text, query) {
  if (!query) return true;
  return String(text || "").toLowerCase().includes(query.toLowerCase());
}

function DiffToken({ type, text }) {
  if (!text) return null;
  return (
    <span
      className={`mr-1 inline rounded px-1 py-0.5 text-sm leading-relaxed ${TOKEN_STYLES[type] || TOKEN_STYLES.equal}`}
    >
      {text}
    </span>
  );
}

function SideBySideColumn({ title, tokens, query }) {
  const visible = tokens.filter((token) => matchesSearch(token.text, query));

  return (
    <div className="min-w-0 rounded-xl border border-line bg-canvas/40 p-3 sm:p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
        {title}
      </p>
      {visible.length === 0 ? (
        <p className="text-sm text-muted">No matching content.</p>
      ) : (
        <div className="space-y-2">
          {visible.map((token, index) => (
            <div key={`${token.type}-${index}`} className="break-words">
              <DiffToken type={token.type} text={token.text} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function UnifiedRows({ rows, query, hideUnchanged }) {
  const visible = rows.filter((row) => {
    if (hideUnchanged && row.type === "equal") return false;
    return (
      matchesSearch(row.original, query) || matchesSearch(row.optimized, query)
    );
  });

  if (visible.length === 0) {
    return <p className="text-sm text-muted">No matching changes in this section.</p>;
  }

  return (
    <div className="space-y-2">
      {visible.map((row, index) => (
        <div
          key={`${row.type}-${index}`}
          className={`rounded-lg border px-3 py-2 text-sm leading-relaxed ${
            row.type === "added"
              ? "border-emerald-200 bg-emerald-50"
              : row.type === "removed"
                ? "border-red-200 bg-red-50"
                : row.type === "changed"
                  ? "border-amber-200 bg-amber-50"
                  : "border-line bg-white"
          }`}
        >
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted">
            {row.type}
          </p>
          {row.type === "added" && (
            <p>
              <DiffToken type="added" text={row.optimized} />
            </p>
          )}
          {row.type === "removed" && (
            <p>
              <DiffToken type="removed" text={row.original} />
            </p>
          )}
          {row.type === "changed" && (
            <div className="space-y-1">
              <p>
                <span className="mr-2 text-xs font-semibold text-muted">From</span>
                <DiffToken type="changed" text={row.original} />
              </p>
              <p>
                <span className="mr-2 text-xs font-semibold text-muted">To</span>
                <DiffToken type="added" text={row.optimized} />
              </p>
            </div>
          )}
          {row.type === "equal" && (
            <p>
              <DiffToken type="equal" text={row.original || row.optimized} />
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function CompareSection({ section, mode, hideUnchanged, query, open, onToggle }) {
  const filteredOriginal = useMemo(() => {
    const tokens = section.side_by_side?.original || [];
    return tokens.filter((token) => {
      if (hideUnchanged && token.type === "equal") return false;
      return matchesSearch(token.text, query);
    });
  }, [section, hideUnchanged, query]);

  const filteredOptimized = useMemo(() => {
    const tokens = section.side_by_side?.optimized || [];
    return tokens.filter((token) => {
      if (hideUnchanged && token.type === "equal") return false;
      return matchesSearch(token.text, query);
    });
  }, [section, hideUnchanged, query]);

  const sectionMatchesSearch =
    !query ||
    filteredOriginal.length > 0 ||
    filteredOptimized.length > 0 ||
    (section.unified || []).some(
      (row) =>
        matchesSearch(row.original, query) || matchesSearch(row.optimized, query)
    );

  if (!sectionMatchesSearch) {
    return null;
  }

  if (hideUnchanged && !section.has_changes) {
    return null;
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-canvas/60"
        aria-expanded={open}
      >
        <div className="min-w-0">
          <h3 className="font-display text-sm font-semibold text-ink">
            {section.title}
          </h3>
          <p className="mt-0.5 text-xs text-muted">
            {section.has_changes ? "Changes detected" : "No changes"}
          </p>
        </div>
        <svg
          className={`h-4 w-4 shrink-0 text-muted transition ${open ? "rotate-90" : ""}`}
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <div className="border-t border-line px-4 py-4">
          {mode === "side-by-side" ? (
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              <SideBySideColumn
                title="Original Resume"
                tokens={filteredOriginal}
                query=""
              />
              <SideBySideColumn
                title="Optimized Resume"
                tokens={filteredOptimized}
                query=""
              />
            </div>
          ) : (
            <UnifiedRows
              rows={section.unified || []}
              query={query}
              hideUnchanged={hideUnchanged}
            />
          )}
        </div>
      )}
    </section>
  );
}

function CompareView({ filename, rewrite, enabled }) {
  const [compareData, setCompareData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("side-by-side");
  const [hideUnchanged, setHideUnchanged] = useState(false);
  const [query, setQuery] = useState("");
  const [openSections, setOpenSections] = useState({});

  const loadCompare = async () => {
    if (!filename || !rewrite) {
      setCompareData(null);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename,
          rewrite,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          toFriendlyError(
            data.detail || data.error || data,
            "Couldn't build the compare view."
          )
        );
      }

      setCompareData(data);
      const nextOpen = {};
      (data.sections || []).forEach((section) => {
        nextOpen[section.id] = true;
      });
      setOpenSections(nextOpen);
    } catch (err) {
      setCompareData(null);
      setError(
        toFriendlyError(err, "Couldn't build the compare view. Please try again.")
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!enabled) {
      setCompareData(null);
      setError("");
      return;
    }
    loadCompare();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filename, rewrite, enabled]);

  const toggleSection = (id) => {
    setOpenSections((current) => ({
      ...current,
      [id]: !current[id],
    }));
  };

  const expandAll = () => {
    const next = {};
    (compareData?.sections || []).forEach((section) => {
      next[section.id] = true;
    });
    setOpenSections(next);
  };

  const collapseAll = () => {
    const next = {};
    (compareData?.sections || []).forEach((section) => {
      next[section.id] = false;
    });
    setOpenSections(next);
  };

  if (!enabled) {
    return (
      <section id="compare" className="panel-card scroll-mt-24">
        <EmptyState
          icon="rewrite"
          description="Run Rewrite Resume first to compare original vs optimized versions."
        />
      </section>
    );
  }

  return (
    <section id="compare" className="space-y-4 scroll-mt-24" aria-label="Rewrite compare">
      <div className="panel-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
              Compare
            </p>
            <h2 className="mt-1 font-display text-xl font-semibold tracking-tight text-ink">
              Original vs Optimized
            </h2>
            <p className="mt-1 text-sm text-muted">
              Highlighted diffs from your parsed resume and the latest rewrite.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-xl border border-line bg-canvas/50 p-1">
              <button
                type="button"
                onClick={() => setMode("side-by-side")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  mode === "side-by-side"
                    ? "bg-white text-accent shadow-sm"
                    : "text-muted hover:text-ink"
                }`}
              >
                Side-by-side
              </button>
              <button
                type="button"
                onClick={() => setMode("unified")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  mode === "unified"
                    ? "bg-white text-accent shadow-sm"
                    : "text-muted hover:text-ink"
                }`}
              >
                Unified diff
              </button>
            </div>

            <button
              type="button"
              onClick={() => setHideUnchanged((value) => !value)}
              className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-accent hover:text-accent"
            >
              {hideUnchanged ? "Show all" : "Hide unchanged"}
            </button>
            <button
              type="button"
              onClick={expandAll}
              className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-accent hover:text-accent"
            >
              Expand
            </button>
            <button
              type="button"
              onClick={collapseAll}
              className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-accent hover:text-accent"
            >
              Collapse
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label htmlFor="compare-search" className="sr-only">
            Search inside compare
          </label>
          <input
            id="compare-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search inside compare..."
            className="w-full max-w-md rounded-xl border border-line bg-canvas/50 px-3 py-2 text-sm text-ink outline-none transition placeholder:text-muted/70 focus:border-accent focus:bg-white focus:ring-2 focus:ring-accent/20"
          />
          <div className="flex flex-wrap gap-2 text-[11px] text-muted">
            <span className="rounded bg-emerald-100 px-2 py-1 text-emerald-900">
              Added
            </span>
            <span className="rounded bg-red-100 px-2 py-1 text-red-900">
              Removed
            </span>
            <span className="rounded bg-amber-100 px-2 py-1 text-amber-950">
              Changed
            </span>
          </div>
        </div>
      </div>

      {loading && (
        <div className="panel-card flex items-center gap-3 text-sm text-muted">
          <Spinner label="Building compare view" />
          Building compare view...
        </div>
      )}

      {error && (
        <ErrorState
          title="Compare failed"
          message={error}
          onRetry={loadCompare}
          retryLabel="Retry compare"
        />
      )}

      {!loading && !error && compareData && (
        <div className="space-y-3">
          {(compareData.sections || []).map((section) => (
            <CompareSection
              key={section.id}
              section={section}
              mode={mode}
              hideUnchanged={hideUnchanged}
              query={query}
              open={Boolean(openSections[section.id])}
              onToggle={() => toggleSection(section.id)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export default CompareView;
