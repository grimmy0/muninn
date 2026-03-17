"""Tests for the WaitingScreen."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App
from textual.widgets import LoadingIndicator, Static

from muninn.screens.waiting import WaitingScreen
from muninn.screens.team_select import TeamSelectScreen
from muninn.screens.main import MainScreen


def _make_team(tmp_path: Path, name: str = "alpha") -> Path:
    """Create a minimal team directory with config."""
    team = tmp_path / name
    team.mkdir(parents=True)
    config = {
        "name": name,
        "description": f"Team {name}",
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
    (team / "config.json").write_text(json.dumps(config))
    # Create inboxes directory for MainScreen compatibility
    (team / "inboxes").mkdir()
    return team


class WaitingTestApp(App[None]):
    CSS_PATH = None

    def __init__(self, teams_dir: Path) -> None:
        super().__init__()
        self._teams_dir = teams_dir
        self.team_path: Path | None = None
        self.team_config = None

    def on_mount(self) -> None:
        self.push_screen(WaitingScreen(self._teams_dir))

    def _push_main(self) -> None:
        assert self.team_path is not None
        self.push_screen(MainScreen(self.team_path, self.team_config))


class TestWaitingScreenCompose:
    @pytest.mark.asyncio
    async def test_has_expected_widgets(self, tmp_path: Path) -> None:
        app = WaitingTestApp(tmp_path)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, WaitingScreen)
            # Should have a loading indicator
            indicators = screen.query(LoadingIndicator)
            assert len(indicators) == 1
            # Should have the title and directory widgets
            title = screen.query_one("#waiting-title", Static)
            assert title is not None
            dir_widget = screen.query_one("#waiting-dir", Static)
            assert dir_widget is not None


class TestWaitingScreenQuit:
    @pytest.mark.asyncio
    async def test_q_exits_app(self, tmp_path: Path) -> None:
        app = WaitingTestApp(tmp_path)
        async with app.run_test() as pilot:
            assert isinstance(app.screen, WaitingScreen)
            await pilot.press("q")


class TestWaitingScreenPoll:
    @pytest.mark.asyncio
    async def test_poll_single_team_pushes_main(self, tmp_path: Path) -> None:
        app = WaitingTestApp(tmp_path)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, WaitingScreen)
            # Create a team directory while waiting
            _make_team(tmp_path, "solo-team")
            # Manually trigger the poll
            screen._poll_teams()
            await pilot.pause()
            # Should have transitioned to MainScreen
            assert isinstance(app.screen, MainScreen)

    @pytest.mark.asyncio
    async def test_poll_multiple_teams_pushes_select(self, tmp_path: Path) -> None:
        app = WaitingTestApp(tmp_path)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, WaitingScreen)
            # Create two team directories
            _make_team(tmp_path, "team-a")
            _make_team(tmp_path, "team-b")
            # Manually trigger the poll
            screen._poll_teams()
            await pilot.pause()
            # Should have transitioned to TeamSelectScreen
            assert isinstance(app.screen, TeamSelectScreen)

    @pytest.mark.asyncio
    async def test_poll_no_teams_stays_on_waiting(self, tmp_path: Path) -> None:
        app = WaitingTestApp(tmp_path)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, WaitingScreen)
            # Poll with no teams
            screen._poll_teams()
            await pilot.pause()
            # Should still be on WaitingScreen
            assert isinstance(app.screen, WaitingScreen)
