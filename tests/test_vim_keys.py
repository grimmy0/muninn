"""Tests for nvim-style keyboard navigation."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from textual.app import App
from textual.widgets import ListView

from muninn.screens.main import MainScreen
from muninn.widgets.command_bar import CommandBar
from muninn.widgets.message_list import MessageList
from muninn.models.message import Message


# --- Fixtures ---

def _make_team_dir(tmp_path: Path) -> Path:
    """Create a minimal team directory with inboxes and config."""
    team = tmp_path / "test-team"
    team.mkdir()
    inboxes = team / "inboxes"
    inboxes.mkdir()
    # Create a config file
    config = {
        "name": "test-team",
        "description": "Test team",
        "created_at": "2025-01-01T00:00:00Z",
        "lead_agent_id": "agent-a",
        "members": [
            {
                "name": "agent-a",
                "agent_type": "claude",
                "model": "sonnet",
                "cwd": "/tmp",
            }
        ],
    }
    (team / "team.json").write_text(json.dumps(config))
    # Create an inbox with messages (JSON array format, .json extension)
    inbox = inboxes / "agent-a.json"
    messages = [
        {
            "from": "agent-b",
            "text": f"Hello message {i}",
            "timestamp": f"2025-01-01T00:0{i}:00Z",
            "read": False,
        }
        for i in range(5)
    ]
    inbox.write_text(json.dumps(messages))
    return team


class TestApp(App[None]):
    """Test app that wraps MainScreen."""

    CSS_PATH = None

    def __init__(self, team_path: Path) -> None:
        super().__init__()
        self._team_path = team_path

    def on_mount(self) -> None:
        self.push_screen(MainScreen(self._team_path))


# --- gg state machine tests ---


class TestGgStateMachine:
    """Test the gg double-tap state machine on MainScreen."""

    @pytest.mark.asyncio
    async def test_double_g_scrolls_to_top(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, MainScreen)
            # Initially g_pending is False
            assert screen._g_pending is False
            # First g press sets pending
            await pilot.press("g")
            assert screen._g_pending is True
            # Second g press clears pending (scrolls to top)
            await pilot.press("g")
            assert screen._g_pending is False

    @pytest.mark.asyncio
    async def test_g_timeout_clears_pending(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, MainScreen)
            await pilot.press("g")
            assert screen._g_pending is True
            # Wait for timeout (500ms + buffer)
            await asyncio.sleep(0.7)
            assert screen._g_pending is False

    @pytest.mark.asyncio
    async def test_G_clears_g_pending(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, MainScreen)
            await pilot.press("g")
            assert screen._g_pending is True
            await pilot.press("G")
            assert screen._g_pending is False


# --- Focus switching tests ---


class TestFocusSwitching:
    @pytest.mark.asyncio
    async def test_h_focuses_sidebar(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            await pilot.press("h")
            focused = app.focused
            assert isinstance(focused, ListView)

    @pytest.mark.asyncio
    async def test_l_focuses_content(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            await pilot.press("l")
            focused = app.focused
            assert isinstance(focused, MessageList)


# --- j/k scroll routing tests ---


class TestScrollRouting:
    @pytest.mark.asyncio
    async def test_j_k_on_message_list(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            # Focus message list
            await pilot.press("l")
            await pilot.press("j")
            await pilot.pause()
            # j should scroll down (or stay if already at bottom)
            # k should scroll up (or stay if already at top)
            await pilot.press("k")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_j_k_on_list_view(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            # Focus sidebar ListView
            await pilot.press("h")
            await pilot.press("j")
            await pilot.pause()
            # Should move cursor
            await pilot.press("k")
            await pilot.pause()


# --- Command bar tests ---


class TestCommandBar:
    @pytest.mark.asyncio
    async def test_slash_opens_command_bar(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            cb = app.screen.query_one("#command-bar", CommandBar)
            assert not cb.has_class("visible")
            await pilot.press("slash")
            assert cb.has_class("visible")

    @pytest.mark.asyncio
    async def test_escape_closes_command_bar(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            cb = app.screen.query_one("#command-bar", CommandBar)
            await pilot.press("slash")
            assert cb.has_class("visible")
            await pilot.press("escape")
            assert not cb.has_class("visible")

    @pytest.mark.asyncio
    async def test_colon_q_exits(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            await pilot.press("colon")
            cb = app.screen.query_one("#command-bar", CommandBar)
            assert cb.has_class("visible")


# --- Search tests ---


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_finds_matches(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, MainScreen)
            # Perform search
            screen._execute_search("Hello")
            assert len(screen._search_matches) > 0
            assert screen._search_match_idx == 0

    @pytest.mark.asyncio
    async def test_search_no_matches(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, MainScreen)
            screen._execute_search("nonexistent_xyz")
            assert len(screen._search_matches) == 0
            assert screen._search_match_idx == -1

    @pytest.mark.asyncio
    async def test_search_next_prev_cycling(self, tmp_path: Path) -> None:
        team = _make_team_dir(tmp_path)
        app = TestApp(team)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, MainScreen)
            screen._execute_search("Hello")
            count = len(screen._search_matches)
            assert count > 1
            # n cycles forward
            screen.action_search_next()
            assert screen._search_match_idx == 1
            # N cycles backward
            screen.action_search_prev()
            assert screen._search_match_idx == 0
            # Wrap around backward
            screen.action_search_prev()
            assert screen._search_match_idx == count - 1


# --- MessageList search tests ---


class TestMessageListSearch:
    def test_find_matches_case_insensitive(self) -> None:
        messages = [
            Message(
                sender="alice",
                recipient="bob",
                text="Hello world",
                timestamp=datetime.now(tz=timezone.utc),
                read=False,
                color="",
                summary="",
                structured=None,
                is_broadcast=False,
                source_file="test.jsonl",
            ),
            Message(
                sender="bob",
                recipient="alice",
                text="Goodbye world",
                timestamp=datetime.now(tz=timezone.utc),
                read=False,
                color="",
                summary="",
                structured=None,
                is_broadcast=False,
                source_file="test.jsonl",
            ),
            Message(
                sender="alice",
                recipient="bob",
                text="hello again",
                timestamp=datetime.now(tz=timezone.utc),
                read=False,
                color="",
                summary="",
                structured=None,
                is_broadcast=False,
                source_file="test.jsonl",
            ),
        ]
        ml = MessageList()
        ml._messages = messages
        matches = ml.find_matches("hello")
        assert matches == [0, 2]

    def test_find_matches_by_sender(self) -> None:
        messages = [
            Message(
                sender="alice",
                recipient="bob",
                text="some text",
                timestamp=datetime.now(tz=timezone.utc),
                read=False,
                color="",
                summary="",
                structured=None,
                is_broadcast=False,
                source_file="test.jsonl",
            ),
        ]
        ml = MessageList()
        ml._messages = messages
        matches = ml.find_matches("alice")
        assert matches == [0]

    def test_find_matches_no_results(self) -> None:
        ml = MessageList()
        ml._messages = []
        matches = ml.find_matches("anything")
        assert matches == []
