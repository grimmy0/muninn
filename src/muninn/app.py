from __future__ import annotations

from pathlib import Path

from textual.app import App

from muninn.models.team import TeamConfig
from muninn.services.team_discovery import discover_teams, load_team_config


class MuninnApp(App[None]):
    TITLE = "Muninn"
    CSS_PATH = "styles.tcss"

    def __init__(
        self,
        team_path: Path | None = None,
        team_name: str | None = None,
        teams_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self._initial_path: Path | None = team_path
        self._initial_name: str | None = team_name
        self._teams_dir: Path | None = teams_dir
        self.team_path: Path | None = team_path
        self.team_config: TeamConfig | None = None

    def on_mount(self) -> None:
        if self._initial_path:
            self.team_path = self._initial_path
            self.team_config = load_team_config(self._initial_path)
            self._push_main()
        elif self._initial_name:
            self._resolve_team_name()
        else:
            self._auto_discover()

    def _resolve_team_name(self) -> None:
        if not self._teams_dir or not self._initial_name:
            self.exit(message="No teams directory found")
            return
        team_dir = self._teams_dir / self._initial_name
        if team_dir.is_dir():
            self.team_path = team_dir
            self.team_config = load_team_config(team_dir)
            self._push_main()
        else:
            self.exit(message=f"Team '{self._initial_name}' not found in {self._teams_dir}")

    def _auto_discover(self) -> None:
        teams = discover_teams(self._teams_dir)
        if not teams:
            self.exit(message="No teams found")
        elif len(teams) == 1:
            self.team_path, self.team_config = teams[0]
            self._push_main()
        else:
            from muninn.screens.team_select import TeamSelectScreen
            _ = self.push_screen(TeamSelectScreen(teams))

    def _push_main(self) -> None:
        from muninn.screens.main import MainScreen
        assert self.team_path is not None
        _ = self.push_screen(MainScreen(self.team_path, self.team_config))
