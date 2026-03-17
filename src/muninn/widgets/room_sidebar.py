from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message as TextualMessage
from textual.widgets import Static, Tree

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
    RoomSidebar Tree {
        height: 1fr;
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

    def compose(self) -> ComposeResult:
        tree: Tree[Room] = Tree("Rooms", id="room-tree")
        tree.show_root = False
        tree.show_guides = False
        tree.guide_depth = 3
        yield tree

    def on_mount(self) -> None:
        self._populate_tree()

    def _involves_lead(self, room: Room) -> bool:
        if not self._lead_agent_id:
            return False
        if room.room_type == RoomType.PAIR:
            return self._lead_agent_id in room.agents
        return False

    def _categorize_rooms(
        self,
    ) -> tuple[Room | None, list[tuple[str, list[Room]]]]:
        """Returns (#general room or None, [(section_name, rooms)])."""
        general: Room | None = None
        groups: dict[str, list[Room]] = {
            "TEAM LEAD": [],
            "CONVERSATIONS": [],
        }
        for room in self._rooms:
            if room.room_type == RoomType.GENERAL:
                general = room
            elif self._lead_agent_id and self._involves_lead(room):
                groups["TEAM LEAD"].append(room)
            else:
                groups["CONVERSATIONS"].append(room)
        sections = [(k, v) for k, v in groups.items() if v]
        return general, sections

    def _populate_tree(self) -> None:
        tree = self.query_one("#room-tree", Tree)
        tree.clear()

        general, sections = self._categorize_rooms()

        # Add #general as standalone leaf at root
        if general:
            badge = (
                f" ({general.unread_count})" if general.unread_count > 0 else ""
            )
            tree.root.add_leaf(f"{general.display_name}{badge}", data=general)

        for section_name, section_rooms in sections:
            section_node = tree.root.add(
                f"[dim bold]{section_name}[/]", expand=True
            )
            for room in section_rooms:
                badge = (
                    f" ({room.unread_count})" if room.unread_count > 0 else ""
                )
                display = room.display_name
                if room.protocol_heavy:
                    label = f"[dim]{display}{badge}[/]"
                else:
                    label = f"{display}{badge}"
                section_node.add_leaf(label, data=room)

    def on_tree_node_selected(self, event: Tree.NodeSelected[Room]) -> None:
        if event.node.data is not None:
            self.post_message(RoomSelected(event.node.data))

    def update_rooms(self, rooms: list[Room]) -> None:
        self._rooms = rooms
        self._populate_tree()
