import json
import os
from pathlib import Path
from typing import Any

import anthropic

from services.claude_client import ClaudeJsonClient
from services.errors import ClaudeServiceError
from services.prompt_loader import load_prompt


class ChatService:
    """Career-coach chat powered by the existing Claude client stack."""

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

    def build_system_prompt(
        self,
        *,
        resume_text: str,
        job_description: str,
        analysis: dict[str, Any] | None,
        rewrite: dict[str, Any] | None,
    ) -> str:
        template = load_prompt(self.prompts_dir, "career_coach.txt")
        analysis_json = (
            json.dumps(analysis, ensure_ascii=False, indent=2)
            if isinstance(analysis, dict) and analysis
            else "(No analysis available yet)"
        )
        rewrite_json = (
            json.dumps(rewrite, ensure_ascii=False, indent=2)
            if isinstance(rewrite, dict) and rewrite
            else "(No rewritten resume available yet)"
        )

        return (
            template.replace(
                "<<<JOB_DESCRIPTION>>>",
                job_description.strip() or "(No job description provided)",
            )
            .replace("<<<RESUME_TEXT>>>", resume_text.strip() or "(Empty resume)")
            .replace("<<<ANALYSIS_JSON>>>", analysis_json)
            .replace("<<<REWRITE_JSON>>>", rewrite_json)
        )

    @staticmethod
    def _normalize_history(history: list[Any]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []

        for item in history or []:
            if not isinstance(item, dict):
                continue

            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()
            if role not in {"user", "assistant"} or not content:
                continue

            # Claude requires alternating roles; merge consecutive same-role turns.
            if normalized and normalized[-1]["role"] == role:
                normalized[-1]["content"] = (
                    f"{normalized[-1]['content']}\n\n{content}".strip()
                )
            else:
                normalized.append({"role": role, "content": content})

        # Conversation must start with a user turn.
        while normalized and normalized[0]["role"] != "user":
            normalized.pop(0)

        return normalized[-20:]

    def chat(
        self,
        *,
        resume_text: str,
        job_description: str,
        message: str,
        history: list[Any] | None = None,
        analysis: dict[str, Any] | None = None,
        rewrite: dict[str, Any] | None = None,
    ) -> str:
        if not resume_text.strip():
            raise ClaudeServiceError("Resume text is empty.")

        user_message = message.strip()
        if not user_message:
            raise ClaudeServiceError("Chat message cannot be empty.")

        system_prompt = self.build_system_prompt(
            resume_text=resume_text,
            job_description=job_description,
            analysis=analysis,
            rewrite=rewrite,
        )
        messages = self._normalize_history(history or [])
        messages.append({"role": "user", "content": user_message})

        return self.json_client.request_text(
            system=system_prompt,
            messages=messages,
            max_tokens=2200,
            operation="career_coach_chat",
        )
