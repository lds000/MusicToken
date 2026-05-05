"""Tiny pub/sub event bus.

Used by the NFC reader, action runner, and Flask UI to broadcast state
changes (now-playing, last-scan, etc.) without coupling the components.
"""
from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Event:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class EventBus:
    """Threadsafe fan-out bus. Each subscriber gets its own queue."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: List[queue.Queue[Event]] = []
        self._last: Dict[str, Event] = {}

    def publish(self, type_: str, payload: Optional[Dict[str, Any]] = None) -> Event:
        evt = Event(type=type_, payload=payload or {})
        with self._lock:
            self._last[type_] = evt
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(evt)
            except queue.Full:
                pass
        return evt

    def subscribe(self) -> "queue.Queue[Event]":
        q: queue.Queue[Event] = queue.Queue(maxsize=128)
        with self._lock:
            self._subscribers.append(q)
            # Replay last-known state so a fresh subscriber sees current
            # now-playing, last-scan, etc.
            for evt in self._last.values():
                try:
                    q.put_nowait(evt)
                except queue.Full:
                    pass
        return q

    def unsubscribe(self, q: "queue.Queue[Event]") -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def last(self, type_: str) -> Optional[Event]:
        with self._lock:
            return self._last.get(type_)
