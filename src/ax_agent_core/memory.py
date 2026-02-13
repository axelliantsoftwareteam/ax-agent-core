from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Dict, List, Optional, Protocol


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationMemory(Protocol):
    def append(self, session_id: str, message: Message) -> None:
        ...

    def history(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        ...

    def clear(self, session_id: str) -> None:
        ...


class InMemoryConversationStore:
    """Simple in-memory conversation state for single-process runtime usage."""

    def __init__(self) -> None:
        self._messages: Dict[str, List[Message]] = {}
        self._lock = RLock()

    def append(self, session_id: str, message: Message) -> None:
        with self._lock:
            self._messages.setdefault(session_id, []).append(message)

    def history(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        with self._lock:
            events = list(self._messages.get(session_id, []))
        if limit is None or limit <= 0:
            return events
        return events[-limit:]

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._messages.pop(session_id, None)
