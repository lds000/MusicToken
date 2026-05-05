"""MusicToken entry point.

Usage:
  python -m musictoken --config config/config.yaml

Wires together:
  config -> registry -> NFC reader -> action runner -> player
                                                     \\-> Flask UI (kiosk)
                                                     \\-> AI suggester
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
from typing import Any

from .actions import ActionRunner
from .ai import build_provider
from .ai.suggester import Suggester
from .config import Config
from .events import EventBus
from .nfc import build_reader
from .players import build_player
from .registry import ChipRegistry
from .ui.app import create_app

log = logging.getLogger("musictoken")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="musictoken")
    p.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to config YAML (default: config/config.yaml)",
    )
    p.add_argument("--host", default=None, help="Override app.host")
    p.add_argument("--port", type=int, default=None, help="Override app.port")
    return p.parse_args(argv)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _load_dotenv() -> None:
    """Load env vars from a local .env file if python-dotenv is installed.

    Keeps secrets like OPENAI_API_KEY out of the YAML config and out of
    git (the .env file is gitignored).
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        return
    load_dotenv()


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    args = parse_args(argv)
    cfg = Config.load(args.config)
    configure_logging(cfg.get("app.log_level", "INFO"))

    log.info("MusicToken starting (config: %s)", cfg.source)

    bus = EventBus()
    registry = ChipRegistry(cfg.get("app.database", "config/chips.db"))
    player = build_player(cfg.section("player"))

    ai_provider = build_provider(cfg.section("ai"))
    suggester = Suggester(ai_provider, registry)

    runner = ActionRunner(
        registry=registry,
        player=player,
        bus=bus,
        commands_cfg=cfg.section("commands"),
        suggester=suggester,
    )

    reader = build_reader(cfg.section("nfc"))
    reader.on_scan(runner.handle_scan)

    app = create_app(
        registry=registry,
        runner=runner,
        reader=reader,
        player=player,
        bus=bus,
        suggester=suggester,
        openscad_path=cfg.get("printing.openscad_path"),
    )

    host = args.host or cfg.get("app.host", "0.0.0.0")
    port = int(args.port or cfg.get("app.port", 8080))

    reader.start()

    def _shutdown(*_: Any) -> None:
        log.info("Shutting down…")
        try:
            reader.stop()
        finally:
            try:
                player.close()
            except Exception:
                log.exception("Error closing player")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    log.info("UI listening on http://%s:%d", host, port)
    # threaded=True so SSE doesn't block other requests; debug=False so the
    # reloader doesn't spawn the NFC reader twice.
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
    _shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
