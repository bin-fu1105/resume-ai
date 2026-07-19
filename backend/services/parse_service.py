"""Structured resume parsing into canonical optimization sections."""

from __future__ import annotations

import re
from typing import Any

SECTION_KEYS = ("summary", "experience", "projects", "skills", "education")

SECTION_ALIASES = {
    "summary": {
        "summary",
        "professional summary",
        "profile",
        "about",
        "objective",
        "about me",
    },
    "experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "work history",
        "employment history",
    },
    "projects": {
        "projects",
        "project",
        "personal projects",
        "selected projects",
        "project experience",
        "key projects",
    },
    "skills": {
        "skills",
        "technical skills",
        "core skills",
        "technologies",
        "tech stack",
        "tools",
        "skills & tools",
        "skills and tools",
    },
    "education": {
        "education",
        "academic background",
        "academics",
        "degrees",
        "education & certifications",
        "education and certifications",
    },
}

HEADING_RE = re.compile(
    r"^(?P<title>[A-Za-z][A-Za-z0-9 &/+\-]{1,40})\s*:?\s*$"
)


def empty_structured_resume() -> dict[str, Any]:
    return {
        "summary": "",
        "experience": [],
        "projects": [],
        "skills": [],
        "education": [],
    }


def _normalize_heading(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower().rstrip(":"))


def _match_section(line: str) -> str | None:
    heading = _normalize_heading(line)
    if not HEADING_RE.match(line.strip()) and ":" not in line and len(heading.split()) > 4:
        return None

    for section, aliases in SECTION_ALIASES.items():
        if heading in aliases:
            return section
    return None


def _split_skill_line(line: str) -> list[str]:
    parts = re.split(r"[,•·|;/]| {2,}", line)
    return [part.strip(" -•\t") for part in parts if part.strip(" -•\t")]


def structure_resume_text(resume_text: str) -> dict[str, Any]:
    """Heuristically split raw resume text into optimization sections."""
    lines = [line.strip() for line in (resume_text or "").splitlines()]
    lines = [line for line in lines if line]

    structured = empty_structured_resume()
    current = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current
        if not current or not buffer:
            buffer = []
            return

        if current == "summary":
            text = " ".join(buffer).strip()
            if text:
                structured["summary"] = text
        elif current == "skills":
            skills: list[str] = []
            for item in buffer:
                skills.extend(_split_skill_line(item))
            seen: set[str] = set()
            structured["skills"] = [
                skill
                for skill in skills
                if not (skill.lower() in seen or seen.add(skill.lower()))
            ]
        else:
            structured[current] = [
                item.lstrip("•-* ").strip()
                for item in buffer
                if item.lstrip("•-* ").strip()
            ]
        buffer = []

    preamble: list[str] = []

    for line in lines:
        section = _match_section(line)
        if section:
            flush()
            current = section
            continue

        if current is None:
            preamble.append(line)
        else:
            buffer.append(line)

    flush()

    if not structured["summary"] and preamble:
        summary_lines = preamble[1:] if len(preamble) > 2 else preamble
        structured["summary"] = " ".join(summary_lines).strip()

    if not structured["experience"] and not any(
        structured[key] for key in ("projects", "skills", "education")
    ):
        leftover = [
            line.lstrip("•-* ").strip()
            for line in lines
            if line.lstrip("•-* ").strip() and not _match_section(line)
        ]
        structured["experience"] = leftover[2:] if len(leftover) > 3 else leftover

    return structured


def normalize_structured_resume(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    summary = str(
        data.get("summary") or data.get("professional_summary") or ""
    ).strip()

    def as_list(value: Any) -> list[str]:
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    return {
        "summary": summary,
        "experience": as_list(data.get("experience")),
        "projects": as_list(data.get("projects")),
        "skills": as_list(data.get("skills")),
        "education": as_list(data.get("education")),
    }


def structured_to_plain_text(structured: dict[str, Any] | None) -> str:
    """Serialize structured resume content back into plain text for re-analysis."""
    data = normalize_structured_resume(structured)
    sections: list[str] = []

    if data["summary"]:
        sections.append(f"Professional Summary\n{data['summary']}")

    if data["experience"]:
        bullets = "\n".join(f"• {item}" for item in data["experience"])
        sections.append(f"Experience\n{bullets}")

    if data["projects"]:
        bullets = "\n".join(f"• {item}" for item in data["projects"])
        sections.append(f"Projects\n{bullets}")

    if data["skills"]:
        sections.append(f"Skills\n{', '.join(data['skills'])}")

    if data["education"]:
        bullets = "\n".join(f"• {item}" for item in data["education"])
        sections.append(f"Education\n{bullets}")

    return "\n\n".join(sections).strip()
