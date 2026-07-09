import json

from muninn.models.room import RoomType
from muninn.services.message_store import MessageStore


class TestMessageStore:
    def test_load_all_inboxes(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        assert store.total_count == 10

    def test_known_agents(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        agents = store.known_agents
        assert len(agents) >= 3
        assert "team-lead" in agents
        assert "analyst" in agents
        assert "researcher" in agents

    def test_discover_rooms(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms()

        # Should have #general
        general = [r for r in rooms if r.room_type == RoomType.GENERAL]
        assert len(general) == 1

        # Should have pair rooms (all 3 pairs, since filter_protocol defaults to False)
        pair_rooms = [r for r in rooms if r.room_type == RoomType.PAIR]
        assert len(pair_rooms) == 3

    def test_protocol_only_rooms_filtered(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms(filter_protocol=True)

        pair_rooms = [r for r in rooms if r.room_type == RoomType.PAIR]
        # analyst↔team-lead is protocol-only, should be filtered
        pair_names = {r.name for r in pair_rooms}
        assert "analyst↔team-lead" not in pair_names
        assert len(pair_rooms) == 2

    def test_mixed_rooms_kept(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms(filter_protocol=True)

        pair_rooms = [r for r in rooms if r.room_type == RoomType.PAIR]
        pair_names = {r.name for r in pair_rooms}
        assert "analyst↔researcher" in pair_names
        assert "researcher↔team-lead" in pair_names

    def test_pair_threshold_one(self, tmp_path):
        inbox_dir = tmp_path / "inboxes"
        inbox_dir.mkdir()
        (inbox_dir / "bob.json").write_text(
            json.dumps(
                [
                    {
                        "from": "alice",
                        "text": "Hello",
                        "timestamp": "2026-01-01T00:00:00Z",
                        "read": False,
                    }
                ]
            )
        )
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms()

        pair_rooms = [r for r in rooms if r.room_type == RoomType.PAIR]
        assert len(pair_rooms) == 1
        assert "alice" in pair_rooms[0].agents
        assert "bob" in pair_rooms[0].agents

    def test_case_insensitive_duplicate_agents(self, tmp_path):
        inbox_dir = tmp_path / "inboxes"
        inbox_dir.mkdir()
        # Message 1: alice to bob
        (inbox_dir / "bob.json").write_text(
            json.dumps(
                [
                    {
                        "from": "alice",
                        "text": "Hello",
                        "timestamp": "2026-01-01T00:00:00Z",
                        "read": False,
                    }
                ]
            )
        )
        # Message 2: Bob to Alice (mixed case)
        (inbox_dir / "Alice.json").write_text(
            json.dumps(
                [
                    {
                        "from": "Bob",
                        "text": "Hi",
                        "timestamp": "2026-01-01T00:00:01Z",
                        "read": False,
                    }
                ]
            )
        )
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms()

        pair_rooms = [r for r in rooms if r.room_type == RoomType.PAIR]
        # Should merge Alice and bob into one room: alice↔bob
        assert len(pair_rooms) == 1
        assert "alice" in pair_rooms[0].agents
        assert "bob" in pair_rooms[0].agents

    def test_broadcast_unread_excluded(self, tmp_path):
        inbox_dir = tmp_path / "inboxes"
        inbox_dir.mkdir()
        # Same message from alice to bob and carol (broadcast)
        msg = {
            "from": "alice",
            "text": "Broadcast msg",
            "timestamp": "2026-01-01T00:00:00Z",
            "read": False,
        }
        (inbox_dir / "bob.json").write_text(json.dumps([msg]))
        (inbox_dir / "carol.json").write_text(json.dumps([msg]))

        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms()

        pair_rooms = [r for r in rooms if r.room_type == RoomType.PAIR]
        # Both pair rooms should have 0 unread (broadcast excluded)
        for room in pair_rooms:
            assert room.unread_count == 0

    def test_protocol_heavy_flag(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms()

        pair_rooms = {r.name: r for r in rooms if r.room_type == RoomType.PAIR}
        # analyst↔team-lead: 4/4 structured = 100% → protocol_heavy
        assert pair_rooms["analyst↔team-lead"].protocol_heavy is True
        # analyst↔researcher: 1/3 structured = 33% → not protocol_heavy
        assert pair_rooms["analyst↔researcher"].protocol_heavy is False

    def test_structured_types_parsed(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)

        types_found = set()
        for msg in store.all_messages:
            if msg.structured:
                types_found.add(msg.structured.type)

        expected = {
            "permission_request",
            "permission_response",
            "task_assignment",
            "shutdown_request",
            "shutdown_approved",
            "idle_notification",
        }
        assert expected == types_found

    def test_differential_reload_no_changes(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)

        # Reload all files — should return empty since nothing changed
        for path in inbox_dir.glob("*.json"):
            new_msgs = store.load_inbox_file(path)
            assert len(new_msgs) == 0

    def test_get_messages_general(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms()
        general = [r for r in rooms if r.room_type == RoomType.GENERAL][0]
        msgs = store.get_messages(general)
        assert len(msgs) == 10

    def test_extract_tasks(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        tasks = store.extract_tasks()
        assert len(tasks) >= 1
        assert all(t.id for t in tasks)
        assert all(t.subject for t in tasks)


    def test_load_inbox_file_detects_broadcast_at_runtime(self, tmp_path):
        inbox_dir = tmp_path / "inboxes"
        inbox_dir.mkdir()
        
        # Message 1 in bob's inbox
        msg = {
            "from": "alice",
            "text": "Hello world",
            "timestamp": "2026-01-01T00:00:00Z",
            "read": False,
        }
        bob_path = inbox_dir / "bob.json"
        bob_path.write_text(json.dumps([msg]))
        
        store = MessageStore()
        # Initial load bob
        store.load_inbox_file(bob_path)
        assert len(store.all_messages) == 1
        assert not store.all_messages[0].is_broadcast
        
        # Now write the same message to carol's inbox
        carol_path = inbox_dir / "carol.json"
        carol_path.write_text(json.dumps([msg]))
        
        # Load carol's file (simulates file watcher detecting new file / update)
        new_msgs = store.load_inbox_file(carol_path)
        
        # It should detect it as a broadcast
        assert len(new_msgs) == 1
        assert new_msgs[0].is_broadcast is True
        
        # Verify that the original message in bob's room is also updated to is_broadcast=True
        assert all(m.is_broadcast for m in store.all_messages)

    def test_load_all_inboxes_ignores_symlinks(self, tmp_path):
        inbox_dir = tmp_path / "inboxes"
        inbox_dir.mkdir()

        # Create a valid json file
        valid_path = inbox_dir / "valid.json"
        valid_path.write_text(json.dumps([{
            "from": "alice",
            "text": "Hello",
            "timestamp": "2026-01-01T00:00:00Z",
            "read": False,
        }]))

        # Create a target file outside
        target_dir = tmp_path.parent / "target-outside-inbox"
        target_dir.mkdir(exist_ok=True)
        target_path = target_dir / "symlink_target.json"
        target_path.write_text(json.dumps([{
            "from": "attacker",
            "text": "Exploit",
            "timestamp": "2026-01-01T00:00:00Z",
            "read": False,
        }]))

        # Symlink in inboxes directory
        sym_path = inbox_dir / "attacker.json"
        sym_path.symlink_to(target_path)

        store = MessageStore()
        store.load_all_inboxes(inbox_dir)

        # Should only load messages from valid.json, NOT from the symlink!
        assert len(store.all_messages) == 1
        assert store.all_messages[0].sender == "alice"


