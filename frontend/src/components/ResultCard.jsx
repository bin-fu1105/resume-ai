function ResultCard({
  title,
  description,
  children,
  className = "",
  animate = false,
  delay = 0,
}) {
  return (
    <section
      className={`panel-card min-w-0 overflow-hidden ${
        animate ? "animate-fade-up" : ""
      } ${className}`}
      style={animate ? { animationDelay: `${delay}ms` } : undefined}
    >
      <div className="mb-4 min-w-0">
        <h3 className="font-display text-base font-semibold tracking-tight text-ink">
          {title}
        </h3>
        {description && (
          <p className="mt-1 text-sm leading-relaxed text-muted">{description}</p>
        )}
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

export default ResultCard;
