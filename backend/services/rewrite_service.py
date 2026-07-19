"""Claude-powered resume optimization — separate from ATS analysis."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import anthropic

from services.claude_client import ClaudeJsonClient
from services.errors import ClaudeServiceError
from services.parse_service import (
    SECTION_KEYS,
    normalize_structured_resume,
    structure_resume_text,
)
from services.prompt_loader import load_prompt

VALID_BADGES = {"High impact", "Improved", "Minor polish", "Unchanged"}
LIST_SECTIONS = {"experience", "projects", "skills", "education"}


class RewriteService:
    """Dedicated service for Claude-powered section-aware resume rewrites."""

    REQUIRED_KEYS = set(SECTION_KEYS)

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        prompts_dir: str | Path | None = None,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ClaudeServiceError("ANTHROPIC_API_KEY is not configured.")

        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
        self.prompts_dir = Path(
            prompts_dir or Path(__file__).resolve().parent.parent / "prompts"
        )
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.json_client = ClaudeJsonClient(self.client, self.model)

    def build_prompt(
        self,
        resume_text: str,
        job_description: str,
        prompt_name: str = "resume_rewrite.txt",
        focus_section: str | None = None,
    ) -> str:
        template = load_prompt(self.prompts_dir, prompt_name)
        section = (focus_section or "").strip().lower()
        if section in self.REQUIRED_KEYS:
            focus_instruction = (
                f"Focus primarily on rewriting the '{section}' section. "
                "Still return the complete JSON with all keys. "
                f"Make the largest, most careful improvements in '{section}'. "
                "Keep other sections polished but secondary."
            )
        else:
            focus_instruction = (
                "Rewrite every section independently and thoroughly. "
                "Do not let one section's wording constrain another section."
            )

        return (
            template.replace(
                "<<<JOB_DESCRIPTION>>>",
                job_description.strip() or "(No job description provided)",
            )
            .replace("<<<RESUME_TEXT>>>", resume_text.strip())
            .replace("<<<FOCUS_INSTRUCTION>>>", focus_instruction)
        )

    def _normalize_insight(self, item: Any, section_id: str) -> dict[str, Any]:
        data = item if isinstance(item, dict) else {}
        badge = str(data.get("improvement_badge") or "Improved").strip()
        if badge not in VALID_BADGES:
            badge = "Improved"

        try:
            gain = int(data.get("estimated_ats_gain", 0))
        except (TypeError, ValueError):
            gain = 0
        gain = max(0, min(20, gain))

        return {
            "id": section_id,
            "improvement_badge": badge,
            "estimated_ats_gain": gain,
            "rationale": str(data.get("rationale") or "").strip(),
        }

    def _normalize_rewrite(self, rewrite: dict[str, Any]) -> dict[str, Any]:
        if "summary" not in rewrite and isinstance(
            rewrite.get("professional_summary"), str
        ):
            rewrite["summary"] = rewrite["professional_summary"]

        normalized = normalize_structured_resume(rewrite)
        if not normalized["summary"] and not any(
            normalized[key] for key in LIST_SECTIONS
        ):
            raise ClaudeServiceError("Rewrite result is empty.")

        insights_raw = rewrite.get("section_insights")
        insights_by_id: dict[str, dict[str, Any]] = {}
        if isinstance(insights_raw, list):
            for item in insights_raw:
                if isinstance(item, dict) and item.get("id") in self.REQUIRED_KEYS:
                    section_id = str(item["id"])
                    insights_by_id[section_id] = self._normalize_insight(
                        item, section_id
                    )

        insights = [
            insights_by_id.get(
                section_id,
                self._normalize_insight({}, section_id),
            )
            for section_id in SECTION_KEYS
        ]

        return {
            **normalized,
            "section_insights": insights,
        }

    def _section_content_for_prompt(self, section: str, original: dict[str, Any]) -> str:
        value = original.get(section)
        if section == "summary":
            return str(value or "").strip() or "(empty)"
        if isinstance(value, list):
            return "\n".join(f"- {item}" for item in value) or "(empty)"
        return str(value or "").strip() or "(empty)"

    def _normalize_section_content(self, section: str, content: Any) -> str | list[str]:
        if section == "summary":
            if isinstance(content, list):
                return " ".join(str(item).strip() for item in content if str(item).strip())
            return str(content or "").strip()

        if isinstance(content, str):
            text = content.strip()
            return [text] if text else []
        if not isinstance(content, list):
            return []
        return [str(item).strip() for item in content if str(item).strip()]

    def rewrite_section(
        self,
        *,
        section: str,
        resume_text: str,
        job_description: str,
        original: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        section = section.strip().lower()
        if section not in self.REQUIRED_KEYS:
            raise ClaudeServiceError(
                "section must be one of: summary, experience, projects, skills, education."
            )
        if not job_description.strip():
            raise ClaudeServiceError("Job description is required for rewrite.")

        parsed = original or structure_resume_text(resume_text)
        template = load_prompt(self.prompts_dir, "section_rewrite.txt")
        prompt = (
            template.replace("<<<SECTION_NAME>>>", section)
            .replace(
                "<<<SECTION_CONTENT>>>",
                self._section_content_for_prompt(section, parsed),
            )
            .replace("<<<RESUME_TEXT>>>", resume_text.strip())
            .replace(
                "<<<JOB_DESCRIPTION>>>",
                job_description.strip() or "(No job description provided)",
            )
            .replace(
                "<<<FOCUS_INSTRUCTION>>>",
                (
                    "Improve ATS keyword matching, use stronger verbs, preserve facts, "
                    "and use STAR style where appropriate. Never invent experience."
                ),
            )
        )

        result = self.json_client.request_json(
            prompt,
            max_tokens=1800,
            operation=f"rewrite_section_{section}",
        )
        content = self._normalize_section_content(section, result.get("content"))
        insight = self._normalize_insight(result, section)
        return {"content": content, "insight": insight}

    def rewrite_sections_independently(
        self,
        resume_text: str,
        job_description: str,
        focus_section: str | None = None,
    ) -> dict[str, Any]:
        """Rewrite each requested section with its own Claude call."""
        if not resume_text.strip():
            raise ClaudeServiceError("Resume text is empty.")
        if not job_description.strip():
            raise ClaudeServiceError("Job description is required for rewrite.")

        original = structure_resume_text(resume_text)
        optimized = normalize_structured_resume(original)
        focus = (focus_section or "").strip().lower() or None
        if focus and focus not in self.REQUIRED_KEYS:
            raise ClaudeServiceError(
                "focus_section must be one of: summary, experience, projects, skills, education."
            )

        targets = [focus] if focus else list(SECTION_KEYS)
        insights_by_id: dict[str, dict[str, Any]] = {
            key: self._normalize_insight(
                {
                    "improvement_badge": "Unchanged",
                    "estimated_ats_gain": 0,
                    "rationale": "Section not rewritten in this pass.",
                },
                key,
            )
            for key in SECTION_KEYS
        }

        def _run(section_id: str) -> tuple[str, dict[str, Any]]:
            return section_id, self.rewrite_section(
                section=section_id,
                resume_text=resume_text,
                job_description=job_description,
                original=original,
            )

        # Parallelize independent section rewrites for latency.
        max_workers = min(5, len(targets))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_run, section_id) for section_id in targets]
            for future in as_completed(futures):
                section_id, payload = future.result()
                optimized[section_id] = payload["content"]
                insights_by_id[section_id] = payload["insight"]

        return {
            **optimized,
            "original": original,
            "section_insights": [insights_by_id[key] for key in SECTION_KEYS],
        }

    def rewrite_resume(
        self,
        resume_text: str,
        job_description: str,
        prompt_name: str = "resume_rewrite.txt",
        focus_section: str | None = None,
        independent: bool = True,
    ) -> dict[str, Any]:
        """
        Optimize resume content for the target JD.

        By default rewrites sections independently (one Claude call per section).
        Falls back to a single full-resume JSON rewrite if needed.
        """
        if independent:
            try:
                return self.rewrite_sections_independently(
                    resume_text=resume_text,
                    job_description=job_description,
                    focus_section=focus_section,
                )
            except ClaudeServiceError:
                raise
            except Exception:
                # Fall through to single-prompt rewrite for resilience.
                pass

        if not resume_text.strip():
            raise ClaudeServiceError("Resume text is empty.")
        if not job_description.strip():
            raise ClaudeServiceError("Job description is required for rewrite.")

        section = (focus_section or "").strip().lower() or None
        if section and section not in self.REQUIRED_KEYS:
            raise ClaudeServiceError(
                "focus_section must be one of: summary, experience, projects, skills, education."
            )

        prompt = self.build_prompt(
            resume_text,
            job_description,
            prompt_name=prompt_name,
            focus_section=section,
        )
        rewrite = self.json_client.request_json(
            prompt,
            max_tokens=4000,
            operation="rewrite_resume",
        )
        normalized = self._normalize_rewrite(rewrite)
        normalized["original"] = structure_resume_text(resume_text)
        return normalized
