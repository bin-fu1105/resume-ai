export function getSectionHeat(score) {
  const value = Number(score) || 0;

  if (value >= 80) {
    return {
      label: "Strong",
      tone: "green",
      cardClass: "border-emerald-200 bg-emerald-50/70 hover:border-emerald-300",
      badgeClass: "bg-emerald-100 text-emerald-800",
      barClass: "bg-emerald-500",
      textClass: "text-emerald-800",
      tooltip: "This section is ATS-strong for the target role.",
    };
  }

  if (value >= 55) {
    return {
      label: "Fair",
      tone: "yellow",
      cardClass: "border-amber-200 bg-amber-50/70 hover:border-amber-300",
      badgeClass: "bg-amber-100 text-amber-900",
      barClass: "bg-amber-500",
      textClass: "text-amber-800",
      tooltip: "This section is usable but needs targeted improvements.",
    };
  }

  return {
    label: "Weak",
    tone: "red",
    cardClass: "border-rose-200 bg-rose-50/70 hover:border-rose-300",
    badgeClass: "bg-rose-100 text-rose-800",
    barClass: "bg-rose-500",
    textClass: "text-rose-800",
    tooltip: "This section is likely hurting ATS and interview probability.",
  };
}

export const SECTION_META = [
  {
    id: "summary",
    title: "Summary",
    description: "Professional summary clarity and role alignment.",
  },
  {
    id: "experience",
    title: "Experience",
    description: "Impact, metrics, and relevance of work history.",
  },
  {
    id: "projects",
    title: "Projects",
    description: "Applied proof of skills and product delivery.",
  },
  {
    id: "skills",
    title: "Skills",
    description: "Keyword coverage and stack match for the job.",
  },
  {
    id: "education",
    title: "Education",
    description: "Degree, coursework, and credential relevance.",
  },
];
