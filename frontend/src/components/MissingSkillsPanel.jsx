import { memo } from "react";
import EmptyState from "./ui/EmptyState";
import Skeleton from "./ui/Skeleton";

const CHIP_STYLES = [
  "bg-accent-soft text-accent-strong",
  "bg-sky-50 text-sky-800",
  "bg-teal-50 text-teal-800",
  "bg-cyan-50 text-cyan-800",
];

function normalizeSkill(item) {
  if (typeof item === "string") {
    return { skill: item, reason: "" };
  }

  return {
    skill: item?.skill || "",
    reason: item?.reason || "",
  };
}

function MissingSkillsPanel({ items, loading = false }) {
  if (loading) {
    return <Skeleton variant="chips" />;
  }

  if (!items?.length) {
    return (
      <EmptyState
        icon="skills"
        description="No analysis yet."
      />
    );
  }

  return (
    <ul className="animate-fade-in space-y-3">
      {items.map((item, index) => {
        const skill = normalizeSkill(item);
        if (!skill.skill) return null;

        return (
          <li
            key={`${skill.skill}-${index}`}
            className="animate-fade-up rounded-xl bg-canvas/60 px-3 py-3"
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <span
              className={`inline-flex max-w-full break-words rounded-full px-3 py-1 text-xs font-medium sm:text-sm ${CHIP_STYLES[index % CHIP_STYLES.length]}`}
            >
              {skill.skill}
            </span>
            {skill.reason && (
              <p className="mt-2 text-sm leading-relaxed text-muted">
                {skill.reason}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export default memo(MissingSkillsPanel);
