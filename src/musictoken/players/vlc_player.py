"""Local VLC playback backend. Useful for local files + internet radio."""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from .base import Player

log = logging.getLogger(__name__)


class VLCPlayer(Player):
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self._lock = threading.Lock()
        self._instance = None
        self._player = None
        self._state: Optional[Dict[str, Any]] = None

    def _ensure(self):
        if self._player is not None:
            return
        try:
            import vlc  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "python-vlc is required for the VLC player (see requirements-pi.txt)"
            ) from exc
        self._instance = vlc.Instance("--no-video", "--quiet")
        self._player = self._instance.media_player_new()
        self._player.audio_set_volume(int(self.cfg.get("volume", 80)))

    def play(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._ensure()
            url = payload.get("url") or payload.get("uri")
            if not url:
                raise ValueError("VLC payload requires 'url'")
            media = self._instance.media_new(url)
            self._player.set_media(media)
            self._player.play()
            self._state = {
                "title": payload.get("title", url),
                "artist": payload.get("artist", ""),
                "source": payload.get("source", "vlc"),
                "uri": url,
                "is_playing": True,
            }
            return dict(self._state)

    def pause(self) -> None:
        with self._lock:
            if self._player:
                self._player.pause()
                if self._state:
                    self._state["is_playing"] = False

    def resume(self) -> None:
        with self._lock:
            if self._player:
                self._player.play()
                if self._state:
                    self._state["is_playing"] = True

    def stop(self) -> None:
        with self._lock:
            if self._player:
                self._player.stop()
            self._state = None

    def skip(self) -> None:
        # VLC backend has no queue; skip == stop.
        self.stop()

    def now_playing(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._state) if self._state else None

    def close(self) -> None:
        self.stop()
