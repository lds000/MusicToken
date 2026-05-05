"""Action runner: turns a scanned chip into a behavior.

Action types currently understood:

==============  =========================================================
``spotify``     payload: ``{"uri": "spotify:..."}`` — start Spotify playback
``radio``       payload: ``{"url": "https://..."}`` — VLC stream
``url``         payload: ``{"url": "..."}`` — generic URL handed to player
``mood``        payload: ``{"mood": "chill"}`` — picks a random chip with
                that genre and re-runs its action
``command``     payload: ``{"command": "skip"}`` — control verbs (skip,
                pause, resume, stop, wild). ``wild`` re-fires a random
                chip.
``shell``       payload: ``{"shell": "..."}`` — runs an arbitrary command
                (advanced; used for smart-home triggers)
==============  =========================================================
"""
from __future__ import annotations

import logging
import random
import shlex
import subprocess
import threading
from typing import Any, Dict, Optional

from .events import EventBus
from .players.base import Player
from .registry import Chip, ChipRegistry

log = logging.getLogger(__name__)


class ActionRunner:
    def __init__(
        self,
        registry: ChipRegistry,
        player: Player,
        bus: EventBus,
        commands_cfg: Optional[Dict[str, Any]] = None,
        suggester: Optional[Any] = None,
    ) -> None:
        self.registry = registry
        self.player = player
        self.bus = bus
        self.commands_cfg = commands_cfg or {}
        self.suggester = suggester
        self._lock = threading.Lock()

    # Public entry: called by the NFC reader on every (debounced) scan.
    def handle_scan(self, uid: str) -> None:
        chip = self.registry.get(uid)
        self.bus.publish(
            "scan",
            {
                "uid": uid,
                "known": chip is not None,
                "chip": chip.to_dict() if chip else None,
            },
        )
        if chip is None:
            log.info("Scanned unknown chip %s — ignoring (program it first).", uid)
            return
        self.registry.mark_scanned(uid)
        self.run_chip(chip)

    def run_chip(self, chip: Chip) -> None:
        with self._lock:
            try:
                self._dispatch(chip)
            except Exception:
                log.exception("Action failed for chip %s", chip.uid)
                self.bus.publish(
                    "error",
                    {"uid": chip.uid, "message": "Action failed; see logs."},
                )

    # ------------------------------------------------------------------

    def _dispatch(self, chip: Chip) -> None:
        action = (chip.action_type or "").lower()
        payload = dict(chip.payload or {})
        payload.setdefault("label", chip.label)

        if action == "spotify":
            np = self.player.play({**payload, "source": "spotify"})
            self.bus.publish("now_playing", np)
            return
        if action in ("radio", "url"):
            np = self.player.play({**payload, "source": action})
            self.bus.publish("now_playing", np)
            return
        if action == "mood":
            return self._dispatch_mood(payload)
        if action == "command":
            return self._dispatch_command(payload)
        if action == "shell":
            return self._dispatch_shell(payload)

        log.warning("Unknown action type %r on chip %s", action, chip.uid)

    def _dispatch_mood(self, payload: Dict[str, Any]) -> None:
        mood = (payload.get("mood") or payload.get("genre") or "").strip()
        if not mood:
            log.warning("Mood action missing 'mood' field")
            return
        choices = [
            c
            for c in self.registry.by_genre(mood)
            if c.action_type in ("spotify", "radio", "url")
        ]
        if not choices:
            log.info("No chips found for mood %r", mood)
            return
        pick = random.choice(choices)
        log.info("Mood %r picked chip %s (%s)", mood, pick.uid, pick.label)
        self._dispatch(pick)

    def _dispatch_command(self, payload: Dict[str, Any]) -> None:
        cmd = (payload.get("command") or "").lower()
        if cmd == "skip":
            self.player.skip()
            self.bus.publish("command", {"command": "skip"})
        elif cmd == "pause":
            self.player.pause()
            self.bus.publish("command", {"command": "pause"})
        elif cmd == "resume":
            self.player.resume()
            self.bus.publish("command", {"command": "resume"})
        elif cmd in ("stop", "clear"):
            self.player.stop()
            self.bus.publish("now_playing", {})
        elif cmd == "wild":
            self._dispatch_wild()
        else:
            log.warning("Unknown command %r", cmd)

        # Optional shell hook from config (e.g. fire smart-home webhook).
        spec = (self.commands_cfg.get(cmd) or {}) if cmd else {}
        shell = spec.get("shell") if isinstance(spec, dict) else None
        if shell:
            self._run_shell(shell)

    def _dispatch_wild(self) -> None:
        chips = [
            c
            for c in self.registry.all()
            if c.action_type in ("spotify", "radio", "url")
        ]
        if not chips:
            log.info("WILD: registry has no playable chips yet.")
            return

        # Try AI-flavored pick first; fall back to pure random.
        pick = None
        if self.suggester is not None:
            try:
                pick = self.suggester.pick_wild(context="wild button")
            except Exception:
                log.exception("AI WILD pick failed; falling back to random.")
                pick = None
        if pick is None:
            pick = random.choice(chips)
        log.info("WILD picked %s (%s)", pick.uid, pick.label)
        self._dispatch(pick)

    def _dispatch_shell(self, payload: Dict[str, Any]) -> None:
        shell = payload.get("shell")
        if not shell:
            log.warning("Shell action missing 'shell' field")
            return
        self._run_shell(shell)

    def _run_shell(self, shell: str) -> None:
        log.info("[shell] %s", shell)
        try:
            subprocess.Popen(  # noqa: S603 - intentional, configured by user
                shlex.split(shell),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            log.exception("Shell command failed: %s", shell)
