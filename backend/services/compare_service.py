"""Deterministic resume compare — no Claude calls."""

from __future__ import annotations

import difflib
from typing import Any

from services.parse_service import (
    normalize_structured_resume,
    structure_resume_text,
)


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
    optimized = normalize_structured_resume(rewrite)

    section_specs = [
        ("summary", "Summary", "text"),
        ("experience", "Experience", "list"),
        ("projects", "Projects", "list"),
        ("skills", "Skills", "list"),
        ("education", "Education", "list"),
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
