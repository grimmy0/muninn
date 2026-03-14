from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    subject: str
    description: str
    status: str
    assigned_by: str
