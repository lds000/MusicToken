"""AI provider interface.

We deliberately keep this surface tiny: every provider must implement
``complete_json``, which takes a system prompt + user prompt and returns
a parsed JSON dict. The Suggester service shapes the prompt and validates
the result.
"""
from __future__ import annotations

import abc
import json
import logging
import re
from typing import Any, Dict

log = logging.getLogger(__name__)


class AIError(RuntimeError):
    """Raised when the AI provider fails or returns unusable output."""


class AIProvider(abc.ABC):
    @abc.abstractmethod
    def complete_json(self, *, system: str, user: str) -> Dict[str, Any]:
        """Return a JSON object from the model.

        Implementations should request JSON-mode where supported and
        fall back to extracting a JSON block from text otherwise.
        """


def extract_json(text: str) -> Dict[str, Any]:
    """Best-effort: pull the first JSON object out of a string."""
    text = (text or "").strip()
    if not text:
        raise AIError("Empty response from AI provider")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find the outermost {...} block.
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise AIError(f"AI response was not JSON: {text[:200]}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AIError(f"AI response was not JSON: {text[:200]}") from exc
