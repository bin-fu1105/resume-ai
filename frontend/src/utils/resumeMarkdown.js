function getSummary(rewrite) {
  return rewrite?.summary || rewrite?.professional_summary || "";
}

export function rewrittenResumeToMarkdown(rewrite) {
  if (!rewrite) {
    return "";
  }

  const summary = getSummary(rewrite);
  const lines = ["# AI Optimized Resume", ""];

  if (summary) {
    lines.push("## Professional Summary", "", summary, "");
  }

  if (rewrite.experience?.length) {
    lines.push("## Experience", "");
    rewrite.experience.forEach((item) => {
      lines.push(`- ${item}`);
    });
    lines.push("");
  }

  if (rewrite.projects?.length) {
    lines.push("## Projects", "");
    rewrite.projects.forEach((item) => {
      lines.push(`- ${item}`);
    });
    lines.push("");
  }

  if (rewrite.skills?.length) {
    lines.push("## Skills", "", rewrite.skills.join(", "), "");
  }

  return `${lines.join("\n").trim()}\n`;
}

export function rewrittenResumeToPlainText(rewrite) {
  if (!rewrite) {
    return "";
  }

  const summary = getSummary(rewrite);
  const sections = [];

  if (summary) {
    sections.push(`Professional Summary\n${summary}`);
  }

  if (rewrite.experience?.length) {
    sections.push(
      `Experience\n${rewrite.experience.map((item) => `• ${item}`).join("\n")}`
    );
  }

  if (rewrite.projects?.length) {
    sections.push(
      `Projects\n${rewrite.projects.map((item) => `• ${item}`).join("\n")}`
    );
  }

  if (rewrite.skills?.length) {
    sections.push(`Skills\n${rewrite.skills.join(", ")}`);
  }

  return sections.join("\n\n");
}

export function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
