function JobDescriptionCard({ value, onChange, error }) {
  const hasError = Boolean(error);

  return (
    <section className="panel-card min-w-0" aria-labelledby="job-description-heading">
      <div className="mb-4">
        <h2
          id="job-description-heading"
          className="font-display text-base font-semibold tracking-tight text-ink"
        >
          Job Description
        </h2>
        <p className="mt-1 text-sm text-muted">
          Paste the target role description for matching insights.
        </p>
      </div>

      <label htmlFor="job-description-input" className="sr-only">
        Job description
      </label>
      <textarea
        id="job-description-input"
        value={value}
        onChange={onChange}
        rows={8}
        placeholder="Paste the job description here..."
        aria-invalid={hasError}
        aria-describedby={hasError ? "job-description-error" : undefined}
        className={[
          "min-h-40 w-full resize-y rounded-xl bg-canvas/50 px-4 py-3 text-sm text-ink outline-none transition placeholder:text-muted/70 focus:bg-white focus:ring-2",
          hasError
            ? "border-2 border-red-500 focus:border-red-500 focus:ring-red-200"
            : "border border-line focus:border-accent focus:ring-accent/20",
        ].join(" ")}
      />

      {hasError && (
        <p
          id="job-description-error"
          className="mt-2 text-sm font-medium text-red-600"
          role="alert"
        >
          {error}
        </p>
      )}
    </section>
  );
}

export default JobDescriptionCard;
