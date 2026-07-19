export function getScoreStatus(score) {
  if (score >= 85) {
    return {
      label: "Excellent",
      explanation:
        "Your resume is highly ATS-ready with strong structure and keyword coverage.",
      barClass: "bg-accent",
      textClass: "text-accent-strong",
      badgeClass: "bg-accent-soft text-accent-strong",
    };
  }

  if (score >= 70) {
    return {
      label: "Good",
      explanation:
        "Solid ATS foundation. A few targeted edits can push this into the top tier.",
      barClass: "bg-teal-500",
      textClass: "text-teal-700",
      badgeClass: "bg-teal-50 text-teal-700",
    };
  }

  if (score >= 50) {
    return {
      label: "Fair",
      explanation:
        "Your resume may pass basic filters, but clarity and keyword alignment need work.",
      barClass: "bg-amber-500",
      textClass: "text-amber-700",
      badgeClass: "bg-amber-50 text-amber-800",
    };
  }

  return {
    label: "Poor",
    explanation:
      "Likely to be filtered out. Focus on formatting, skills, and measurable impact.",
    barClass: "bg-rose-500",
    textClass: "text-rose-700",
    badgeClass: "bg-rose-50 text-rose-700",
  };
}
