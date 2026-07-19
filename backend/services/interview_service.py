import json
import os
from pathlib import Path
from typing import Any

import anthropic

from services.claude_client import ClaudeJsonClient
from services.errors import ClaudeServiceError
from services.prompt_loader import load_prompt


class InterviewService:
    """Claude-powered interview question generation and answer evaluation."""

    VALID_CATEGORIES = {"Behavioral", "Technical"}

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

    def _load_with_shared(self, prompt_name: str) -> str:
        template = load_prompt(self.prompts_dir, prompt_name)
        shared = load_prompt(self.prompts_dir, "shared_rules.txt")
        return template.replace("<<<SHARED_RULES>>>", shared)

    @staticmethod
    def _string_list(value: Any, *, max_items: int = 6) -> list[str]:
        if not isinstance(value, list):
            return []
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
            if len(items) >= max_items:
                break
        return items

    def _normalize_questions(self, payload: dict[str, Any]) -> dict[str, Any]:
        questions = payload.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ClaudeServiceError("Interview questions list is empty.")

        if len(questions) < 8 or len(questions) > 10:
            # Soft clamp: accept 6–12 but prefer 8–10; reject if clearly wrong.
            if len(questions) < 6 or len(questions) > 12:
                raise ClaudeServiceError(
                    "Interview must include between 8 and 10 questions."
                )

        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(questions[:10], start=1):
            if not isinstance(item, dict):
                raise ClaudeServiceError("Each interview question must be an object.")

            question = str(item.get("question", "")).strip()
            if not question:
                raise ClaudeServiceError("Interview question text cannot be empty.")

            category = str(item.get("category", "")).strip()
            if category not in self.VALID_CATEGORIES:
                lowered = category.lower()
                if "tech" in lowered:
                    category = "Technical"
                else:
                    category = "Behavioral"

            try:
                qid = int(item.get("id", index))
            except (TypeError, ValueError):
                qid = index

            normalized.append(
                {
                    "id": qid if qid > 0 else index,
                    "category": category,
                    "question": question,
                }
            )

        # Re-number sequentially for UI stability.
        for index, item in enumerate(normalized, start=1):
            item["id"] = index

        return {"questions": normalized}

    def _normalize_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            score = int(payload.get("score", 0))
        except (TypeError, ValueError) as exc:
            raise ClaudeServiceError("Interview score must be an integer.") from exc

        score = max(0, min(100, score))
        feedback_raw = payload.get("feedback")
        if not isinstance(feedback_raw, dict):
            feedback_raw = {}

        follow_up = str(payload.get("follow_up", "")).strip()
        if not follow_up:
            follow_up = "Can you walk me through a concrete example with more detail?"

        return {
            "score": score,
            "feedback": {
                "strengths": self._string_list(feedback_raw.get("strengths"), max_items=3),
                "weaknesses": self._string_list(
                    feedback_raw.get("weaknesses"), max_items=3
                ),
                "improvements": self._string_list(
                    feedback_raw.get("improvements"), max_items=3
                ),
            },
            "follow_up": follow_up,
        }

    def _normalize_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            overall = int(payload.get("overall_score", 0))
        except (TypeError, ValueError) as exc:
            raise ClaudeServiceError("overall_score must be an integer.") from exc

        improvements = self._string_list(payload.get("improvements"), max_items=5)
        while len(improvements) < 5:
            improvements.append(
                "Practice answering with a clearer situation, action, and measurable result."
            )

        return {
            "overall_score": max(0, min(100, overall)),
            "strengths": self._string_list(payload.get("strengths"), max_items=4),
            "weaknesses": self._string_list(payload.get("weaknesses"), max_items=4),
            "improvements": improvements[:5],
            "learning_topics": self._string_list(
                payload.get("learning_topics"), max_items=6
            ),
        }

    def start_interview(
        self, resume_text: str, job_description: str
    ) -> dict[str, Any]:
        if not resume_text.strip():
            raise ClaudeServiceError("Resume text is empty.")

        template = self._load_with_shared("interview_start.txt")
        prompt = (
            template.replace(
                "<<<JOB_DESCRIPTION>>>",
                job_description.strip() or "(No job description provided)",
            ).replace("<<<RESUME_TEXT>>>", resume_text.strip())
        )

        payload = self.json_client.request_json(
            prompt,
            max_tokens=2500,
            operation="interview_start",
        )
        return self._normalize_questions(payload)

    def evaluate_answer(
        self,
        *,
        question: str,
        answer: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        question_text = (question or "").strip()
        if not question_text:
            raise ClaudeServiceError("Interview question is required.")

        history_json = json.dumps(history or [], ensure_ascii=False, indent=2)
        template = self._load_with_shared("interview_answer.txt")
        prompt = (
            template.replace("<<<HISTORY_JSON>>>", history_json)
            .replace("<<<QUESTION>>>", question_text)
            .replace(
                "<<<ANSWER>>>",
                (answer or "").strip() or "(No answer provided)",
            )
        )

        payload = self.json_client.request_json(
            prompt,
            max_tokens=1800,
            operation="interview_answer",
        )
        return self._normalize_evaluation(payload)

    def summarize_interview(
        self,
        *,
        resume_text: str,
        job_description: str,
        turns: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not turns:
            raise ClaudeServiceError("Interview turns are required for summary.")

        template = self._load_with_shared("interview_summary.txt")
        prompt = (
            template.replace(
                "<<<JOB_DESCRIPTION>>>",
                job_description.strip() or "(No job description provided)",
            )
            .replace(
                "<<<RESUME_TEXT>>>",
                resume_text.strip() or "(Empty resume)",
            )
            .replace(
                "<<<TURNS_JSON>>>",
                json.dumps(turns, ensure_ascii=False, indent=2),
            )
        )

        payload = self.json_client.request_json(
            prompt,
            max_tokens=2200,
            operation="interview_summary",
        )
        return self._normalize_summary(payload)
