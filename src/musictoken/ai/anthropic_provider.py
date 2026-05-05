"""Anthropic Messages provider."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

import requests

from .base import AIError, AIProvider, extract_json

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-3-5-haiku-latest"
DEFAULT_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.api_key = cfg.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = cfg.get("model") or DEFAULT_MODEL
        self.base_url = cfg.get("base_url") or DEFAULT_URL
        self.timeout = float(cfg.get("timeout", 30.0))
        self.max_tokens = int(cfg.get("max_tokens", 1024))

    def complete_json(self, *, system: str, user: str) -> Dict[str, Any]:
        if not self.api_key:
            raise AIError("Anthropic api_key not configured")
        # Append an explicit JSON instruction; Anthropic doesn't have a
        # dedicated json mode flag, but it follows the instruction reliably.
        system_full = system + "\n\nRespond with a single JSON object and nothing else."
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_full,
            "messages": [{"role": "user", "content": user}],
        }
        try:
            resp = requests.post(
                self.base_url,
                json=body,
                timeout=self.timeout,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
            )
        except requests.RequestException as exc:
            raise AIError(f"Anthropic request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise AIError(f"Anthropic {resp.status_code}: {resp.text[:300]}")
        try:
            blocks = resp.json().get("content", [])
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except Exception as exc:
            raise AIError(f"Unexpected Anthropic response: {resp.text[:200]}") from exc
        return extract_json(text)
