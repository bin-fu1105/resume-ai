import os
from pathlib import Path
from typing import Any

import anthropic

from services.claude_client import ClaudeJsonClient
from services.errors import ClaudeServiceError
from services.prompt_loader import load_prompt

# Re-export for existing imports: `from services.claude_service import ClaudeServiceError`
__all__ = ["ClaudeService", "ClaudeServiceError"]


class ClaudeService:
    REQUIRED_ANALYSIS_KEYS = {
        "ats_score",
        "ats_explanation",
        "resume_match",
        "missing_skills",
        "strengths",
        "suggestions",
        "optimized_summary",
        "sections",
    }
    REQUIRED_MATCH_KEYS = {"skills", "projects", "education", "experience"}
    REQUIRED_SECTION_KEYS = {"summary", "experience", "projects", "skills"}
    REQUIRED_SUGGESTION_KEYS = {"reason", "example", "impact"}
    VALID_SEVERITIES = {"low", "medium", "high"}

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        prompts_dir: str | Path | None = None,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ClaudeServiceError("ANTHROPIC_API_KEY is not configured.")

        self.model = model or os.getenv(
            "ANTHROPIC_MODEL",
            "claude-sonnet-5",
        )
        self.prompts_dir = Path(
            prompts_dir or Path(__file__).resolve().parent.parent / "prompts"
        )
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.json_client = ClaudeJsonClient(self.client, self.model)

    def build_resume_analysis_prompt(
        self,
        resume_text: str,
        job_description: str,
        prompt_name: str = "resume_analysis.txt",
    ) -> str:
        template = load_prompt(self.prompts_dir, prompt_name)
        return (
            template.replace(
                "<<<JOB_DESCRIPTION>>>",
                job_description.strip() or "(No job description provided)",
            ).replace("<<<RESUME_TEXT>>>", resume_text.strip())
        )

    @staticmethod
    def _normalize_missing_skills(items: list[Any]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for item in items:
            if isinstance(item, str):
                skill = item.strip()
                if skill:
                    normalized.append(
                        {
                            "skill": skill,
                            "reason": "Important for role alignment and ATS matching.",
                        }
                    )
                continue

            if not isinstance(item, dict):
                raise ClaudeServiceError("missing_skills items must be objects or strings.")

            skill = str(item.get("skill", "")).strip()
            reason = str(item.get("reason", "")).strip()
            if not skill or not reason:
                raise ClaudeServiceError(
                    "Each missing_skills item must include skill and reason."
                )
            normalized.append({"skill": skill, "reason": reason})

        return normalized

    @staticmethod
    def _normalize_strengths(items: list[Any]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for item in items:
            if isinstance(item, str):
                title = item.strip()
                if title:
                    normalized.append(
                        {
                            "title": title,
                            "reason": "Supports interview probability for the target role.",
                        }
                    )
                continue

            if not isinstance(item, dict):
                raise ClaudeServiceError("strengths items must be objects or strings.")

            title = str(item.get("title") or item.get("strength") or "").strip()
            reason = str(item.get("reason", "")).strip()
            if not title or not reason:
                raise ClaudeServiceError(
                    "Each strengths item must include title and reason."
                )
            normalized.append({"title": title, "reason": reason})

        return normalized

    def _normalize_suggestions(self, items: list[Any]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for item in items:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    normalized.append(
                        {
                            "reason": text,
                            "example": "Provide a concrete rewrite grounded in your real experience.",
                            "impact": "Improves clarity and interview probability.",
                        }
                    )
                continue

            if not isinstance(item, dict):
                raise ClaudeServiceError("suggestions items must be objects or strings.")

            missing = self.REQUIRED_SUGGESTION_KEYS - set(item.keys())
            if missing:
                raise ClaudeServiceError(
                    "Each suggestion must include: "
                    + ", ".join(sorted(self.REQUIRED_SUGGESTION_KEYS))
                )

            reason = str(item.get("reason", "")).strip()
            example = str(item.get("example", "")).strip()
            impact = str(item.get("impact", "")).strip()
            if not reason or not example or not impact:
                raise ClaudeServiceError(
                    "Each suggestion reason, example, and impact must be non-empty."
                )

            normalized.append(
                {
                    "reason": reason,
                    "example": example,
                    "impact": impact,
                }
            )

        return normalized

    def _normalize_sections(self, sections: Any) -> dict[str, Any]:
        if not isinstance(sections, dict):
            raise ClaudeServiceError("sections must be an object.")

        missing = self.REQUIRED_SECTION_KEYS - set(sections.keys())
        if missing:
            raise ClaudeServiceError(
                "sections is missing keys: " + ", ".join(sorted(missing))
            )

        normalized: dict[str, Any] = {}
        for key in self.REQUIRED_SECTION_KEYS:
            section = sections.get(key)
            if not isinstance(section, dict):
                raise ClaudeServiceError(f"sections.{key} must be an object.")

            try:
                score = int(section.get("score", 0))
            except (TypeError, ValueError) as exc:
                raise ClaudeServiceError(
                    f"sections.{key}.score must be an integer."
                ) from exc

            score = max(0, min(100, score))

            issues_raw = section.get("issues", [])
            if not isinstance(issues_raw, list):
                raise ClaudeServiceError(f"sections.{key}.issues must be a list.")

            issues: list[dict[str, str]] = []
            for item in issues_raw:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        issues.append(
                            {
                                "type": "general",
                                "description": text,
                                "severity": "medium",
                            }
                        )
                    continue

                if not isinstance(item, dict):
                    raise ClaudeServiceError(
                        f"sections.{key}.issues items must be objects or strings."
                    )

                issue_type = str(item.get("type", "general")).strip() or "general"
                description = str(item.get("description", "")).strip()
                severity = str(item.get("severity", "medium")).strip().lower()
                if severity not in self.VALID_SEVERITIES:
                    severity = "medium"
                if description:
                    issues.append(
                        {
                            "type": issue_type,
                            "description": description,
                            "severity": severity,
                        }
                    )

            def string_list(value: Any) -> list[str]:
                if not isinstance(value, list):
                    return []
                return [str(entry).strip() for entry in value if str(entry).strip()]

            normalized[key] = {
                "score": score,
                "strengths": string_list(section.get("strengths")),
                "weaknesses": string_list(section.get("weaknesses")),
                "issues": issues,
                "suggested_improvements": string_list(
                    section.get("suggested_improvements")
                ),
            }

        return normalized

    def _validate_analysis(self, analysis: dict[str, Any]) -> dict[str, Any]:
        # Backward-compatible default if older prompt variants omit explanation.
        if "ats_explanation" not in analysis:
            analysis["ats_explanation"] = ""

        # Allow older responses without sections by synthesizing a minimal map.
        if "sections" not in analysis:
            resume_match = analysis.get("resume_match") or {}

            def safe_score(value: Any, fallback: int = 0) -> int:
                try:
                    return max(0, min(100, int(value)))
                except (TypeError, ValueError):
                    return fallback

            overall = safe_score(analysis.get("ats_score"), 0)
            analysis["sections"] = {
                "summary": {
                    "score": overall,
                    "strengths": [],
                    "weaknesses": [],
                    "issues": [],
                    "suggested_improvements": [],
                },
                "experience": {
                    "score": safe_score(resume_match.get("experience"), overall),
                    "strengths": [],
                    "weaknesses": [],
                    "issues": [],
                    "suggested_improvements": [],
                },
                "projects": {
                    "score": safe_score(resume_match.get("projects"), overall),
                    "strengths": [],
                    "weaknesses": [],
                    "issues": [],
                    "suggested_improvements": [],
                },
                "skills": {
                    "score": safe_score(resume_match.get("skills"), overall),
                    "strengths": [],
                    "weaknesses": [],
                    "issues": [],
                    "suggested_improvements": [],
                },
            }

        missing = self.REQUIRED_ANALYSIS_KEYS - set(analysis.keys())
        if missing:
            raise ClaudeServiceError(
                f"Claude JSON is missing keys: {', '.join(sorted(missing))}"
            )

        resume_match = analysis.get("resume_match")
        if not isinstance(resume_match, dict):
            raise ClaudeServiceError("resume_match must be an object.")

        missing_match = self.REQUIRED_MATCH_KEYS - set(resume_match.keys())
        if missing_match:
            raise ClaudeServiceError(
                "resume_match is missing keys: "
                + ", ".join(sorted(missing_match))
            )

        if not isinstance(analysis.get("missing_skills"), list):
            raise ClaudeServiceError("missing_skills must be a list.")
        if not isinstance(analysis.get("strengths"), list):
            raise ClaudeServiceError("strengths must be a list.")
        if not isinstance(analysis.get("suggestions"), list):
            raise ClaudeServiceError("suggestions must be a list.")
        if not isinstance(analysis.get("optimized_summary"), str):
            raise ClaudeServiceError("optimized_summary must be a string.")
        if not isinstance(analysis.get("ats_explanation"), str):
            raise ClaudeServiceError("ats_explanation must be a string.")

        try:
            analysis["ats_score"] = int(analysis["ats_score"])
            analysis["resume_match"] = {
                key: int(resume_match[key]) for key in self.REQUIRED_MATCH_KEYS
            }
        except (TypeError, ValueError) as exc:
            raise ClaudeServiceError(
                "Score fields must be numeric integers."
            ) from exc

        analysis["ats_explanation"] = analysis["ats_explanation"].strip()
        analysis["optimized_summary"] = analysis["optimized_summary"].strip()
        analysis["missing_skills"] = self._normalize_missing_skills(
            analysis["missing_skills"]
        )
        analysis["strengths"] = self._normalize_strengths(analysis["strengths"])
        analysis["suggestions"] = self._normalize_suggestions(analysis["suggestions"])
        analysis["sections"] = self._normalize_sections(analysis["sections"])

        if len(analysis["strengths"]) < 3:
            raise ClaudeServiceError("strengths must contain at least 3 items.")
        if len(analysis["suggestions"]) < 3:
            raise ClaudeServiceError("suggestions must contain at least 3 items.")
        if not analysis["ats_explanation"]:
            raise ClaudeServiceError("ats_explanation cannot be empty.")
        if not analysis["optimized_summary"]:
            raise ClaudeServiceError("optimized_summary cannot be empty.")

        return analysis

    def analyze_resume(
        self,
        resume_text: str,
        job_description: str = "",
        prompt_name: str = "resume_analysis.txt",
    ) -> dict[str, Any]:
        if not resume_text.strip():
            raise ClaudeServiceError("Resume text is empty.")

        prompt = self.build_resume_analysis_prompt(
            resume_text,
            job_description,
            prompt_name=prompt_name,
        )
        analysis = self.json_client.request_json(
            prompt,
            max_tokens=8000,
            operation="analyze_resume",
        )
        return self._validate_analysis(analysis)
