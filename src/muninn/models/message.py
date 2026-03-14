from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StructuredPayload:
    type: str
    data: dict[str, Any]

    @classmethod
    def from_text(cls, text: str) -> StructuredPayload | None:
        if not text or text[0] != "{":
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
        structured = StructuredPayload.from_text(raw.get("text", ""))
        ts_str: str = raw.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.min

        summary = ""
        if structured:
            summary = cls._make_summary(structured)

        return cls(
            sender=raw.get("from", "unknown"),
            recipient=recipient,
            text=raw.get("text", ""),
            timestamp=timestamp,
            read=raw.get("read", False),
            color=raw.get("color", ""),
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
