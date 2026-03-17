from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Static

from muninn.services.team_discovery import discover_teams

if TYPE_CHECKING:
    from muninn.app import MuninnApp


class WaitingScreen(Screen):
    BINDINGS = [("q", "quit", "Quit")]

    def action_quit(self) -> None:
        self.app.exit()

    DEFAULT_CSS = """
    WaitingScreen {
        align: center middle;
    }
    #waiting-container {
        width: 60;
        height: auto;
        padding: 2 4;
        border: thick $accent;
        background: $surface;
    }
    #waiting-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #waiting-dir {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }
    #waiting-hint {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, teams_dir: Path | None = None) -> None:
        super().__init__()
        self._teams_dir = teams_dir or Path.home() / ".claude" / "teams"

    def compose(self) -> ComposeResult:
        with Center():
            with Middle():
                with Vertical(id="waiting-container"):
                    yield Static("Waiting for teams...", id="waiting-title")
                    yield Static(
                        f"Watching: {self._teams_dir}", id="waiting-dir"
                    )
                    yield LoadingIndicator()
                    yield Static(
                        "Teams will be loaded automatically when discovered",
                        id="waiting-hint",
                    )

    def on_mount(self) -> None:
        self.set_interval(3.0, self._poll_teams)

    def _poll_teams(self) -> None:
        teams = discover_teams(self._teams_dir)
        if not teams:
            return
        app: MuninnApp = self.app  # type: ignore[assignment]
        if len(teams) == 1:
            app.team_path, app.team_config = teams[0]
            app.pop_screen()
            app._push_main()
        else:
            from muninn.screens.team_select import TeamSelectScreen

            app.pop_screen()
            app.push_screen(TeamSelectScreen(teams))
