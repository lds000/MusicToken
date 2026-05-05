"""Flask app: kiosk player view + admin/programmer."""
from __future__ import annotations

import json
import logging
import queue
import secrets
from typing import Any, Dict, Optional

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template,
    request,
    stream_with_context,
)

from ..actions import ActionRunner
from ..ai import AIError
from ..ai.suggester import Suggester
from ..events import EventBus
from ..nfc.base import NFCReader
from ..players.base import Player
from ..printing import GENRE_COLORS, render_chip_scad, split_label
from ..registry import ChipRegistry

log = logging.getLogger(__name__)

GENRES = [
    ("rock", "Rock", "#8B1A1A"),
    ("chill", "Chill", "#475C7A"),
    ("party", "Party", "#D4A636"),
    ("dinner", "Dinner", "#2F5233"),
    ("norway", "Norway", "#4B2E83"),
    ("news", "News/Radio", "#B8B8B8"),
    ("wild", "Wild", "#111111"),
]

ACTION_TYPES = [
    ("spotify", "Spotify URI"),
    ("radio", "Radio / stream URL"),
    ("url", "Generic URL"),
    ("mood", "Mood (random by genre)"),
    ("command", "Command (skip/pause/resume/stop/wild)"),
    ("shell", "Shell command (advanced)"),
]


