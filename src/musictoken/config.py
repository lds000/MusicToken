"""Configuration loader.

Reads a YAML config and exposes it as a nested dict with helpful accessors.
Falls back to sensible defaults when keys are missing so the app can boot
even with a stub config file.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml

log = logging.getLogger(__name__)

DEFAULTS: Dict[str, Any] = {
    "app": {
        "host": "0.0.0.0",
        "port": 8080,
        "log_level": "INFO",
        "database": "config/chips.db",
    },
    "nfc": {
        "backend": "mock",
        "poll_interval": 0.25,
        "rescan_cooldown": 1.5,
    },
    "player": {
        "backend": "mock",
    },
    "ai": {
        "backend": "mock",
    },
    "commands": {},
}


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, val in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


class Config:
    """Wrapper around a config dict with dotted-path lookup."""

    def __init__(self, data: Dict[str, Any], source: Path | None = None) -> None:
        self._data = data
        self.source = source

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "Config":
        p = Path(path)
        if not p.exists():
            log.warning("Config file %s not found, using defaults.", p)
            return cls(dict(DEFAULTS), p)
        with p.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        merged = _deep_merge(DEFAULTS, raw)
        return cls(merged, p)

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def section(self, name: str) -> Dict[str, Any]:
        val = self._data.get(name, {})
        return val if isinstance(val, dict) else {}

    @property
    def raw(self) -> Dict[str, Any]:
        return self._data
