"""MFRC522 NFC reader backend (SPI) using the mfrc522 PyPI package."""
from __future__ import annotations

import logging
from typing import Optional

from .base import NFCReader

log = logging.getLogger(__name__)


class MFRC522Reader(NFCReader):
    def __init__(self, poll_interval: float, rescan_cooldown: float) -> None:
        super().__init__(poll_interval=poll_interval, rescan_cooldown=rescan_cooldown)
        self._reader = None

    def open(self) -> None:
        try:
            from mfrc522 import SimpleMFRC522  # type: ignore
        except ImportError as exc:  # pragma: no cover - hardware-only
            raise RuntimeError(
                "MFRC522 driver requires the 'mfrc522' package + RPi.GPIO."
            ) from exc

        self._reader = SimpleMFRC522()
        log.info("MFRC522 reader initialized")

    def close(self) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore

            GPIO.cleanup()
        except Exception:  # pragma: no cover
            pass

    def _read_uid(self) -> Optional[str]:
        if self._reader is None:
            return None
        # SimpleMFRC522.read_id_no_block returns the integer UID or None.
        try:
            uid_int = self._reader.read_id_no_block()
        except Exception:  # pragma: no cover - hardware glitches
            log.exception("MFRC522 read failed")
            return None
        if not uid_int:
            return None
        return f"{uid_int:X}"
