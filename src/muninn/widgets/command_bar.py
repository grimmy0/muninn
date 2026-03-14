from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Static


class CommandBar(Static):
    """Search (/) and command (:) input bar, hidden by default."""

    DEFAULT_CSS = """
    CommandBar {
        display: none;
        height: 1;
        dock: bottom;
        layout: horizontal;
    }
    CommandBar.visible {
        display: block;
    }
    CommandBar #cb-prompt {
        width: 2;
        background: $accent;
        color: $text;
    }
    CommandBar #cb-input {
        width: 1fr;
        border: none;
        height: 1;
        padding: 0;
    }
    CommandBar #cb-input:focus {
        border: none;
    }
    """

    class Submitted(Message):
        def __init__(self, mode: str, value: str) -> None:
            super().__init__()
            self.mode = mode
            self.value = value

    class Dismissed(Message):
        def __init__(self, mode: str) -> None:
            super().__init__()
            self.mode = mode

    def __init__(self, id: str | None = None) -> None:  # noqa: A002
        super().__init__(id=id)
        self._mode = "/"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static("/", id="cb-prompt")
            yield Input(id="cb-input")

    def show(self, mode: str = "/") -> None:
        self._mode = mode
        self.query_one("#cb-prompt", Static).update(mode)
        inp = self.query_one("#cb-input", Input)
        inp.value = ""
        self.add_class("visible")
        inp.focus()

    def hide(self) -> None:
        self.remove_class("visible")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        value = event.value.strip()
        self.hide()
        if value:
            self.post_message(self.Submitted(self._mode, value))
        else:
            self.post_message(self.Dismissed(self._mode))

    def on_key(self, event: object) -> None:
        from textual.events import Key

        if isinstance(event, Key) and event.key == "escape":
            event.stop()
            self.hide()
            self.post_message(self.Dismissed(self._mode))
