"""List all programmed chips."""
from __future__ import annotations

import json
import sys

import click

sys.path.insert(0, "src")

from musictoken.config import Config  # noqa: E402
from musictoken.registry import ChipRegistry  # noqa: E402


@click.command()
@click.option("--config", "config_path", default="config/config.yaml")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of a table.")
def main(config_path: str, as_json: bool) -> None:
    cfg = Config.load(config_path)
    registry = ChipRegistry(cfg.get("app.database", "config/chips.db"))
    chips = registry.all()
    if as_json:
        click.echo(json.dumps([c.to_dict() for c in chips], indent=2))
        return
    if not chips:
        click.echo("(no chips yet — program one in the admin UI or via program_chip.py)")
        return
    click.echo(f"{'UID':<18}{'GENRE':<10}{'ACTION':<10}LABEL")
    click.echo("-" * 60)
    for c in chips:
        click.echo(f"{c.uid:<18}{c.genre:<10}{c.action_type:<10}{c.label}")


if __name__ == "__main__":
    main()
