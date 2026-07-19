"""Compare legacy vs upgraded prompts on the same resume."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from services.claude_service import ClaudeService
from services.rewrite_service import RewriteService

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

RESUME = """
Alex Chen
Full Stack Engineer

Summary
Software engineer with experience building SaaS products.

Skills
Python, React, Docker, PostgreSQL, JavaScript

Experience
Software Engineer, BrightApps (2021-2024)
- Built SaaS APIs and dashboards
- Improved deploy reliability with Docker
- Worked on database queries in PostgreSQL

Projects
Inventory Platform
- React frontend and Python API for inventory tracking
- Helped team ship containerized deployment
""".strip()

JD = (
    "Hiring a Full Stack Engineer with Python, React, Docker, PostgreSQL, "
    "REST APIs, and measurable product delivery experience."
)


def summarize_analysis(label: str, analysis: dict) -> None:
    print(f"\n=== {label} ANALYSIS ===")
    print("ats_score:", analysis.get("ats_score"))
    print("ats_explanation:", (analysis.get("ats_explanation") or "")[:240])
    print("missing_skills sample:", analysis.get("missing_skills", [])[:2])
    print("strengths sample:", analysis.get("strengths", [])[:2])
    suggestions = analysis.get("suggestions", [])
    print("suggestions count:", len(suggestions))
    if suggestions:
        first = suggestions[0]
        print("first suggestion:", json.dumps(first, ensure_ascii=False)[:400])


def summarize_rewrite(label: str, rewrite: dict) -> None:
    print(f"\n=== {label} REWRITE ===")
    print("summary:", (rewrite.get("summary") or "")[:220])
    experience = rewrite.get("experience") or []
    print("experience count:", len(experience))
    if experience:
        print("first experience bullet:", experience[0][:240])
    print("skills:", rewrite.get("skills"))


def main() -> None:
    analyzer = ClaudeService()
    rewriter = RewriteService()

    # Legacy analysis: raw JSON (old schema), no new validation.
    legacy_prompt = analyzer.build_resume_analysis_prompt(
        RESUME,
        JD,
        prompt_name="legacy/resume_analysis.txt",
    )
    legacy_analysis = analyzer.json_client.request_json(
        legacy_prompt,
        max_tokens=2500,
        operation="compare_legacy_analyze",
    )

    new_analysis = analyzer.analyze_resume(RESUME, JD)

    legacy_rewrite_prompt = rewriter.build_prompt(
        RESUME,
        JD,
        prompt_name="legacy/resume_rewrite.txt",
    )
    legacy_rewrite = rewriter.json_client.request_json(
        legacy_rewrite_prompt,
        max_tokens=3000,
        operation="compare_legacy_rewrite",
    )
    if "summary" not in legacy_rewrite and legacy_rewrite.get("professional_summary"):
        legacy_rewrite["summary"] = legacy_rewrite["professional_summary"]

    new_rewrite = rewriter.rewrite_resume(RESUME, JD)

    summarize_analysis("LEGACY", legacy_analysis)
    summarize_analysis("NEW", new_analysis)
    summarize_rewrite("LEGACY", legacy_rewrite)
    summarize_rewrite("NEW", new_rewrite)

    print("\n=== QUALITY DELTAS ===")
    legacy_suggestion = (legacy_analysis.get("suggestions") or [None])[0]
    new_suggestion = (new_analysis.get("suggestions") or [None])[0]
    print(
        "Legacy suggestion is plain string:",
        isinstance(legacy_suggestion, str),
    )
    print(
        "New suggestion has reason/example/impact:",
        isinstance(new_suggestion, dict)
        and {"reason", "example", "impact"} <= set(new_suggestion.keys()),
    )
    print(
        "New analysis includes ats_explanation:",
        bool(new_analysis.get("ats_explanation")),
    )
    print(
        "New missing skill includes reason:",
        isinstance((new_analysis.get("missing_skills") or [{}])[0], dict)
        and bool((new_analysis.get("missing_skills") or [{}])[0].get("reason")),
    )

    out = Path("_compare_prompts_output.json")
    out.write_text(
        json.dumps(
            {
                "legacy_analysis": legacy_analysis,
                "new_analysis": new_analysis,
                "legacy_rewrite": legacy_rewrite,
                "new_rewrite": new_rewrite,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote full comparison to {out.resolve()}")


if __name__ == "__main__":
    main()
