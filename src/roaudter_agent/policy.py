from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.providers.base import ProviderState


def _requested_model(task: TaskEnvelope) -> str | None:
    return (
        task.constraints.get("model")
        or task.payload.get("model")
        or task.payload.get("llm_model")
    )


@dataclass(slots=True)
class RouterPolicy:
    """
    Build provider preference order (names), then map to ProviderState filtered by health.
    Design goals:
    - generic (tests can use arbitrary provider names)
    - allow explicit overrides (provider_hint)
    - support cloud->local preference when :cloud model requested
    """
    default_chain: List[str]

    def select_chain(self, task: TaskEnvelope, providers: Iterable[ProviderState]) -> List[ProviderState]:
        # only healthy providers
        healthy = [p for p in providers if p.healthy and p.adapter.healthcheck()]
        by_name = {p.adapter.name: p for p in healthy}
        available_names = [p.adapter.name for p in healthy]

        chain_names: List[str] = []

        # 1) explicit hint first
        if task.provider_hint:
            chain_names.append(task.provider_hint)

        # 2) cloud model hint (only if those providers exist)
        model = _requested_model(task)
        if model and str(model).endswith(":cloud"):
            chain_names += ["ollama_cloud", "ollama"]

        # 3) configured defaults next
        chain_names += self.default_chain

        # 4) finally: any remaining available providers (keeps tests working)
        chain_names += available_names

        # de-dup while preserving order, and keep only existing
        seen = set()
        uniq: List[str] = []
        for name in chain_names:
            if name and name not in seen and name in by_name:
                seen.add(name)
                uniq.append(name)

        return [by_name[n] for n in uniq]
