import os
from pathlib import Path
from typing import Any

import anthropic

from services.claude_client import ClaudeJsonClient
from services.errors import ClaudeServiceError
from services.prompt_loader import load_prompt


class RewriteService:
    """Dedicated service for Claude-powered resume rewrites."""

    REQUIRED_KEYS = {"summary", "experience", "projects", "skills"}

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
            focus_instruction = "Rewrite all sections thoroughly and evenly."

        return (
            template.replace(
                "<<<JOB_DESCRIPTION>>>",
                job_description.strip() or "(No job description provided)",
            )
            .replace("<<<RESUME_TEXT>>>", resume_text.strip())
            .replace("<<<FOCUS_INSTRUCTION>>>", focus_instruction)
        )

    def _normalize_rewrite(self, rewrite: dict[str, Any]) -> dict[str, Any]:
        # Accept legacy key from earlier prompt versions.
        if "summary" not in rewrite and isinstance(
            rewrite.get("professional_summary"), str
        ):
            rewrite["summary"] = rewrite["professional_summary"]

        missing = self.REQUIRED_KEYS - set(rewrite.keys())
        if missing:
            raise ClaudeServiceError(
                f"Claude rewrite JSON is missing keys: {', '.join(sorted(missing))}"
            )

        if not isinstance(rewrite.get("summary"), str):
            raise ClaudeServiceError("summary must be a string.")

        for key in ("experience", "projects", "skills"):
            value = rewrite.get(key)
            if not isinstance(value, list):
                raise ClaudeServiceError(f"{key} must be a list.")
            rewrite[key] = [str(item).strip() for item in value if str(item).strip()]

        rewrite["summary"] = rewrite["summary"].strip()
        if not rewrite["summary"]:
            raise ClaudeServiceError("summary cannot be empty.")

        return {
            "summary": rewrite["summary"],
            "experience": rewrite["experience"],
            "projects": rewrite["projects"],
            "skills": rewrite["skills"],
        }

    def rewrite_resume(
        self,
        resume_text: str,
        job_description: str,
        prompt_name: str = "resume_rewrite.txt",
        focus_section: str | None = None,
    ) -> dict[str, Any]:
        if not resume_text.strip():
            raise ClaudeServiceError("Resume text is empty.")
        if not job_description.strip():
            raise ClaudeServiceError("Job description is required for rewrite.")

        section = (focus_section or "").strip().lower() or None
        if section and section not in self.REQUIRED_KEYS:
            raise ClaudeServiceError(
                "focus_section must be one of: summary, experience, projects, skills."
            )

        prompt = self.build_prompt(
            resume_text,
            job_description,
            prompt_name=prompt_name,
            focus_section=section,
        )
        rewrite = self.json_client.request_json(
            prompt,
            max_tokens=3500,
            operation="rewrite_resume",
        )
        return self._normalize_rewrite(rewrite)
