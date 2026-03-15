from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MemberInfo:
    agent_id: str
    name: str
    agent_type: str
    model: str
    joined_at: datetime
    cwd: str

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> MemberInfo:
        joined_ts = raw.get("joinedAt", 0)
        try:
            joined = datetime.fromtimestamp(joined_ts / 1000)
        except (ValueError, TypeError, OSError):
            joined = datetime.min
        return cls(
            agent_id=raw.get("agentId", ""),
            name=raw.get("name", ""),
            agent_type=raw.get("agentType", ""),
            model=raw.get("model", ""),
            joined_at=joined,
            cwd=raw.get("cwd", ""),
        )


@dataclass(frozen=True)
class TeamConfig:
    name: str
    description: str
    created_at: datetime
    lead_agent_id: str
    lead_session_id: str
    members: tuple[MemberInfo, ...]

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TeamConfig:
        created_ts = raw.get("createdAt", 0)
        try:
            created = datetime.fromtimestamp(created_ts / 1000)
        except (ValueError, TypeError, OSError):
            created = datetime.min
        members = tuple(MemberInfo.from_raw(m) for m in raw.get("members", []))
        return cls(
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            created_at=created,
            lead_agent_id=raw.get("leadAgentId", ""),
            lead_session_id=raw.get("leadSessionId", ""),
            members=members,
        )
