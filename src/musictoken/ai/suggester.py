"""Suggester service.

Glues an :class:`AIProvider` to MusicToken's data model. The Flask routes
call into this layer; this layer shapes prompts, validates output, and
returns clean dicts safe to render.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from ..registry import Chip, ChipRegistry
from .base import AIError, AIProvider

log = logging.getLogger(__name__)

VALID_GENRES = {"rock", "chill", "party", "dinner", "norway", "news", "wild"}
VALID_ACTIONS = {"spotify", "radio", "url", "mood", "command", "shell"}

SUGGEST_SYSTEM = """You are MusicToken's music librarian.

The user owns a physical NFC-token music system. Each token triggers one
playback action. Given a vibe prompt and the existing library, propose
new tokens that would complement it.

Rules:
- Output ONE JSON object: {"suggestions": [ ... ]}.
- Each suggestion has: label (UPPERCASE 'ARTIST / WORK', max 32 chars),
  genre (one of: rock, chill, party, dinner, norway, news, wild),
  action_type (almost always "spotify"; use "radio" for live streams),
  payload (object), reason (short, 1 sentence).
- For Spotify, payload = {"uri": "spotify:album:...|spotify:track:...|spotify:playlist:..."}.
- For radio,  payload = {"url": "https://..."}.
- Avoid duplicating items already in the library (by label or URI).
- Keep labels punchy and uppercase; the chip text band is small.
"""

PICK_SYSTEM = """You are MusicToken's DJ. Pick a single chip from the
provided library that best fits the context. Output ONE JSON object:
{"uid": "<the chip uid>", "reason": "<short>"}. The uid MUST exist in the
library. If the library is empty, return {"uid": null, "reason": "..."}.
"""

AUTOFILL_SYSTEM = """You are MusicToken's metadata helper. Given a
payload object (a Spotify URI or a stream URL) and the user's action_type,
return a JSON object: {"label": "...", "genre": "...", "reason": "..."}.

The label should be UPPERCASE in the form 'ARTIST / WORK' (max 32 chars).
The genre must be one of: rock, chill, party, dinner, norway, news, wild.
"""


class Suggester:
    def __init__(self, provider: AIProvider, registry: ChipRegistry) -> None:
        self.provider = provider
        self.registry = registry

    # ------------------------------------------------------------------

    def suggest_chips(self, prompt: str, count: int = 6) -> List[Dict[str, Any]]:
        count = max(1, min(int(count), 20))
        existing = [
            {"label": c.label, "genre": c.genre, "uri": (c.payload or {}).get("uri")}
            for c in self.registry.all()
            if c.label
        ]
        user = (
            f"vibe prompt: {prompt}\n"
            f"count: {count}\n"
            f"existing library: {json.dumps(existing, ensure_ascii=False)}\n"
        )
        try:
            data = self.provider.complete_json(system=SUGGEST_SYSTEM, user=user)
        except AIError as exc:
            log.warning("AI suggest failed: %s", exc)
            raise

        raw = data.get("suggestions") or []
        if not isinstance(raw, list):
            raise AIError("AI did not return a 'suggestions' list")

        cleaned: List[Dict[str, Any]] = []
        for item in raw[:count]:
            s = self._validate_suggestion(item)
            if s:
                cleaned.append(s)
        return cleaned

    def pick_wild(self, context: Optional[str] = None) -> Optional[Chip]:
        chips = [
            c
            for c in self.registry.all()
            if c.action_type in ("spotify", "radio", "url")
        ]
        if not chips:
            return None
        slim = [
            {
                "uid": c.uid,
                "label": c.label,
                "genre": c.genre,
                "scans": c.scan_count,
            }
            for c in chips
        ]
        user = f"context: {context or 'no context'}\nlibrary: {json.dumps(slim)}"
        try:
            data = self.provider.complete_json(system=PICK_SYSTEM, user=user)
        except AIError as exc:
            log.warning("AI pick_wild failed: %s — falling back to random.", exc)
            return None
        uid = (data.get("uid") or "").strip()
        if not uid:
            return None
        return self.registry.get(uid)

    def autofill(
        self, payload: Dict[str, Any] | str, action_type: str = ""
    ) -> Dict[str, Any]:
        if isinstance(payload, str):
            payload_str = payload
        else:
            payload_str = json.dumps(payload)
        user = (
            f"action_type: {action_type or 'unknown'}\n"
            f"payload: {payload_str}\n"
        )
        try:
            data = self.provider.complete_json(system=AUTOFILL_SYSTEM, user=user)
        except AIError as exc:
            log.warning("AI autofill failed: %s", exc)
            raise
        return {
            "label": str(data.get("label", "")).strip()[:32],
            "genre": self._coerce_genre(data.get("genre")),
            "reason": str(data.get("reason", "")).strip(),
        }

    # ------------------------------------------------------------------

    def _validate_suggestion(self, item: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(item, dict):
            return None
        label = str(item.get("label", "")).strip()
        if not label:
            return None
        action_type = str(item.get("action_type") or "spotify").strip().lower()
        if action_type not in VALID_ACTIONS:
            action_type = "spotify"
        payload = item.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {"raw": str(payload)}
        # Action-type-specific sanity checks.
        if action_type == "spotify" and not str(payload.get("uri", "")).startswith(
            "spotify:"
        ):
            return None
        if action_type in ("radio", "url") and not payload.get("url"):
            return None
        return {
            "label": label[:48],
            "genre": self._coerce_genre(item.get("genre")),
            "action_type": action_type,
            "payload": payload,
            "reason": str(item.get("reason", "")).strip()[:160],
        }

    @staticmethod
    def _coerce_genre(value: Any) -> str:
        v = str(value or "").strip().lower()
        return v if v in VALID_GENRES else ""
