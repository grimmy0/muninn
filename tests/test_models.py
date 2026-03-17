import json

from muninn.models.message import Message, StructuredPayload
from muninn.models.room import Room, RoomType
from muninn.models.team import TeamConfig


class TestStructuredPayload:
    def test_from_text_permission_request(self):
        text = json.dumps(
            {"type": "permission_request", "tool_name": "Bash", "description": "run ls"}
        )
        payload = StructuredPayload.from_text(text)
        assert payload is not None
        assert payload.type == "permission_request"
        assert payload.data["tool_name"] == "Bash"

    def test_from_text_plain_text(self):
        assert StructuredPayload.from_text("hello world") is None

    def test_from_text_empty(self):
        assert StructuredPayload.from_text("") is None

    def test_from_text_invalid_json(self):
        assert StructuredPayload.from_text("{invalid") is None

    def test_from_text_no_type_key(self):
        assert StructuredPayload.from_text('{"foo": "bar"}') is None

    def test_all_structured_types(self):
        for t in [
            "permission_request",
            "permission_response",
            "task_assignment",
            "shutdown_request",
            "shutdown_approved",
            "idle_notification",
        ]:
            text = json.dumps({"type": t, "data": "test"})
            payload = StructuredPayload.from_text(text)
            assert payload is not None
            assert payload.type == t


class TestMessage:
    def test_from_raw_plain(self):
        raw = {
            "from": "alice",
            "text": "hello bob",
            "timestamp": "2026-03-14T02:24:20.813Z",
            "color": "blue",
            "read": False,
        }
        msg = Message.from_raw(raw, "bob", "bob.json")
        assert msg.sender == "alice"
        assert msg.recipient == "bob"
        assert msg.text == "hello bob"
        assert msg.structured is None
        assert not msg.is_broadcast

    def test_from_raw_structured(self):
        raw = {
            "from": "team-lead",
            "text": json.dumps(
                {"type": "task_assignment", "taskId": "1", "subject": "Do stuff"}
            ),
            "timestamp": "2026-03-14T02:24:20.813Z",
            "read": False,
        }
        msg = Message.from_raw(raw, "worker", "worker.json")
        assert msg.structured is not None
        assert msg.structured.type == "task_assignment"
        assert "TASK" in msg.summary


class TestRoom:
    def test_general_matches_all(self):
        room = Room(RoomType.GENERAL, "general", ("a", "b"))
        assert room.matches_message("a", "b")
        assert room.matches_message("c", "d")

    def test_pair_room(self):
        room = Room(RoomType.PAIR, "a↔b", ("a", "b"))
        assert room.matches_message("a", "b")
        assert room.matches_message("b", "a")
        assert not room.matches_message("a", "c")

    def test_display_name(self):
        assert Room(RoomType.GENERAL, "general", ()).display_name == "#general"
        assert Room(RoomType.PAIR, "a↔b", ("a", "b")).display_name == "a↔b"


class TestTeamConfig:
    def test_from_raw(self):
        raw = {
            "name": "test-team",
            "description": "A test team",
            "createdAt": 1773454977303,
            "leadAgentId": "lead@test",
            "leadSessionId": "abc-123",
            "members": [
                {
                    "agentId": "lead@test",
                    "name": "lead",
                    "agentType": "team-lead",
                    "model": "opus",
                    "joinedAt": 1773454977303,
                    "cwd": "/tmp",
                }
            ],
        }
        config = TeamConfig.from_raw(raw)
        assert config.name == "test-team"
        assert len(config.members) == 1
        assert config.members[0].name == "lead"
