"""OpenAI Chat Completions provider (JSON mode)."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

import requests

from .base import AIError, AIProvider, extract_json

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.api_key = cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        self.model = cfg.get("model") or DEFAULT_MODEL
        self.base_url = cfg.get("base_url") or DEFAULT_URL
        self.timeout = float(cfg.get("timeout", 30.0))
        if not self.api_key:
            log.warning(
                "OpenAI provider has no api_key configured — calls will fail. "
                "Set config.ai.openai.api_key or the OPENAI_API_KEY env var."
            )

    def complete_json(self, *, system: str, user: str) -> Dict[str, Any]:
        if not self.api_key:
            raise AIError("OpenAI api_key not configured")

        body = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            resp = requests.post(
                self.base_url,
                json=body,
                timeout=self.timeout,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except requests.RequestException as exc:
            raise AIError(f"OpenAI request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise AIError(f"OpenAI {resp.status_code}: {resp.text[:300]}")
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            raise AIError(f"Unexpected OpenAI response shape: {resp.text[:200]}") from exc
        return extract_json(content)
