from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message as TextualMessage
from textual.widgets import ListView, ListItem, Static

from typing import Any

from muninn.models.room import Room, RoomType


class RoomSelected(TextualMessage):
    def __init__(self, room: Room) -> None:
        super().__init__()
        self.room = room


class RoomSidebar(Static):
    """Sidebar showing available rooms grouped by category."""

    DEFAULT_CSS = """
    RoomSidebar {
        width: 28;
        dock: left;
        border-right: solid $accent;
        height: 1fr;
    }
    RoomSidebar ListView {
        height: 1fr;
    }
    RoomSidebar .room-item {
        padding: 0 1;
    }
    RoomSidebar .section-header {
        padding: 0 1;
        color: $text-muted;
        text-style: bold;
    }
    """

    def __init__(
        self,
        rooms: list[Room],
        lead_agent_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._rooms = rooms
        self._lead_agent_id = lead_agent_id
        self._index_to_room: dict[int, Room] = {}

    def compose(self) -> ComposeResult:
        yield ListView(id="room-list")

    def on_mount(self) -> None:
        self._populate_list()

    def _involves_lead(self, room: Room) -> bool:
        if not self._lead_agent_id:
            return False
        if room.room_type == RoomType.AGENT:
            return room.name == self._lead_agent_id
        if room.room_type == RoomType.PAIR:
            return self._lead_agent_id in room.agents
        return False

    def _categorize_rooms(self) -> list[tuple[str, list[Room]]]:
        groups: dict[str, list[Room]] = {
            "TEAM LEAD": [],
            "GROUP": [],
            "DIRECT": [],
        }
        for room in self._rooms:
            if room.room_type == RoomType.GENERAL:
                groups["GROUP"].append(room)
            elif self._lead_agent_id and self._involves_lead(room):
                groups["TEAM LEAD"].append(room)
            else:
                groups["DIRECT"].append(room)
        return [(k, v) for k, v in groups.items() if v]

    def _populate_list(self) -> None:
        lv = self.query_one("#room-list", ListView)
        lv.clear()
        self._index_to_room.clear()

        sections = self._categorize_rooms()
        idx = 0
        for section_name, section_rooms in sections:
            header = ListItem(
                Static(f"  {section_name}", classes="section-header"),
            )
            header.disabled = True
            lv.append(header)
            idx += 1
            for room in section_rooms:
                badge = f" ({room.unread_count})" if room.unread_count > 0 else ""
                label = f"{room.display_name}{badge}"
                self._index_to_room[idx] = room
                lv.append(ListItem(Static(label, classes="room-item")))
                idx += 1

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and idx in self._index_to_room:
            self.post_message(RoomSelected(self._index_to_room[idx]))

    def update_rooms(self, rooms: list[Room]) -> None:
        self._rooms = rooms
        self._populate_list()
