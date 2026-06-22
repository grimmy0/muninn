from __future__ import annotations

import logging
from pathlib import Path
import sys

import click


@click.command()
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    help="Direct path to team directory",
)
@click.option("--team", type=str, help="Team name to look up in teams directory")
@click.option(
    "--teams-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Override teams directory (default: ~/.claude/teams)",
)
def main(path: Path | None, team: str | None, teams_dir: Path | None) -> None:
    """TUI for viewing agent team communications."""
    log_dir = Path.home() / ".claude"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "muninn.log"

    logging.basicConfig(
        filename=str(log_file),
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    from muninn.app import MuninnApp

    if path and team:
        raise click.UsageError("Cannot specify both --path and --team")

    if teams_dir is None:
        teams_dir = Path.home() / ".claude" / "teams"

    app = MuninnApp(team_path=path, team_name=team, teams_dir=teams_dir)
    _ = app.run()


if __name__ == "__main__":
    main()
