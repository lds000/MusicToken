"""Ask the configured AI provider for chip suggestions from the CLI.

Example:
  python -m scripts.suggest_chips --prompt "late-night driving music" --count 8
"""
from __future__ import annotations

import json
import sys

import click

sys.path.insert(0, "src")

from musictoken.ai import build_provider  # noqa: E402
from musictoken.ai.suggester import Suggester  # noqa: E402
from musictoken.config import Config  # noqa: E402
from musictoken.registry import ChipRegistry  # noqa: E402


@click.command()
@click.option("--config", "config_path", default="config/config.yaml")
@click.option("--prompt", required=True)
@click.option("--count", type=int, default=6)
def main(config_path: str, prompt: str, count: int) -> None:
    cfg = Config.load(config_path)
    registry = ChipRegistry(cfg.get("app.database", "config/chips.db"))
    provider = build_provider(cfg.section("ai"))
    suggester = Suggester(provider, registry)
    out = suggester.suggest_chips(prompt, count=count)
    click.echo(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
