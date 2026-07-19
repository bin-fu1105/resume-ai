import EmptyState from "./ui/EmptyState";

/** @deprecated Prefer EmptyState directly. Kept for compatibility. */
function PlaceholderNote({ children, icon = "default", title }) {
  return (
    <EmptyState
      icon={icon}
      title={title}
      description={typeof children === "string" ? children : undefined}
    />
  );
}

export default PlaceholderNote;
