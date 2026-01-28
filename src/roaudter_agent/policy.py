from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.providers.base import ProviderState


@dataclass(slots=True)
class RouterPolicy:
    """
    Returns provider preference order (names), filtered by health.
    """
    default_chain: List[str]

    def select_chain(self, task: TaskEnvelope, providers: Iterable[ProviderState]) -> List[ProviderState]:
        by_name = {p.adapter.name: p for p in providers if p.healthy and p.adapter.healthcheck()}

        chain: List[str] = []
        if task.provider_hint:
            chain.append(task.provider_hint)

        # Simple heuristic (can evolve later)
        if task.intent.lower() in {"code", "coding", "patch"}:
            chain += ["ollama", "openai"]
        else:
            chain += ["openai", "ollama"]

        chain += self.default_chain

        # de-dup while preserving order
        seen = set()
        uniq = []
        for name in chain:
            if name and name not in seen:
                seen.add(name)
                uniq.append(name)

        return [by_name[n] for n in uniq if n in by_name]
