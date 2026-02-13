from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Protocol


@dataclass
class Message:
    role: str
    content: str


class ConversationStore(Protocol):
    def append(self, session_id: str, message: Message) -> None:
        ...

    def history(self, session_id: str) -> List[Message]:
        ...

    def clear(self, session_id: str) -> None:
        ...


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._store: Dict[str, List[Message]] = {}

    def append(self, session_id: str, message: Message) -> None:
        self._store.setdefault(session_id, []).append(message)

    def history(self, session_id: str) -> List[Message]:
        return list(self._store.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)
