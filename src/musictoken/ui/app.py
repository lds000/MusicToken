"""Flask app: kiosk player view + admin/programmer."""
from __future__ import annotations

import json
import logging
import queue
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
        return render_template(
            "admin.html",
            chips=[c.to_dict() for c in registry.all()],
            genres=GENRES,
            actions=ACTION_TYPES,
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
        if not uid:
            abort(400, "uid is required")
        payload = _coerce_payload(data.get("payload"))
        chip = registry.upsert(
            uid=uid,
            label=(data.get("label") or "").strip(),
            genre=(data.get("genre") or "").strip().lower(),
            action_type=(data.get("action_type") or "").strip().lower(),
            payload=payload,
        )
        return jsonify(chip.to_dict()), 201

    @app.delete("/api/chips/<uid>")
    def api_chips_delete(uid: str) -> Any:
        ok = registry.delete(uid.upper())
        if not ok:
            abort(404, "no such chip")
        return ("", 204)

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
