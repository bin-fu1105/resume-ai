import json
import logging
import re
import time
from typing import Any

import anthropic

from services.errors import ClaudeServiceError

logger = logging.getLogger("resume_ai.claude")


class ClaudeJsonClient:
    """Shared Claude JSON caller with one automatic retry and usage logging."""

    def __init__(self, client: anthropic.Anthropic, model: str):
        self.client = client
        self.model = model

    @staticmethod
    def extract_text(response: Any) -> str:
        return "\n".join(
            block.text
            for block in response.content
            if hasattr(block, "text") and block.text
        ).strip()

    @staticmethod
    def strip_code_fences(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def _parse_json_object(self, raw_text: str) -> dict[str, Any]:
        cleaned = self.strip_code_fences(raw_text)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ClaudeServiceError(
                "Claude returned data that is not valid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise ClaudeServiceError("Claude JSON must be an object.")

        return payload

    def request_json(
        self,
        prompt: str,
        *,
        max_tokens: int = 2500,
        operation: str = "claude_json",
    ) -> dict[str, Any]:
        retry_count = 0
        last_error: Exception | None = None
        total_prompt_tokens = 0
        total_completion_tokens = 0
        started = time.perf_counter()

        attempts = 2  # initial attempt + one retry on invalid JSON
        for attempt in range(attempts):
            attempt_started = time.perf_counter()
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
            except Exception as exc:
                raise ClaudeServiceError(f"Claude API request failed: {exc}") from exc

            usage = getattr(response, "usage", None)
            prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            attempt_latency_ms = int((time.perf_counter() - attempt_started) * 1000)

            raw_text = self.extract_text(response)

            try:
                payload = self._parse_json_object(raw_text)
            except ClaudeServiceError as exc:
                last_error = exc
                logger.warning(
                    "%s invalid JSON on attempt %s | prompt_tokens=%s "
                    "completion_tokens=%s latency_ms=%s retry_count=%s",
                    operation,
                    attempt + 1,
                    prompt_tokens,
                    completion_tokens,
                    attempt_latency_ms,
                    retry_count,
                )
                if attempt == 0:
                    retry_count = 1
                    continue
                total_latency_ms = int((time.perf_counter() - started) * 1000)
                logger.error(
                    "%s failed after retry | prompt_tokens=%s completion_tokens=%s "
                    "latency_ms=%s retry_count=%s",
                    operation,
                    total_prompt_tokens,
                    total_completion_tokens,
                    total_latency_ms,
                    retry_count,
                )
                raise last_error

            total_latency_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "%s success | prompt_tokens=%s completion_tokens=%s "
                "latency_ms=%s retry_count=%s",
                operation,
                total_prompt_tokens,
                total_completion_tokens,
                total_latency_ms,
                retry_count,
            )
            return payload

        raise ClaudeServiceError("Claude JSON request failed.") from last_error

    def request_text(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 2000,
        operation: str = "claude_text",
    ) -> str:
        started = time.perf_counter()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
        except Exception as exc:
            raise ClaudeServiceError(f"Claude API request failed: {exc}") from exc

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        latency_ms = int((time.perf_counter() - started) * 1000)
        text = self.extract_text(response)

        if not text:
            logger.error(
                "%s empty response | prompt_tokens=%s completion_tokens=%s "
                "latency_ms=%s retry_count=0",
                operation,
                prompt_tokens,
                completion_tokens,
                latency_ms,
            )
            raise ClaudeServiceError("Claude returned an empty response.")

        logger.info(
            "%s success | prompt_tokens=%s completion_tokens=%s "
            "latency_ms=%s retry_count=0",
            operation,
            prompt_tokens,
            completion_tokens,
            latency_ms,
        )
        return text

