"""Provider that wraps a primary AI provider and falls back to a backup
when the primary raises :class:`AIError` (quota, network, malformed JSON).

This keeps the UI responsive when OpenAI is rate-limited or out of credit
without requiring any user-visible config change.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import AIError, AIProvider

log = logging.getLogger(__name__)


class FallbackProvider(AIProvider):
    def __init__(self, primary: AIProvider, backup: AIProvider) -> None:
        self.primary = primary
        self.backup = backup
        self._primary_failed = False

    def complete_json(self, *, system: str, user: str) -> Dict[str, Any]:
        if not self._primary_failed:
            try:
                return self.primary.complete_json(system=system, user=user)
            except AIError as exc:
                log.warning(
                    "AI primary provider failed (%s) — falling back to backup. "
                    "Restart the app to re-try the primary.",
                    exc,
                )
                self._primary_failed = True
        return self.backup.complete_json(system=system, user=user)
