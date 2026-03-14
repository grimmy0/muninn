from __future__ import annotations

from pathlib import Path

from textual.message import Message as TextualMessage
from textual.message_pump import MessagePump


class InboxFileChanged(TextualMessage):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path


class NewInboxFile(TextualMessage):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path


class ConfigChanged(TextualMessage):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path


async def watch_team_dir(team_path: Path, target: MessagePump) -> None:
    """Watch team directory for changes. Run as a Textual worker."""
    import watchfiles

    inbox_dir = team_path / "inboxes"
    config_path = team_path / "config.json"
    known_files = {str(p) for p in inbox_dir.glob("*.json")} if inbox_dir.is_dir() else set()

    paths_to_watch: list[str] = []
    if inbox_dir.is_dir():
        paths_to_watch.append(str(inbox_dir))
    if config_path.exists():
        paths_to_watch.append(str(config_path))

    if not paths_to_watch:
        return

    async for changes in watchfiles.awatch(*paths_to_watch):
        for _change_type, path_str in changes:
            path = Path(path_str)
            if path.suffix != ".json":
                continue

            if path.name == "config.json":
                target.post_message(ConfigChanged(path))
            elif path.parent.name == "inboxes":
                if path_str not in known_files:
                    known_files.add(path_str)
                    target.post_message(NewInboxFile(path))
                else:
                    target.post_message(InboxFileChanged(path))
