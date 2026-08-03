from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _has_safe_nesting(text: str, max_depth: int = 10) -> bool:
    """Check if the text has nesting depth of braces/brackets <= max_depth, ignoring strings."""
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == '\\':
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char in "{[":
                depth += 1
                if depth > max_depth:
                    return False
            elif char in "]}":
                depth = 0 if depth <= 0 else depth - 1
    return True


@dataclass(frozen=True)
class StructuredPayload:
    type: str
    data: dict[str, Any]

    @classmethod
    def from_text(cls, text: str) -> StructuredPayload | None:
        if not text or text[0] != "{":
            return None
        if len(text) > 65536:
            return None
        if not _has_safe_nesting(text, max_depth=10):
            return None
        try:
            parsed: dict[str, Any] = json.loads(text)
            if isinstance(parsed, dict) and "type" in parsed:
                msg_type: str = parsed.pop("type")
                return cls(type=msg_type, data=parsed)
        except (json.JSONDecodeError, KeyError):
            pass
        return None


@dataclass(frozen=True)
class Message:
    sender: str
    recipient: str
    text: str
    timestamp: datetime
    read: bool
    color: str
    summary: str
    structured: StructuredPayload | None
    is_broadcast: bool
    source_file: str

    @classmethod
    def from_raw(cls, raw: dict[str, Any], recipient: str, source_file: str) -> Message:
        raw_text = raw.get("text", "")
        text_str = raw_text if isinstance(raw_text, str) else str(raw_text)
        structured = StructuredPayload.from_text(text_str)

        ts_val = raw.get("timestamp", "")
        ts_str = ts_val if isinstance(ts_val, str) else str(ts_val)
        try:
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.min

        summary = ""
        if structured:
            summary = cls._make_summary(structured)

        sender_val = raw.get("from", "unknown")
        sender_str = str(sender_val).lower()
        color_val = raw.get("color", "")
        color_str = color_val if isinstance(color_val, str) else str(color_val)

        return cls(
            sender=sender_str,
            recipient=str(recipient).lower(),
            text=text_str,
            timestamp=timestamp,
            read=bool(raw.get("read", False)),
            color=color_str,
            summary=summary,
            structured=structured,
            is_broadcast=False,
            source_file=source_file,
        )

    @staticmethod
    def _make_summary(payload: StructuredPayload) -> str:
        t = payload.type
        d = payload.data
        if t == "permission_request":
            tool = d.get("tool_name", "unknown")
            desc = d.get("description", "")
            return f"[PERM] {tool}: {desc[:80]}"
        elif t == "permission_response":
            approved = d.get("subtype") == "success"
            resp = d.get("response", {})
            desc = ""
            if isinstance(resp, dict):
                updated = resp.get("updated_input", {})
                if isinstance(updated, dict):
                    desc = str(updated.get("description", ""))
            return f"[{'APPROVED' if approved else 'DENIED'}] {desc[:80]}"
        elif t == "task_assignment":
            subject = d.get("subject", "")
            return f"[TASK] {subject[:80]}"
        elif t in ("shutdown_request", "shutdown_approved"):
            return f"[{t.upper().replace('_', ' ')}]"
        elif t == "idle_notification":
            return f"[IDLE] {d.get('summary', '')[:80]}"
        else:
            return f"[{t}]"
