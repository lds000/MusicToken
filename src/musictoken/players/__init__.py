"""Music player backends.

A 'player' knows how to start/stop audio in response to action payloads.
The default ``mock`` player just logs and emits events, which is enough
to drive the UI during development.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import Player
from .mock import MockPlayer

log = logging.getLogger(__name__)


def build_player(cfg: Dict[str, Any]) -> Player:
    backend = (cfg.get("backend") or "mock").lower()

    if backend == "mock":
        return MockPlayer()

    if backend == "spotify":
        from .spotify_player import SpotifyPlayer

        return SpotifyPlayer(cfg.get("spotify", {}) or {})

    if backend == "vlc":
        from .vlc_player import VLCPlayer

        return VLCPlayer(cfg.get("vlc", {}) or {})

    log.warning("Unknown player backend %r — using mock.", backend)
    return MockPlayer()


__all__ = ["Player", "MockPlayer", "build_player"]
