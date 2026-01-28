from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any

from roaudter_agent.contracts import TaskEnvelope


class ProviderError(RuntimeError):
    pass


class ProviderAdapter(Protocol):
    name: str

    def healthcheck(self) -> bool: ...
    def generate(self, task: TaskEnvelope) -> Any: ...


@dataclass(slots=True)
class ProviderState:
    adapter: ProviderAdapter
    healthy: bool = True
