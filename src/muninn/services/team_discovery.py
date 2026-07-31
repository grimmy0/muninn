from __future__ import annotations

import json
import logging
from pathlib import Path

from muninn.models.team import TeamConfig

logger = logging.getLogger(__name__)


def is_safe_path(path: Path, base_dir: Path) -> bool:
    """Check that path is strictly within base_dir and contains no symbolic links."""
    try:
        resolved_base = base_dir.resolve()
        resolved_path = path.resolve()
    except OSError:
        return False

    # Prevent directory traversal
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError:
        return False

    # Prevent symbolic links in any path component
    curr = path
    while curr != base_dir and curr != curr.parent:
        if curr.is_symlink():
            return False
        curr = curr.parent

    return True


def discover_teams(teams_dir: Path | None = None) -> list[tuple[Path, TeamConfig]]:
    if teams_dir is None:
        teams_dir = Path.home() / ".claude" / "teams"
    try:
        teams_dir = teams_dir.resolve()
    except OSError:
        return []
    if not teams_dir.is_dir():
        return []

    results = []
    for entry in sorted(teams_dir.iterdir()):
        if entry.is_symlink():
            continue
        if not entry.is_dir():
            continue
        if not is_safe_path(entry, teams_dir):
            continue

        config_path = entry / "config.json"
        if config_path.is_symlink():
            continue
        if config_path.exists():
            try:
                raw = json.loads(config_path.read_text())
                config = TeamConfig.from_raw(raw)
                results.append((entry, config))
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.warning("Failed to load/parse team config at %s: %s", config_path, e, exc_info=True)
                continue
    return results


def load_team_config(team_path: Path, teams_dir: Path | None = None) -> TeamConfig | None:
    if teams_dir is None:
        default_dir = Path.home() / ".claude" / "teams"
        try:
            team_path.resolve().relative_to(default_dir.resolve())
            teams_dir = default_dir
        except (ValueError, OSError):
            teams_dir = team_path.parent
    try:
        teams_dir = teams_dir.resolve()
    except OSError:
        return None

    if not is_safe_path(team_path, teams_dir):
        return None

    config_path = team_path / "config.json"
    if config_path.is_symlink():
        return None
    if not config_path.exists():
        return None
    try:
        raw = json.loads(config_path.read_text())
        return TeamConfig.from_raw(raw)
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.warning("Failed to load/parse team config at %s: %s", config_path, e, exc_info=True)
        return None


def discover_agents_from_inboxes(team_path: Path, teams_dir: Path | None = None) -> set[str]:
    if teams_dir is None:
        default_dir = Path.home() / ".claude" / "teams"
        try:
            team_path.resolve().relative_to(default_dir.resolve())
            teams_dir = default_dir
        except (ValueError, OSError):
            teams_dir = team_path.parent
    try:
        teams_dir = teams_dir.resolve()
    except OSError:
        return set()

    if not is_safe_path(team_path, teams_dir):
        return set()

    inbox_dir = team_path / "inboxes"
    if inbox_dir.is_symlink():
        return set()
    if not inbox_dir.is_dir():
        return set()
    return {f.stem for f in inbox_dir.glob("*.json") if not f.is_symlink()}


