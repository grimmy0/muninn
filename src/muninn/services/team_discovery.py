from __future__ import annotations

import json
from pathlib import Path

from muninn.models.team import TeamConfig


def discover_teams(teams_dir: Path | None = None) -> list[tuple[Path, TeamConfig]]:
    if teams_dir is None:
        teams_dir = Path.home() / ".claude" / "teams"
    if not teams_dir.is_dir():
        return []

    results = []
    for entry in sorted(teams_dir.iterdir()):
        if not entry.is_dir():
            continue
        config_path = entry / "config.json"
        if config_path.exists():
            try:
                raw = json.loads(config_path.read_text())
                config = TeamConfig.from_raw(raw)
                results.append((entry, config))
            except (json.JSONDecodeError, KeyError):
                continue
    return results


def load_team_config(team_path: Path) -> TeamConfig | None:
    config_path = team_path / "config.json"
    if not config_path.exists():
        return None
    try:
        raw = json.loads(config_path.read_text())
        return TeamConfig.from_raw(raw)
    except (json.JSONDecodeError, KeyError):
        return None


def discover_agents_from_inboxes(team_path: Path) -> set[str]:
    inbox_dir = team_path / "inboxes"
    if not inbox_dir.is_dir():
        return set()
    return {f.stem for f in inbox_dir.glob("*.json")}
