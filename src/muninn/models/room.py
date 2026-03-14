from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RoomType(Enum):
    GENERAL = "general"
    AGENT = "agent"
    PAIR = "pair"


@dataclass
class Room:
    room_type: RoomType
    name: str
    agents: tuple[str, ...]
    unread_count: int = 0

    @property
    def display_name(self) -> str:
        if self.room_type == RoomType.GENERAL:
            return "#general"
        elif self.room_type == RoomType.AGENT:
            return f"@{self.name}"
        else:
            return f"{'↔'.join(self.agents)}"

    def matches_message(self, sender: str, recipient: str) -> bool:
        if self.room_type == RoomType.GENERAL:
            return True
        elif self.room_type == RoomType.AGENT:
            return recipient == self.name
        elif self.room_type == RoomType.PAIR:
            pair = tuple(sorted((sender, recipient)))
            return pair == tuple(sorted(self.agents))
        return False
