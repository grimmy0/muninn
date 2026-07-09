"""Tests for TUI screens and widgets integration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Static

from muninn.screens.help import HelpScreen
from muninn.screens.team_select import TeamSelectScreen
from muninn.screens.main import MainScreen
from muninn.app import MuninnApp


def _make_team(tmp_path: Path, name: str = "alpha") -> Path:
    """Create a minimal team directory with config."""
    team = tmp_path / name
    team.mkdir(parents=True, exist_ok=True)
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
    (team / "inboxes").mkdir(exist_ok=True)
    return team


class HelpTestApp(App[None]):
    CSS_PATH = None

    def on_mount(self) -> None:
        self.push_screen(HelpScreen())


@pytest.mark.asyncio
async def test_help_screen_dismiss() -> None:
    app = HelpTestApp()
    async with app.run_test() as pilot:
        assert isinstance(app.screen, HelpScreen)
        static = app.screen.query_one(Static)
        assert static is not None

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_team_select_screen_integration(tmp_path: Path) -> None:
    # Create two fake teams
    _make_team(tmp_path, "team-a")
    _make_team(tmp_path, "team-b")

    app = MuninnApp(teams_dir=tmp_path)
    async with app.run_test() as pilot:
        # App should start on TeamSelectScreen
        assert isinstance(app.screen, TeamSelectScreen)

        option_list = app.screen.query_one("#team-list")
        assert option_list.option_count == 2

        # Post OptionSelected event for first team using OptionList.OptionSelected
        from textual.widgets import OptionList
        option = option_list.get_option_at_index(0)
        option_list.post_message(
            OptionList.OptionSelected(option_list, option, 0)
        )
        await pilot.pause()

        # Should transition to MainScreen
        assert isinstance(app.screen, MainScreen)
        assert app.team_path == tmp_path / "team-a"
