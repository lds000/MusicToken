"""Spotify Connect backend powered by spotipy.

Notes:
- We use ``SpotifyOAuth`` with a cache file so the user only has to log in
  once (via the admin UI).
- Playback is sent to the Spotify Connect device whose name matches
  ``device_name`` in config. Set the Pi up as a Spotify Connect endpoint
  (e.g. via raspotify) so this name resolves to the Pi itself.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from .base import Player

log = logging.getLogger(__name__)

DEFAULT_SCOPE = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "playlist-read-private"
)


class SpotifyPlayer(Player):
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self._lock = threading.Lock()
        self._sp = None
        self._device_id: Optional[str] = None

    # -- lazy connection ------------------------------------------------

    def _client(self):
        if self._sp is not None:
            return self._sp
        try:
            import spotipy  # type: ignore
            from spotipy.oauth2 import SpotifyOAuth  # type: ignore
        except ImportError as exc:
            raise RuntimeError("spotipy is required for the Spotify player") from exc

        client_id = self.cfg.get("client_id") or ""
        client_secret = self.cfg.get("client_secret") or ""
        redirect_uri = self.cfg.get("redirect_uri") or "http://localhost:8080/spotify/callback"
        cache_path = self.cfg.get("cache_path") or "config/.spotify_cache"

        if not client_id or not client_secret:
            raise RuntimeError(
                "Spotify client_id / client_secret missing in config.player.spotify"
            )

        auth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=DEFAULT_SCOPE,
            cache_path=cache_path,
            open_browser=False,
        )
        self._sp = spotipy.Spotify(auth_manager=auth)
        return self._sp

    def _resolve_device(self) -> Optional[str]:
        target = (self.cfg.get("device_name") or "").strip().lower()
        try:
            devices = self._client().devices().get("devices", [])
        except Exception:
            log.exception("Failed to list Spotify devices")
            return None
        if not devices:
            return None
        if target:
            for d in devices:
                if d.get("name", "").strip().lower() == target:
                    self._device_id = d["id"]
                    return self._device_id
        # fall back to first active device
        for d in devices:
            if d.get("is_active"):
                self._device_id = d["id"]
                return self._device_id
        self._device_id = devices[0]["id"]
        return self._device_id

    # -- Player API -----------------------------------------------------

    def play(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            sp = self._client()
            uri = payload.get("uri")
            uris: Optional[List[str]] = None
            context_uri: Optional[str] = None
            if not uri:
                raise ValueError("Spotify payload requires a 'uri' field")
            if uri.startswith("spotify:track:"):
                uris = [uri]
            else:
                context_uri = uri

            device_id = self._resolve_device()
            sp.start_playback(
                device_id=device_id,
                context_uri=context_uri,
                uris=uris,
            )
            shuffle = bool(payload.get("shuffle", False))
            try:
                sp.shuffle(shuffle, device_id=device_id)
            except Exception:
                log.debug("Could not toggle shuffle", exc_info=True)

            return self.now_playing() or {
                "title": payload.get("label", uri),
                "source": "spotify",
                "uri": uri,
                "is_playing": True,
            }

    def pause(self) -> None:
        try:
            self._client().pause_playback(device_id=self._device_id)
        except Exception:
            log.exception("Spotify pause failed")

    def resume(self) -> None:
        try:
            self._client().start_playback(device_id=self._device_id)
        except Exception:
            log.exception("Spotify resume failed")

    def stop(self) -> None:
        self.pause()

    def skip(self) -> None:
        try:
            self._client().next_track(device_id=self._device_id)
        except Exception:
            log.exception("Spotify skip failed")

    def now_playing(self) -> Optional[Dict[str, Any]]:
        try:
            cur = self._client().current_playback()
        except Exception:
            log.exception("Spotify current_playback failed")
            return None
        if not cur or not cur.get("item"):
            return None
        item = cur["item"]
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        return {
            "title": item.get("name", ""),
            "artist": artists,
            "source": "spotify",
            "uri": item.get("uri", ""),
            "is_playing": cur.get("is_playing", False),
            "image": (item.get("album", {}).get("images") or [{}])[0].get("url"),
        }
