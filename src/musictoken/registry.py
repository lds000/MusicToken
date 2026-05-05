"""SQLite-backed chip registry.

A 'chip' is the physical NFC token. Each row stores the tag UID plus the
action that should be run when it is scanned.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS chips (
    uid           TEXT PRIMARY KEY,
    label         TEXT NOT NULL DEFAULT '',
    genre         TEXT NOT NULL DEFAULT '',
    action_type   TEXT NOT NULL,
    payload_json  TEXT NOT NULL DEFAULT '{}',
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL,
    last_seen_at  REAL,
    scan_count    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_chips_genre ON chips(genre);
CREATE INDEX IF NOT EXISTS idx_chips_action ON chips(action_type);
"""


@dataclass
class Chip:
    uid: str
    label: str = ""
    genre: str = ""
    action_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0
    last_seen_at: Optional[float] = None
    scan_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "label": self.label,
            "genre": self.genre,
            "action_type": self.action_type,
            "payload": self.payload,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_seen_at": self.last_seen_at,
            "scan_count": self.scan_count,
        }


class ChipRegistry:
    """Threadsafe wrapper around the SQLite chip table."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_chip(row: sqlite3.Row) -> Chip:
        try:
            payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
        except json.JSONDecodeError:
            payload = {}
        return Chip(
            uid=row["uid"],
            label=row["label"] or "",
            genre=row["genre"] or "",
            action_type=row["action_type"] or "",
            payload=payload,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_seen_at=row["last_seen_at"],
            scan_count=row["scan_count"],
        )

    def upsert(
        self,
        uid: str,
        *,
        label: str = "",
        genre: str = "",
        action_type: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Chip:
        now = time.time()
        payload_json = json.dumps(payload or {})
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT created_at FROM chips WHERE uid = ?", (uid,)
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO chips (uid, label, genre, action_type, payload_json,
                                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(uid) DO UPDATE SET
                    label = excluded.label,
                    genre = excluded.genre,
                    action_type = excluded.action_type,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (uid, label, genre, action_type, payload_json, created_at, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM chips WHERE uid = ?", (uid,)).fetchone()
        return self._row_to_chip(row)

    def delete(self, uid: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM chips WHERE uid = ?", (uid,))
            conn.commit()
            return cur.rowcount > 0

    def get(self, uid: str) -> Optional[Chip]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM chips WHERE uid = ?", (uid,)).fetchone()
        return self._row_to_chip(row) if row else None

    def all(self) -> List[Chip]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chips ORDER BY genre, label, uid"
            ).fetchall()
        return [self._row_to_chip(r) for r in rows]

    def by_genre(self, genre: str) -> List[Chip]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chips WHERE genre = ? ORDER BY label, uid",
                (genre,),
            ).fetchall()
        return [self._row_to_chip(r) for r in rows]

    def mark_scanned(self, uid: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE chips
                   SET last_seen_at = ?,
                       scan_count = scan_count + 1
                 WHERE uid = ?
                """,
                (time.time(), uid),
            )
            conn.commit()
