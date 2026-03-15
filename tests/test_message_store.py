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

        # Should have @agent rooms
        agent_rooms = [r for r in rooms if r.room_type == RoomType.AGENT]
        assert len(agent_rooms) >= 3

        # Should have some pair rooms
        pair_rooms = [r for r in rooms if r.room_type == RoomType.PAIR]
        assert len(pair_rooms) >= 1

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

    def test_get_messages_agent(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        rooms = store.discover_rooms()
        team_lead_room = [
            r for r in rooms if r.room_type == RoomType.AGENT and r.name == "team-lead"
        ]
        assert len(team_lead_room) == 1
        msgs = store.get_messages(team_lead_room[0])
        assert len(msgs) > 0

    def test_extract_tasks(self, inbox_dir):
        store = MessageStore()
        store.load_all_inboxes(inbox_dir)
        tasks = store.extract_tasks()
        assert len(tasks) >= 1
        assert all(t.id for t in tasks)
        assert all(t.subject for t in tasks)
