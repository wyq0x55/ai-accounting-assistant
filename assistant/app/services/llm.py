"""OpenAI-compatible LLM client (works with Ollama / llama.cpp / vLLM).

Uses only the standard library so the assistant has no hard dependency on
any vendor SDK. When no base URL / API key is configured the client is
considered *disabled* and the pipeline falls back to pure rules.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Optional

from .classifier import Classification

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a strict expense classifier for a personal accounting app. "
    "Given a merchant name and a raw payment message (often Chinese), pick the "
    "single best category from the provided list. Respond with ONLY a compact "
    "JSON object: {\"category\": <one of the list>, \"confidence\": <0..1>, "
    "\"reason\": <short>}. Never invent a category outside the list."
)


class LLMConfig:
    def __init__(
        self,
        base_url: Optional[str],
        api_key: Optional[str],
        model: str,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.model)


class OpenAICompatibleClient:
    """Minimal chat-completions client returning a Classification."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def _chat(self, messages: list[dict], temperature: float = 0.0) -> str:
        url = f"{self.config.base_url}/chat/completions"
        payload = json.dumps(
            {
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.config.api_key:
            req.add_header("Authorization", f"Bearer {self.config.api_key}")
        with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]

    def classify(
        self, merchant: Optional[str], raw_text: str, categories: list[str]
    ) -> Optional[Classification]:
        if not self.enabled:
            return None
        user = (
            f"Categories: {', '.join(categories)}\n"
            f"Merchant: {merchant or 'unknown'}\n"
            f"Message: {raw_text}"
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
        try:
            content = self._chat(messages)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("LLM request failed: %s", exc)
            return None
        return self._parse(content, categories)

    def summarize(self, prompt: str) -> Optional[str]:
        """Free-form natural-language summary for AI monthly reports."""
        if not self.enabled:
            return None
        messages = [
            {
                "role": "system",
                "content": "You are a concise personal-finance analyst. "
                "Answer in the same language as the user's data (Chinese).",
            },
            {"role": "user", "content": prompt},
        ]
        try:
            return self._chat(messages, temperature=0.3).strip()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("LLM summary failed: %s", exc)
            return None

    @staticmethod
    def _parse(content: str, categories: list[str]) -> Optional[Classification]:
        content = content.strip()
        # Tolerate code fences.
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            data = json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            return None
        category = str(data.get("category", "")).strip()
        if category not in categories:
            category = "其他"
        try:
            confidence = float(data.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        confidence = max(0.0, min(1.0, confidence))
        return Classification(
            category=category,
            confidence=confidence,
            source="llm",
            reason=str(data.get("reason", "")).strip()[:200],
        )


def build_client(config: LLMConfig) -> Optional[OpenAICompatibleClient]:
    if not config.enabled:
        logger.info("LLM disabled (no base_url/model); using rules only.")
        return None
    return OpenAICompatibleClient(config)
