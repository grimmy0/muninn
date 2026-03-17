from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RoomType(Enum):
    GENERAL = "general"
    PAIR = "pair"


def _truncate(name: str, max_len: int = 10) -> str:
    return name if len(name) <= max_len else name[: max_len - 1] + "…"


@dataclass
class Room:
    room_type: RoomType
    name: str
    agents: tuple[str, ...]
    unread_count: int = 0
    protocol_heavy: bool = False

    @property
    def display_name(self) -> str:
        if self.room_type == RoomType.GENERAL:
            return "#general"
        else:
            return f"{_truncate(self.agents[0])}↔{_truncate(self.agents[1])}"

    def matches_message(self, sender: str, recipient: str) -> bool:
        if self.room_type == RoomType.GENERAL:
            return True
        elif self.room_type == RoomType.PAIR:
            pair = tuple(sorted((sender, recipient)))
            return pair == tuple(sorted(self.agents))
        return False
