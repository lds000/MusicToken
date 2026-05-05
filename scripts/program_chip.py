"""Program a chip from the command line.

Example:
  python -m scripts.program_chip --uid 04A2B3C4D5E6F7 \\
         --genre rock --action spotify \\
         --payload '{"uri": "spotify:album:1DFixLWuPkv3KT3TnV35m3"}' \\
         --label "EAGLES / HOTEL CALIFORNIA"
"""
from __future__ import annotations

import json
import sys

import click

# Allow running this file directly without installing the package.
sys.path.insert(0, "src")

from musictoken.config import Config  # noqa: E402
from musictoken.registry import ChipRegistry  # noqa: E402


@click.command()
@click.option("--config", "config_path", default="config/config.yaml")
@click.option("--uid", required=True)
@click.option("--label", default="")
@click.option("--genre", default="")
@click.option("--action", "action_type", required=True)
@click.option("--payload", default="{}")
def main(config_path: str, uid: str, label: str, genre: str,
         action_type: str, payload: str) -> None:
    cfg = Config.load(config_path)
    registry = ChipRegistry(cfg.get("app.database", "config/chips.db"))
    try:
        payload_dict = json.loads(payload) if payload else {}
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"--payload is not valid JSON: {exc}") from exc

    chip = registry.upsert(
        uid=uid.upper(),
        label=label,
        genre=genre.lower(),
        action_type=action_type.lower(),
        payload=payload_dict,
    )
    click.echo(json.dumps(chip.to_dict(), indent=2))


if __name__ == "__main__":
    main()
