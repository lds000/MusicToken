"""NFC reader abstraction.

The system is intentionally hardware-agnostic: the rest of the app talks
to :class:`NFCReader` and never imports a vendor library directly. The
concrete driver is selected at runtime by ``config.nfc.backend``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import NFCReader, ScanCallback
from .mock import MockReader

log = logging.getLogger(__name__)


def build_reader(cfg: Dict[str, Any]) -> NFCReader:
    backend = (cfg.get("backend") or "mock").lower()
    poll = float(cfg.get("poll_interval", 0.25))
    cooldown = float(cfg.get("rescan_cooldown", 1.5))

    if backend == "mock":
        return MockReader(poll_interval=poll, rescan_cooldown=cooldown)

    if backend == "pn532_i2c":
        from .pn532 import PN532I2CReader

        opts = cfg.get("pn532_i2c", {}) or {}
        return PN532I2CReader(
            poll_interval=poll,
            rescan_cooldown=cooldown,
            bus=int(opts.get("bus", 1)),
            address=int(opts.get("address", 0x24)),
        )

    if backend == "pn532_spi":
        from .pn532 import PN532SPIReader

        opts = cfg.get("pn532_spi", {}) or {}
        return PN532SPIReader(
            poll_interval=poll,
            rescan_cooldown=cooldown,
            cs_pin=str(opts.get("cs_pin", "D8")),
        )

    if backend == "mfrc522_spi":
        from .mfrc522_backend import MFRC522Reader

        return MFRC522Reader(poll_interval=poll, rescan_cooldown=cooldown)

    log.warning("Unknown NFC backend %r — falling back to mock.", backend)
    return MockReader(poll_interval=poll, rescan_cooldown=cooldown)


__all__ = ["NFCReader", "ScanCallback", "MockReader", "build_reader"]
