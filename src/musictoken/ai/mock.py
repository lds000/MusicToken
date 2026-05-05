"""Mock AI provider — deterministic, useful in dev + tests.

It pattern-matches on the user prompt to return plausible suggestions so
the admin UI is fully functional even with no API keys configured.
"""
from __future__ import annotations

import hashlib
import logging
import random
import re
from typing import Any, Dict, List

from .base import AIProvider

log = logging.getLogger(__name__)

# Tiny seed library used by the mock 'suggest' path.
_SEED = [
    {"label": "FLEETWOOD MAC / DREAMS", "genre": "rock",
     "action_type": "spotify",
     "payload": {"uri": "spotify:track:0ofHAoxe9vBkTCp2UQIavz"}},
    {"label": "EAGLES / HOTEL CALIFORNIA", "genre": "rock",
     "action_type": "spotify",
     "payload": {"uri": "spotify:track:40riOy7x9W7GXjyGp4pjAv"}},
    {"label": "MILES DAVIS / KIND OF BLUE", "genre": "chill",
     "action_type": "spotify",
     "payload": {"uri": "spotify:album:1weenld61qoidwYuZ1GESA"}},
    {"label": "BON IVER / FOR EMMA", "genre": "chill",
     "action_type": "spotify",
     "payload": {"uri": "spotify:album:1xn54DMo2qIqBuMqHtUsFd"}},
    {"label": "DAFT PUNK / DISCOVERY", "genre": "party",
     "action_type": "spotify",
     "payload": {"uri": "spotify:album:2noRn2Aes5aoNVsU6iWThc"}},
    {"label": "LCD SOUNDSYSTEM / DANCE YRSELF", "genre": "party",
     "action_type": "spotify",
     "payload": {"uri": "spotify:track:6l1RZyFy7v0Jm9aBjK5fKr"}},
    {"label": "NORAH JONES / COME AWAY", "genre": "dinner",
     "action_type": "spotify",
     "payload": {"uri": "spotify:album:6ki6CPI3GhPxewvTMyhGgo"}},
    {"label": "SIGRID / SUCKER PUNCH", "genre": "norway",
     "action_type": "spotify",
     "payload": {"uri": "spotify:album:6dq9Vy39IJWxnRCJPuhUpe"}},
    {"label": "AURORA / RUNAWAY", "genre": "norway",
     "action_type": "spotify",
     "payload": {"uri": "spotify:track:5zHyIMrLvomJiMRJ8BnRP4"}},
    {"label": "NRK P1", "genre": "news",
     "action_type": "radio",
     "payload": {"url": "https://lyd.nrk.no/nrk_radio_p1_oslo_mp3_h"}},
    {"label": "NPR NEWS", "genre": "news",
     "action_type": "radio",
     "payload": {"url": "https://npr-ice.streamguys1.com/live.mp3"}},
    {"label": "BRIAN ENO / AMBIENT 1", "genre": "chill",
     "action_type": "spotify",
     "payload": {"uri": "spotify:album:21hGHdqLGFSoX5kIqgvFgr"}},
]


class MockProvider(AIProvider):
    def complete_json(self, *, system: str, user: str) -> Dict[str, Any]:
        log.info("[mock-ai] system=%s user=%s", system[:60], user[:120])

        # Deterministic seed per prompt so repeated calls return the
        # same set, but different prompts return different picks.
        h = hashlib.sha1(user.encode("utf-8")).hexdigest()
        rng = random.Random(int(h[:8], 16))

        sys_l = system.lower()
        if "metadata helper" in sys_l or "autofill" in sys_l:
            return _mock_autofill(user)
        if "pick a single chip" in sys_l or "musictoken's dj" in sys_l:
            return _mock_pick(user, rng)
        return _mock_suggest(user, rng)


def _mock_suggest(user: str, rng: random.Random) -> Dict[str, Any]:
    m = re.search(r"count\s*[:=]\s*(\d+)", user, flags=re.I)
    count = int(m.group(1)) if m else 6
    pool: List[Dict[str, Any]] = list(_SEED)
    rng.shuffle(pool)
    picks = pool[: max(1, min(count, len(pool)))]
    out = []
    for p in picks:
        out.append({**p, "reason": "matched mock vibe"})
    return {"suggestions": out}


def _mock_pick(user: str, rng: random.Random) -> Dict[str, Any]:
    # Caller passes a JSON list of chips; pick one.
    m = re.search(r"\[.*\]", user, flags=re.DOTALL)
    if not m:
        return {"uid": None, "reason": "no chips supplied"}
    import json
    try:
        chips = json.loads(m.group(0))
    except Exception:
        return {"uid": None, "reason": "couldn't parse chip list"}
    if not chips:
        return {"uid": None, "reason": "empty library"}
    pick = rng.choice(chips)
    return {"uid": pick.get("uid"), "reason": "mock random pick"}


def _mock_autofill(user: str) -> Dict[str, Any]:
    label = "UNKNOWN / UNKNOWN"
    genre = "rock"
    if "spotify:" in user:
        kind = re.search(r"spotify:(album|track|playlist|artist):", user)
        if kind:
            label = f"SPOTIFY / {kind.group(1).upper()}"
    if "nrk" in user.lower():
        label, genre = "NRK", "news"
    if "npr" in user.lower():
        label, genre = "NPR NEWS", "news"
    return {"label": label, "genre": genre, "reason": "mock autofill"}
