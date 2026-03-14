from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, OptionList
from textual.widgets.option_list import Option

from muninn.models.team import TeamConfig

if TYPE_CHECKING:
    from muninn.app import MuninnApp


class TeamSelectScreen(Screen):
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, teams: list[tuple[Path, TeamConfig]]) -> None:
        super().__init__()
        self._teams = teams

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        option_list = OptionList(id="team-list")
        for _path, config in self._teams:
            members = len(config.members)
            label = f"{config.name} — {config.description[:60]} ({members} members)"
            option_list.add_option(Option(label, id=config.name))
        yield option_list
        yield Footer()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        path, config = self._teams[idx]
        app: MuninnApp = self.app  # type: ignore[assignment]
        app.team_path = path
        app.team_config = config
        app.pop_screen()
        app.push_screen("main")
