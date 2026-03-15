from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from muninn.models.message import Message
from muninn.models.room import Room, RoomType
from muninn.models.task import Task


def _pair_key(a: str, b: str) -> tuple[str, str]:
    """Create a sorted pair key for two agents."""
    return (a, b) if a <= b else (b, a)


class MessageStore:
    def __init__(self) -> None:
        self._all_messages: list[Message] = []
        self._by_recipient: dict[str, list[Message]] = defaultdict(list)
        self._by_pair: dict[tuple[str, str], list[Message]] = defaultdict(list)
        self._file_msg_counts: dict[str, int] = {}
        self._known_agents: set[str] = set()

    @property
    def all_messages(self) -> list[Message]:
        return self._all_messages

    @property
    def known_agents(self) -> set[str]:
        return set(self._known_agents)

    @property
    def total_count(self) -> int:
        return len(self._all_messages)

    def load_inbox_file(self, path: Path) -> list[Message]:
        path_str = str(path)
        recipient = path.stem

        try:
            raw_data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(raw_data, list):
            return []

        prev_count = self._file_msg_counts.get(path_str, 0)

        # Handle truncation: if file has fewer messages than before, full reload
        if len(raw_data) < prev_count:
            self._remove_messages_from_file(path_str)
            prev_count = 0

        new_entries = raw_data[prev_count:]
        if not new_entries:
            return []

        new_messages = []
        for raw in new_entries:
            msg = Message.from_raw(raw, recipient, path_str)
            new_messages.append(msg)
            self._known_agents.add(msg.sender)
            self._known_agents.add(msg.recipient)
            self._by_recipient[recipient].append(msg)
            pair_key = _pair_key(msg.sender, msg.recipient)
            self._by_pair[pair_key].append(msg)

        self._all_messages.extend(new_messages)
        self._all_messages.sort(key=lambda m: m.timestamp)
        self._file_msg_counts[path_str] = len(raw_data)

        return new_messages

    def _remove_messages_from_file(self, path_str: str) -> None:
        self._all_messages = [
            m for m in self._all_messages if m.source_file != path_str
        ]
        # Rebuild indices
        self._by_recipient.clear()
        self._by_pair.clear()
        for msg in self._all_messages:
            self._by_recipient[msg.recipient].append(msg)
            pair_key = _pair_key(msg.sender, msg.recipient)
            self._by_pair[pair_key].append(msg)

    def load_all_inboxes(self, inbox_dir: Path) -> None:
        if not inbox_dir.is_dir():
            return
        for path in sorted(inbox_dir.glob("*.json")):
            self.load_inbox_file(path)
        self.detect_broadcasts()

    def get_messages(self, room: Room) -> list[Message]:
        if room.room_type == RoomType.GENERAL:
            return list(self._all_messages)
        elif room.room_type == RoomType.AGENT:
            msgs = self._by_recipient.get(room.name, [])
            return sorted(msgs, key=lambda m: m.timestamp)
        elif room.room_type == RoomType.PAIR:
            pair_key = _pair_key(room.agents[0], room.agents[1])
            msgs = self._by_pair.get(pair_key, [])
            return sorted(msgs, key=lambda m: m.timestamp)
        return []

    def discover_rooms(self) -> list[Room]:
        rooms: list[Room] = []

        # #general
        rooms.append(
            Room(
                room_type=RoomType.GENERAL,
                name="general",
                agents=tuple(sorted(self._known_agents)),
                unread_count=sum(1 for m in self._all_messages if not m.read),
            )
        )

        # @agent rooms
        for agent in sorted(self._known_agents):
            msgs = self._by_recipient.get(agent, [])
            if msgs:
                rooms.append(
                    Room(
                        room_type=RoomType.AGENT,
                        name=agent,
                        agents=(agent,),
                        unread_count=sum(1 for m in msgs if not m.read),
                    )
                )

        # Pair rooms (only pairs with 2+ messages)
        pair_counts = []
        for pair_key, msgs in self._by_pair.items():
            if len(msgs) >= 2:
                pair_counts.append((pair_key, len(msgs)))
        pair_counts.sort(key=lambda x: -x[1])

        for pair_key, _ in pair_counts:
            msgs = self._by_pair[pair_key]
            rooms.append(
                Room(
                    room_type=RoomType.PAIR,
                    name=f"{pair_key[0]}↔{pair_key[1]}",
                    agents=pair_key,
                    unread_count=sum(1 for m in msgs if not m.read),
                )
            )

        return rooms

    def detect_broadcasts(self) -> None:
        # Group by (sender, timestamp_iso) — same message sent to multiple recipients
        sig_map: dict[tuple[str, str], list[int]] = defaultdict(list)
        for idx, msg in enumerate(self._all_messages):
            sig = (msg.sender, msg.timestamp.isoformat())
            sig_map[sig].append(idx)

        for sig, indices in sig_map.items():
            if len(indices) >= 2:
                # Check that text content is identical
                texts = {self._all_messages[i].text for i in indices}
                if len(texts) == 1:
                    for i in indices:
                        old = self._all_messages[i]
                        self._all_messages[i] = Message(
                            sender=old.sender,
                            recipient=old.recipient,
                            text=old.text,
                            timestamp=old.timestamp,
                            read=old.read,
                            color=old.color,
                            summary=old.summary,
                            structured=old.structured,
                            is_broadcast=True,
                            source_file=old.source_file,
                        )

    def extract_tasks(self) -> list[Task]:
        tasks: list[Task] = []
        seen_ids: set[str] = set()
        for msg in self._all_messages:
            if msg.structured and msg.structured.type == "task_assignment":
                task_id = msg.structured.data.get("taskId", "")
                if task_id and task_id not in seen_ids:
                    seen_ids.add(task_id)
                    tasks.append(
                        Task(
                            id=task_id,
                            subject=msg.structured.data.get("subject", ""),
                            description=msg.structured.data.get("description", ""),
                            status="assigned",
                            assigned_by=msg.structured.data.get(
                                "assignedBy", msg.sender
                            ),
                        )
                    )
        return tasks