def create_app(
    *,
    registry: ChipRegistry,
    runner: ActionRunner,
    reader: NFCReader,
    player: Player,
    bus: EventBus,
    suggester: Optional[Suggester] = None,
) -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["JSON_SORT_KEYS"] = False

    # -- Pages ----------------------------------------------------------

    @app.route("/")
    def index() -> str:
        return render_template("player.html", genres=GENRES)

    @app.route("/admin")
    def admin() -> str:
        filaments = {
            slug: {"name": name, "hex": hex_, "filament": filament}
            for slug, (name, hex_, filament) in GENRE_COLORS.items()
        }
        return render_template(
            "admin.html",
            chips=[c.to_dict() for c in registry.all()],
            genres=GENRES,
            actions=ACTION_TYPES,
            filaments=filaments,
        )

    # -- API ------------------------------------------------------------

    @app.get("/api/state")
    def api_state() -> Any:
        np = bus.last("now_playing")
        scan = bus.last("scan")
        return jsonify(
            {
                "now_playing": np.payload if np else None,
                "last_scan": scan.payload if scan else None,
            }
        )

    @app.get("/api/chips")
    def api_chips() -> Any:
        return jsonify([c.to_dict() for c in registry.all()])

    @app.post("/api/chips")
    def api_chips_create() -> Any:
        data = request.get_json(silent=True) or request.form.to_dict()
        uid = (data.get("uid") or "").strip().upper()
        # Allow saving a designed chip before a physical tag exists by
        # auto-issuing a placeholder UID. Real scans later can be claimed
        # to this design via /api/chips/<uid>/claim.
        if not uid:
            uid = "DESIGN-" + secrets.token_hex(4).upper()
        payload = _coerce_payload(data.get("payload"))
        chip = registry.upsert(
            uid=uid,
            label=(data.get("label") or "").strip(),
            genre=(data.get("genre") or "").strip().lower(),
            action_type=(data.get("action_type") or "").strip().lower(),
            payload=payload,
        )
        return jsonify(chip.to_dict()), 201

    @app.post("/api/chips/<uid>/claim")
    def api_chips_claim(uid: str) -> Any:
        """Re-key a 'DESIGN-...' chip to the UID of a real NFC tag.

        Use this after you've printed the top plate and stuck it on a
        physical tag: tap the tag (or pass new_uid in the body), and the
        registry row is migrated to the real UID.
        """
        data = request.get_json(silent=True) or {}
        new_uid = (data.get("new_uid") or "").strip().upper()
        if not new_uid:
            last = bus.last("scan")
            if last and last.payload.get("uid"):
                new_uid = str(last.payload["uid"]).upper()
        if not new_uid:
            abort(400, "no new_uid provided and no recent scan to use")

        existing = registry.get(uid.upper())
        if not existing:
            abort(404, "no such design")
        if registry.get(new_uid):
            abort(409, f"a chip with uid {new_uid} already exists")

        chip = registry.upsert(
            uid=new_uid,
            label=existing.label,
            genre=existing.genre,
            action_type=existing.action_type,
            payload=existing.payload,
        )
        registry.delete(uid.upper())
        return jsonify(chip.to_dict())

    @app.delete("/api/chips/<uid>")
    def api_chips_delete(uid: str) -> Any:
        ok = registry.delete(uid.upper())
        if not ok:
            abort(404, "no such chip")
        return ("", 204)

    @app.get("/api/chips/<uid>/scad")
    def api_chips_scad(uid: str) -> Any:
        chip = registry.get(uid.upper())
        if not chip:
            abort(404, "no such chip")
        body = render_chip_scad(chip)
        safe = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in (chip.label or chip.uid)
        ).strip("_")[:40] or chip.uid
        resp = Response(body, mimetype="application/x-scad")
        resp.headers["Content-Disposition"] = f'attachment; filename="{safe}.scad"'
        return resp

    @app.get("/api/print_meta")
    def api_print_meta() -> Any:
        """Genre → color + filament reference for the live preview."""
        return jsonify({
            slug: {"name": name, "hex": hex_, "filament": filament}
            for slug, (name, hex_, filament) in GENRE_COLORS.items()
        })

    @app.post("/api/scan")
    def api_simulate_scan() -> Any:
        data = request.get_json(silent=True) or request.form.to_dict()
        uid = (data.get("uid") or "").strip().upper()
        if not uid:
            abort(400, "uid is required")
        reader.inject(uid)
        return jsonify({"ok": True, "uid": uid})

    @app.post("/api/control/<verb>")
    def api_control(verb: str) -> Any:
        verb = verb.lower()
        if verb == "pause":
            player.pause()
        elif verb == "resume":
            player.resume()
        elif verb == "stop":
            player.stop()
            bus.publish("now_playing", {})
        elif verb == "skip":
            player.skip()
        elif verb == "wild":
            runner.run_chip(_FakeChip("wild", "command", {"command": "wild"}))
        else:
            abort(400, f"unknown verb {verb}")
        bus.publish("command", {"command": verb})
        return jsonify({"ok": True, "command": verb})

    # -- AI suggestions -------------------------------------------------

    @app.post("/api/ai/suggest")
    def api_ai_suggest() -> Any:
        if suggester is None:
            abort(503, "AI suggester not configured")
        data = request.get_json(silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        count = int(data.get("count") or 6)
        if not prompt:
            abort(400, "prompt is required")
        try:
            suggestions = suggester.suggest_chips(prompt, count=count)
        except AIError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify({"suggestions": suggestions})

    @app.post("/api/ai/autofill")
    def api_ai_autofill() -> Any:
        if suggester is None:
            abort(503, "AI suggester not configured")
        data = request.get_json(silent=True) or {}
        payload = data.get("payload") or ""
        action_type = (data.get("action_type") or "").strip()
        try:
            result = suggester.autofill(payload, action_type=action_type)
        except AIError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify(result)

    # -- Server-Sent Events --------------------------------------------

    @app.get("/api/events")
    def api_events() -> Response:
        def stream():
            q = bus.subscribe()
            try:
                while True:
                    try:
                        evt = q.get(timeout=15)
                    except queue.Empty:
                        # Heartbeat keeps the connection alive through
                        # proxies and helps the client detect disconnects.
                        yield ": ping\n\n"
                        continue
                    yield f"event: {evt.type}\ndata: {evt.to_json()}\n\n"
            finally:
                bus.unsubscribe(q)

        resp = Response(stream_with_context(stream()), mimetype="text/event-stream")
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Accel-Buffering"] = "no"
        return resp

    return app


# ---------------------------------------------------------------------------


class _FakeChip:
    """Lightweight stand-in for a Chip when invoking the runner from a
    UI control button (e.g. the WILD shortcut on the player screen)."""

    def __init__(self, label: str, action_type: str, payload: Dict[str, Any]):
        self.uid = f"_ui_{label}"
        self.label = label
        self.genre = ""
        self.action_type = action_type
        self.payload = payload


def _coerce_payload(value: Any) -> Dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    return {"value": value}
