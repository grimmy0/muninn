from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold underline]Muninn Keyboard Shortcuts[/]

[bold]Navigation[/]
  h            Focus sidebar
  l            Focus content panel
  Tab          Cycle focus

[bold]Scrolling[/]
  j / k        Scroll down / up
  G             Jump to bottom
  gg            Jump to top
  Ctrl+d / u   Half page down / up
  Ctrl+f / b   Full page down / up

[bold]Tabs[/]
  1 / 2 / 3   Messages / Tasks / Team

[bold]Search[/]
  /            Search messages
  n / N        Next / Previous match

[bold]Commands[/]
  :            Command mode
               :q  :quit   Exit
               :h  :help   Show help

[bold]Other[/]
  p            Toggle permission messages
  ?            This help screen
  q            Quit
"""


class HelpScreen(ModalScreen[None]):
    """Modal overlay showing all keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("question_mark", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-overlay {
        background: $surface 90%;
        width: 60;
        max-height: 80%;
        padding: 1 2;
        border: thick $accent;
    }
    """

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="help-overlay"):
                yield Static(HELP_TEXT, markup=True)

    async def action_dismiss(self, result: None = None) -> None:
        self.dismiss(result)
