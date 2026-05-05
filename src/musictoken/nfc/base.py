"""Base NFC reader class.

Concrete drivers subclass :class:`NFCReader` and implement
:meth:`_read_uid`. The base class handles the polling thread, debounce,
and callback dispatch.
"""
from __future__ import annotations

import abc
import logging
import threading
import time
from typing import Callable, Optional

log = logging.getLogger(__name__)

ScanCallback = Callable[[str], None]


class NFCReader(abc.ABC):
    """Abstract NFC reader. Spawns a background polling thread."""

    def __init__(self, poll_interval: float = 0.25, rescan_cooldown: float = 1.5) -> None:
        self.poll_interval = poll_interval
        self.rescan_cooldown = rescan_cooldown
        self._callback: Optional[ScanCallback] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._last_uid: Optional[str] = None
        self._last_uid_at: float = 0.0

    @abc.abstractmethod
    def _read_uid(self) -> Optional[str]:
        """Return the UID of the tag currently on the reader, or None."""

    def open(self) -> None:
        """Hook for one-time hardware init. Default: no-op."""

    def close(self) -> None:
        """Hook for hardware teardown. Default: no-op."""

    def on_scan(self, cb: ScanCallback) -> None:
        self._callback = cb

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.open()
        self._thread = threading.Thread(target=self._run, name="nfc-reader", daemon=True)
        self._thread.start()
        log.info("NFC reader started (%s)", type(self).__name__)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        try:
            self.close()
        except Exception:  # pragma: no cover - cleanup best-effort
            log.exception("Error closing NFC reader")
        log.info("NFC reader stopped")

    # ------------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                uid = self._read_uid()
            except Exception:  # pragma: no cover - hardware glitches
                log.exception("NFC read failed")
                uid = None
            if uid:
                self._handle_uid(uid)
            else:
                # Tag lifted — reset so re-tap of the same chip fires again.
                if self._last_uid is not None and (
                    time.time() - self._last_uid_at > self.rescan_cooldown
                ):
                    self._last_uid = None
            self._stop.wait(self.poll_interval)

    def _handle_uid(self, uid: str) -> None:
        now = time.time()
        if uid == self._last_uid and (now - self._last_uid_at) < self.rescan_cooldown:
            self._last_uid_at = now
            return
        self._last_uid = uid
        self._last_uid_at = now
        log.info("NFC scan: %s", uid)
        if self._callback:
            try:
                self._callback(uid)
            except Exception:
                log.exception("Scan callback failed for uid=%s", uid)

    # Public helper used by the admin UI's "simulate scan" feature.
    def inject(self, uid: str) -> None:
        """Pretend a tag with this UID was scanned. Bypasses hardware."""
        self._handle_uid(uid)
