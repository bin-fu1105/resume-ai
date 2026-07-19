"""Deterministic resume compare — no Claude calls."""

from __future__ import annotations

import difflib
import re
from typing import Any


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
}

HEADING_RE = re.compile(
    r"^(?P<title>[A-Za-z][A-Za-z0-9 &/+\-]{1,40})\s*:?\s*$"
)


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
    """Heuristically split raw resume text into compare sections."""
    lines = [line.strip() for line in (resume_text or "").splitlines()]
    lines = [line for line in lines if line]

    structured = {
        "summary": "",
        "experience": [],
        "projects": [],
        "skills": [],
    }

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
            # de-dupe preserving order
            seen = set()
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

    # If no explicit summary heading, use early preamble lines as summary.
    if not structured["summary"] and preamble:
        # Skip likely name/title first line when multiple preamble lines exist.
        summary_lines = preamble[1:] if len(preamble) > 2 else preamble
        structured["summary"] = " ".join(summary_lines).strip()

    # If experience never found, keep remaining non-header bullets as experience.
    if not structured["experience"] and not any(
        structured[key] for key in ("projects", "skills")
    ):
        leftover = [
            line.lstrip("•-* ").strip()
            for line in lines
            if line.lstrip("•-* ").strip() and not _match_section(line)
        ]
        structured["experience"] = leftover[2:] if len(leftover) > 3 else leftover

    return structured


def _normalize_rewrite(rewrite: dict[str, Any] | None) -> dict[str, Any]:
    payload = rewrite or {}
    summary = str(
        payload.get("summary") or payload.get("professional_summary") or ""
    ).strip()

    def as_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    return {
        "summary": summary,
        "experience": as_list(payload.get("experience")),
        "projects": as_list(payload.get("projects")),
        "skills": as_list(payload.get("skills")),
    }


def _word_diff(original: str, optimized: str) -> dict[str, list[dict[str, str]]]:
    original_words = original.split()
    optimized_words = optimized.split()
    matcher = difflib.SequenceMatcher(None, original_words, optimized_words)

    original_tokens: list[dict[str, str]] = []
    optimized_tokens: list[dict[str, str]] = []
    unified: list[dict[str, str]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        left = " ".join(original_words[i1:i2]).strip()
        right = " ".join(optimized_words[j1:j2]).strip()

        if tag == "equal":
            if left:
                original_tokens.append({"type": "equal", "text": left})
                optimized_tokens.append({"type": "equal", "text": right})
                unified.append(
                    {"type": "equal", "original": left, "optimized": right}
                )
        elif tag == "delete":
            if left:
                original_tokens.append({"type": "removed", "text": left})
                unified.append(
                    {"type": "removed", "original": left, "optimized": ""}
                )
        elif tag == "insert":
            if right:
                optimized_tokens.append({"type": "added", "text": right})
                unified.append(
                    {"type": "added", "original": "", "optimized": right}
                )
        elif tag == "replace":
            if left:
                original_tokens.append({"type": "changed", "text": left})
            if right:
                optimized_tokens.append({"type": "changed", "text": right})
            unified.append(
                {
                    "type": "changed",
                    "original": left,
                    "optimized": right,
                }
            )

    return {
        "original": original_tokens,
        "optimized": optimized_tokens,
        "unified": unified,
    }


def _list_diff(
    original_items: list[str],
    optimized_items: list[str],
) -> dict[str, list[dict[str, str]]]:
    matcher = difflib.SequenceMatcher(None, original_items, optimized_items)

    original_rows: list[dict[str, str]] = []
    optimized_rows: list[dict[str, str]] = []
    unified: list[dict[str, str]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for index in range(i2 - i1):
                left = original_items[i1 + index]
                right = optimized_items[j1 + index]
                original_rows.append({"type": "equal", "text": left})
                optimized_rows.append({"type": "equal", "text": right})
                unified.append(
                    {"type": "equal", "original": left, "optimized": right}
                )
        elif tag == "delete":
            for item in original_items[i1:i2]:
                original_rows.append({"type": "removed", "text": item})
                unified.append(
                    {"type": "removed", "original": item, "optimized": ""}
                )
        elif tag == "insert":
            for item in optimized_items[j1:j2]:
                optimized_rows.append({"type": "added", "text": item})
                unified.append(
                    {"type": "added", "original": "", "optimized": item}
                )
        elif tag == "replace":
            left_chunk = original_items[i1:i2]
            right_chunk = optimized_items[j1:j2]
            max_len = max(len(left_chunk), len(right_chunk))
            for index in range(max_len):
                left = left_chunk[index] if index < len(left_chunk) else ""
                right = right_chunk[index] if index < len(right_chunk) else ""
                if left and right:
                    original_rows.append({"type": "changed", "text": left})
                    optimized_rows.append({"type": "changed", "text": right})
                    unified.append(
                        {
                            "type": "changed",
                            "original": left,
                            "optimized": right,
                        }
                    )
                elif left:
                    original_rows.append({"type": "removed", "text": left})
                    unified.append(
                        {"type": "removed", "original": left, "optimized": ""}
                    )
                elif right:
                    optimized_rows.append({"type": "added", "text": right})
                    unified.append(
                        {"type": "added", "original": "", "optimized": right}
                    )

    return {
        "original": original_rows,
        "optimized": optimized_rows,
        "unified": unified,
    }


def compare_resumes(
    resume_text: str,
    rewrite: dict[str, Any] | None,
) -> dict[str, Any]:
    original = structure_resume_text(resume_text)
    optimized = _normalize_rewrite(rewrite)

    section_specs = [
        ("summary", "Summary", "text"),
        ("experience", "Experience", "list"),
        ("projects", "Projects", "list"),
        ("skills", "Skills", "list"),
    ]

    sections = []
    for key, title, kind in section_specs:
        if kind == "text":
            diff = _word_diff(original.get("summary", ""), optimized.get("summary", ""))
        else:
            diff = _list_diff(original.get(key, []), optimized.get(key, []))

        has_changes = any(item.get("type") != "equal" for item in diff["unified"])
        sections.append(
            {
                "id": key,
                "title": title,
                "has_changes": has_changes,
                "side_by_side": {
                    "original": diff["original"],
                    "optimized": diff["optimized"],
                },
                "unified": diff["unified"],
            }
        )

    return {
        "original": original,
        "optimized": optimized,
        "sections": sections,
    }
