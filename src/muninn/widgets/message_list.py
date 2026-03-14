from __future__ import annotations

from collections.abc import Callable
from typing import Any

from textual.containers import VerticalScroll
from textual.widgets import Static

from muninn.models.message import Message
from muninn.widgets.message_bubble import render_message

ColorFn = Callable[[str], str]


class MessageList(VerticalScroll):
    """Scrollable list of messages with auto-scroll.

    Renders messages in batches to keep widget count manageable.
    Each batch is a single Static widget containing multiple messages.
    """

    DEFAULT_CSS = """
    MessageList {
        width: 1fr;
        height: 1fr;
    }
    """

    BATCH_SIZE: int = 50

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._auto_scroll_enabled = True
        self._messages: list[Message] = []
        self._color_fn: ColorFn | None = None
        self._show_recipient = True

    def load_messages(
        self,
        messages: list[Message],
        color_fn: ColorFn,
        show_recipient: bool = True,
        filter_permissions: bool = False,
    ) -> None:
        self.remove_children()
        self._color_fn = color_fn
        self._show_recipient = show_recipient

        if filter_permissions:
            messages = [
                m for m in messages
                if not (m.structured and m.structured.type in ("permission_request", "permission_response"))
            ]
        self._messages = messages

        # Render in batches
        for i in range(0, len(messages), self.BATCH_SIZE):
            batch = messages[i : i + self.BATCH_SIZE]
            content = "\n".join(
                render_message(msg, color_fn(msg.sender), show_recipient)
                for msg in batch
            )
            _ = self.mount(Static(content, markup=True))

        if self._auto_scroll_enabled:
            self.call_after_refresh(self.scroll_end, animate=False)

    def append_message(self, msg: Message, color: str, show_recipient: bool = True) -> None:
        self._messages.append(msg)
        content = render_message(msg, color, show_recipient)
        self.mount(Static(content, markup=True))
        if self._auto_scroll_enabled:
            self.call_after_refresh(self.scroll_end, animate=False)

    def on_scroll_y(self) -> None:
        if self.scroll_offset.y < self.max_scroll_y - 2:
            self._auto_scroll_enabled = False
        else:
            self._auto_scroll_enabled = True

    def find_matches(self, query: str) -> list[int]:
        """Return indices of messages matching query (case-insensitive)."""
        q = query.lower()
        return [
            i
            for i, msg in enumerate(self._messages)
            if q in msg.text.lower() or q in msg.sender.lower()
        ]

    def highlight_match(self, message_idx: int) -> None:
        """Scroll so the batch containing message_idx is visible."""
        batch_idx = message_idx // self.BATCH_SIZE
        children = list(self.children)
        if 0 <= batch_idx < len(children):
            children[batch_idx].scroll_visible(animate=False)
