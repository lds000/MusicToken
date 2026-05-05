"""Mock NFC reader for development without hardware."""
from __future__ import annotations

from typing import Optional

from .base import NFCReader


class MockReader(NFCReader):
    """No-op reader. Scans only happen via :meth:`inject`.

    Used by the dev/Windows path and by the admin UI's "Simulate scan"
    button.
    """

    def _read_uid(self) -> Optional[str]:
        return None
