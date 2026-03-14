from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message as TextualMessage
from textual.widgets import ListView, ListItem, Static

from typing import Any

from muninn.models.room import Room


class RoomSelected(TextualMessage):
    def __init__(self, room: Room) -> None:
        super().__init__()
        self.room = room


class RoomSidebar(Static):
    """Sidebar showing available rooms."""

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
    """

    def __init__(self, rooms: list[Room], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._rooms = rooms

    def compose(self) -> ComposeResult:
        yield ListView(id="room-list")

    def on_mount(self) -> None:
        self._populate_list()

    def _populate_list(self) -> None:
        lv = self.query_one("#room-list", ListView)
        lv.clear()
        for room in self._rooms:
            badge = f" ({room.unread_count})" if room.unread_count > 0 else ""
            label = f"{room.display_name}{badge}"
            lv.append(ListItem(Static(label, classes="room-item")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._rooms):
            self.post_message(RoomSelected(self._rooms[idx]))

    def update_rooms(self, rooms: list[Room]) -> None:
        self._rooms = rooms
        self._populate_list()
