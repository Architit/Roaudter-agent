from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class TaskEnvelope:
    task_id: str
    agent: str
    intent: str
    priority: int = 0
    payload: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    provider_hint: Optional[str] = None


@dataclass(slots=True)
class ResultEnvelope:
    task_id: str
    status: str  # "ok" | "error"
    provider_used: Optional[str] = None
    latency_ms: Optional[int] = None
    tokens: int | None = None
    usage: dict | None = None
    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None
