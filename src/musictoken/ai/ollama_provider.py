"""Ollama provider — talk to a local model (e.g. llama3.2)."""
from __future__ import annotations

import logging
from typing import Any, Dict

import requests

from .base import AIError, AIProvider, extract_json

log = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.base_url = (cfg.get("base_url") or "http://localhost:11434").rstrip("/")
        self.model = cfg.get("model") or "llama3.2"
        self.timeout = float(cfg.get("timeout", 60.0))

    def complete_json(self, *, system: str, user: str) -> Dict[str, Any]:
        body = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat", json=body, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise AIError(f"Ollama request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise AIError(f"Ollama {resp.status_code}: {resp.text[:300]}")
        try:
            content = resp.json()["message"]["content"]
        except Exception as exc:
            raise AIError(f"Unexpected Ollama response: {resp.text[:200]}") from exc
        return extract_json(content)
