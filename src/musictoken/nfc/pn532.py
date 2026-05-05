"""PN532 NFC reader backends (I²C and SPI) using Adafruit CircuitPython.

These imports are lazy: importing this module on a non-Pi system without
the libraries installed should still raise a clear error pointing at
``requirements-pi.txt``.
"""
from __future__ import annotations

import logging
from typing import Optional

from .base import NFCReader

log = logging.getLogger(__name__)


def _format_uid(raw: bytes | bytearray | list[int] | None) -> Optional[str]:
    if not raw:
        return None
    return "".join(f"{b:02X}" for b in raw)


class PN532I2CReader(NFCReader):
    def __init__(
        self,
        poll_interval: float,
        rescan_cooldown: float,
        bus: int = 1,
        address: int = 0x24,
    ) -> None:
        super().__init__(poll_interval=poll_interval, rescan_cooldown=rescan_cooldown)
        self.bus = bus
        self.address = address
        self._pn532 = None

    def open(self) -> None:
        try:
            import board  # type: ignore
            import busio  # type: ignore
            from adafruit_pn532.i2c import PN532_I2C  # type: ignore
        except ImportError as exc:  # pragma: no cover - hardware-only
            raise RuntimeError(
                "PN532 I2C driver requires adafruit-circuitpython-pn532 + "
                "adafruit-blinka. Install requirements-pi.txt on the Pi."
            ) from exc

        i2c = busio.I2C(board.SCL, board.SDA)
        self._pn532 = PN532_I2C(i2c, address=self.address, debug=False)
        self._pn532.SAM_configuration()
        log.info("PN532 (I2C) firmware: %s", self._pn532.firmware_version)

    def _read_uid(self) -> Optional[str]:
        if self._pn532 is None:
            return None
        uid = self._pn532.read_passive_target(timeout=0.1)
        return _format_uid(uid)


class PN532SPIReader(NFCReader):
    def __init__(
        self,
        poll_interval: float,
        rescan_cooldown: float,
        cs_pin: str = "D8",
    ) -> None:
        super().__init__(poll_interval=poll_interval, rescan_cooldown=rescan_cooldown)
        self.cs_pin_name = cs_pin
        self._pn532 = None

    def open(self) -> None:
        try:
            import board  # type: ignore
            import busio  # type: ignore
            from digitalio import DigitalInOut  # type: ignore
            from adafruit_pn532.spi import PN532_SPI  # type: ignore
        except ImportError as exc:  # pragma: no cover - hardware-only
            raise RuntimeError(
                "PN532 SPI driver requires adafruit-circuitpython-pn532 + "
                "adafruit-blinka. Install requirements-pi.txt on the Pi."
            ) from exc

        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        cs = DigitalInOut(getattr(board, self.cs_pin_name))
        self._pn532 = PN532_SPI(spi, cs, debug=False)
        self._pn532.SAM_configuration()
        log.info("PN532 (SPI) firmware: %s", self._pn532.firmware_version)

    def _read_uid(self) -> Optional[str]:
        if self._pn532 is None:
            return None
        uid = self._pn532.read_passive_target(timeout=0.1)
        return _format_uid(uid)
