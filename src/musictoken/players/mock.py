"""In-memory mock player. Logs everything; great for dev + tests."""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from .base import Player

log = logging.getLogger(__name__)


class MockPlayer(Player):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Optional[Dict[str, Any]] = None

    def play(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            label = payload.get("label") or payload.get("uri") or "unknown"
            log.info("[mock-player] PLAY %s", label)
            self._state = {
                "title": payload.get("title") or label,
                "artist": payload.get("artist", ""),
                "source": payload.get("source", "mock"),
                "uri": payload.get("uri", ""),
                "is_playing": True,
            }
            return dict(self._state)

    def pause(self) -> None:
        with self._lock:
            log.info("[mock-player] PAUSE")
            if self._state:
                self._state["is_playing"] = False

    def resume(self) -> None:
        with self._lock:
            log.info("[mock-player] RESUME")
            if self._state:
                self._state["is_playing"] = True

    def stop(self) -> None:
        with self._lock:
            log.info("[mock-player] STOP")
            self._state = None

    def skip(self) -> None:
        log.info("[mock-player] SKIP")

    def now_playing(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._state) if self._state else None
