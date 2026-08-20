from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from pathlib import Path

from muninn.models.message import Message
from muninn.models.room import Room, RoomType
from muninn.models.task import Task

logger = logging.getLogger(__name__)

_PROTOCOL_TYPES = frozenset(
    {
        "idle_notification",
        "shutdown_request",
        "shutdown_approved",
        "permission_request",
        "permission_response",
        "task_assignment",
    }
)


def _pair_key(a: str, b: str) -> tuple[str, str]:
    """Create a sorted pair key for two agents."""
    return (a, b) if a <= b else (b, a)


def _is_protocol_only(msgs: list[Message]) -> bool:
    return all(m.structured and m.structured.type in _PROTOCOL_TYPES for m in msgs)


class MessageStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._all_messages: list[Message] = []
        self._by_pair: dict[tuple[str, str], list[Message]] = defaultdict(list)
        self._file_msg_counts: dict[str, int] = {}
        self._known_agents: set[str] = set()
        self._dirty = False

    def _ensure_clean(self) -> None:
        with self._lock:
            if self._dirty:
                self._all_messages.sort(key=lambda m: m.timestamp)
                self.detect_broadcasts()
                self._rebuild_pair_index()
                self._dirty = False

    @property
    def all_messages(self) -> list[Message]:
        with self._lock:
            self._ensure_clean()
            return self._all_messages

    @property
    def known_agents(self) -> set[str]:
        with self._lock:
            return set(self._known_agents)

    @property
    def total_count(self) -> int:
        with self._lock:
            return len(self._all_messages)

    def load_inbox_file(self, path: Path, *, _defer_clean: bool = False) -> list[Message]:
        with self._lock:
            if path.is_symlink():
                return []
            path_str = str(path)
            recipient = path.stem

            try:
                raw_data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load/parse inbox file %s: %s", path, e, exc_info=True)
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
                if not isinstance(raw, dict):
                    continue
                msg = Message.from_raw(raw, recipient, path_str)
                new_messages.append(msg)
                self._known_agents.add(msg.sender)
                self._known_agents.add(msg.recipient)

            self._all_messages.extend(new_messages)
            self._file_msg_counts[path_str] = len(raw_data)
            self._dirty = True

            if _defer_clean:
                return []

            self._ensure_clean()

            # Find and return the updated message instances with correct is_broadcast state
            updated_messages = []
            for msg in new_messages:
                for m in self._all_messages:
                    if (m.source_file == msg.source_file and 
                        m.sender == msg.sender and 
                        m.recipient == msg.recipient and 
                        m.timestamp == msg.timestamp and 
                        m.text == msg.text):
                        updated_messages.append(m)
                        break
            return updated_messages

    def _remove_messages_from_file(self, path_str: str) -> None:
        with self._lock:
            self._all_messages = [
                m for m in self._all_messages if m.source_file != path_str
            ]
            self._dirty = True

    def _rebuild_pair_index(self) -> None:
        with self._lock:
            self._by_pair.clear()
            for msg in self._all_messages:
                pair_key = _pair_key(msg.sender, msg.recipient)
                self._by_pair[pair_key].append(msg)

    def load_all_inboxes(self, inbox_dir: Path) -> None:
        with self._lock:
            if inbox_dir.is_symlink() or not inbox_dir.is_dir():
                return
            for path in sorted(inbox_dir.glob("*.json")):
                if path.is_symlink():
                    continue
                self.load_inbox_file(path, _defer_clean=True)
            self._dirty = True

    def get_messages(self, room: Room) -> list[Message]:
        with self._lock:
            self._ensure_clean()
            if room.room_type == RoomType.GENERAL:
                return list(self._all_messages)
            elif room.room_type == RoomType.PAIR:
                pair_key = _pair_key(room.agents[0], room.agents[1])
                msgs = self._by_pair.get(pair_key, [])
                return list(msgs)
            return []

    def get_messages_for_agent(self, agent_name: str) -> list[Message]:
        """Return all messages sent by or addressed to agent_name."""
        target = agent_name.lower()
        with self._lock:
            self._ensure_clean()
            return [
                m
                for m in self._all_messages
                if m.sender == target or m.recipient == target
            ]

    def discover_rooms(self, *, filter_protocol: bool = False) -> list[Room]:
        with self._lock:
            self._ensure_clean()
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

            # Pair rooms (threshold: at least 1 message)
            pair_counts = []
            for pair_key, msgs in self._by_pair.items():
                if msgs:
                    pair_counts.append((pair_key, len(msgs)))
            pair_counts.sort(key=lambda x: -x[1])

            for pair_key, _ in pair_counts:
                msgs = self._by_pair[pair_key]

                if filter_protocol and _is_protocol_only(msgs):
                    continue

                total = len(msgs)
                structured_count = sum(
                    1
                    for m in msgs
                    if m.structured and m.structured.type in _PROTOCOL_TYPES
                )
                protocol_heavy = total > 0 and (structured_count / total) > 0.8

                rooms.append(
                    Room(
                        room_type=RoomType.PAIR,
                        name=f"{pair_key[0]}↔{pair_key[1]}",
                        agents=pair_key,
                        unread_count=sum(
                            1 for m in msgs if not m.read and not m.is_broadcast
                        ),
                        protocol_heavy=protocol_heavy,
                    )
                )

            return rooms

    def detect_broadcasts(self) -> None:
        with self._lock:
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
        with self._lock:
            self._ensure_clean()
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

    def mark_read(self, message: Message, read: bool = True) -> Message | None:
        with self._lock:
            for idx, m in enumerate(self._all_messages):
                if (
                    m.source_file == message.source_file
                    and m.sender == message.sender
                    and m.recipient == message.recipient
                    and m.timestamp == message.timestamp
                    and m.text == message.text
                ):
                    updated = Message(
                        sender=m.sender,
                        recipient=m.recipient,
                        text=m.text,
                        timestamp=m.timestamp,
                        read=read,
                        color=m.color,
                        summary=m.summary,
                        structured=m.structured,
                        is_broadcast=m.is_broadcast,
                        source_file=m.source_file,
                    )
                    self._all_messages[idx] = updated
                    self._dirty = True
                    self._ensure_clean()
                    return updated
            return None
