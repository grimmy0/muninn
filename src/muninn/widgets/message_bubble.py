from __future__ import annotations

from muninn.models.message import Message


def _escape(text: str) -> str:
    """Escape Rich markup characters in user text."""
    return text.replace("[", "\\[")


def render_message(msg: Message, color: str, show_recipient: bool = True) -> str:
    """Render a message as Rich markup text with a border-like frame."""
    ts = msg.timestamp.strftime("%H:%M:%S")

    # System events: shutdown, idle — minimal rendering
    if msg.structured and msg.structured.type in (
        "shutdown_request",
        "shutdown_approved",
        "idle_notification",
    ):
        if msg.structured.type == "idle_notification":
            summary = msg.structured.data.get("summary", "")
            return f"[dim]    {_escape(msg.sender)} idle — {_escape(summary)}  \\[{ts}][/dim]"
        label = msg.structured.type.replace("_", " ").upper()
        return f"[dim]    {_escape(msg.sender)}: \\[{label}]  \\[{ts}][/dim]"

    lines = []

    # Header line
    header_parts = [f"[bold {color}]{_escape(msg.sender)}[/]"]
    if show_recipient:
        header_parts.append(f" → {_escape(msg.recipient)}")
    header_parts.append(f"  \\[{ts}]")
    if msg.is_broadcast:
        header_parts.append(" [bold magenta]\\[broadcast][/]")
    lines.append("".join(header_parts))

    # Body
    if msg.structured:
        lines.append(_render_structured(msg))
    else:
        lines.append(f"  {_escape(msg.text)}")

    # Simple frame using box chars
    content = "\n".join(lines)
    return f"╭─\n│ {content.replace(chr(10), chr(10) + '│ ')}\n╰─"


def _render_structured(msg: Message) -> str:
    assert msg.structured is not None
    payload = msg.structured
    t = payload.type
    d = payload.data

    if t == "permission_request":
        tool = _escape(d.get("tool_name", "?"))
        desc = _escape(str(d.get("description", "")))
        return f"  [bold yellow]⚡ PERM REQUEST[/] {tool}\n  {desc}"

    elif t == "permission_response":
        approved = d.get("subtype") == "success"
        tag = "[bold green]✓ APPROVED[/]" if approved else "[bold red]✗ DENIED[/]"
        resp = d.get("response", {})
        desc = ""
        if isinstance(resp, dict):
            updated = resp.get("updated_input", {})
            if isinstance(updated, dict):
                desc = str(updated.get("description", ""))
        return f"  {tag} {_escape(desc)}"

    elif t == "task_assignment":
        subject = _escape(str(d.get("subject", "")))
        desc = _escape(str(d.get("description", "")))
        return f"  [bold cyan]📋 TASK[/] {subject}\n  {desc}"

    else:
        return f"  \\[{_escape(t)}] {_escape(msg.summary)}"
