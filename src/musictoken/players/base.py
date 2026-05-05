"""Base music-player interface."""
from __future__ import annotations

import abc
from typing import Any, Dict, Optional


class Player(abc.ABC):
    """Minimal music-player surface used by the action runner."""

    @abc.abstractmethod
    def play(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Start playback. Returns a now-playing dict for the UI."""

    def pause(self) -> None:  # pragma: no cover - default no-op
        return None

    def resume(self) -> None:  # pragma: no cover - default no-op
        return None

    def stop(self) -> None:  # pragma: no cover - default no-op
        return None

    def skip(self) -> None:  # pragma: no cover - default no-op
        return None

    def now_playing(self) -> Optional[Dict[str, Any]]:  # pragma: no cover
        return None

    def close(self) -> None:  # pragma: no cover - default no-op
        return None
