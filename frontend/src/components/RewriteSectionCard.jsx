import { useState } from "react";

async function copyText(text) {
  await navigator.clipboard.writeText(text);
}

function RewriteSectionCard({
  title,
  copyText: sectionCopyText,
  defaultOpen = true,
  children,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [copyLabel, setCopyLabel] = useState("Copy");

  const handleCopy = async () => {
    try {
      await copyText(sectionCopyText);
      setCopyLabel("Copied");
    } catch {
      setCopyLabel("Failed");
    }
    setTimeout(() => setCopyLabel("Copy"), 1600);
  };

  return (
    <section className="animate-fade-up overflow-hidden rounded-xl border border-line bg-canvas/40">
      <div className="flex items-center justify-between gap-3 border-b border-line/80 px-4 py-3">
        <button
          type="button"
          onClick={() => setOpen((current) => !current)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
          aria-expanded={open}
        >
          <svg
            className={`h-4 w-4 shrink-0 text-muted transition-transform ${
              open ? "rotate-90" : ""
            }`}
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
          <h4 className="font-display text-sm font-semibold text-ink">{title}</h4>
        </button>

        <button
          type="button"
          onClick={handleCopy}
          className="shrink-0 rounded-lg border border-line bg-white px-2.5 py-1 text-xs font-semibold text-ink transition hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label={`Copy ${title}`}
        >
          {copyLabel}
        </button>
      </div>

      {open && <div className="animate-fade-up px-4 py-4">{children}</div>}
    </section>
  );
}

export default RewriteSectionCard;
