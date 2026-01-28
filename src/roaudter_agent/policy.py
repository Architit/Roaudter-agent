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
    Policy v2:
    - Generic (tests can use arbitrary provider names)
    - provider_hint first
    - if model endswith ':cloud' => prefer ollama_cloud then ollama
    - otherwise preference by intent/priority (extend later)
    NOTE: Health filtering is done outside (HealthMonitor); policy does NOT call healthcheck.
    """
    default_chain: List[str]

    def select_chain(self, task: TaskEnvelope, providers: Iterable[ProviderState]) -> List[ProviderState]:
        available = list(providers)
        by_name = {p.adapter.name: p for p in available}
        available_names = [p.adapter.name for p in available]

        chain: List[str] = []

        # 1) explicit hint first
        if task.provider_hint:
            chain.append(task.provider_hint)

        # 2) model-driven ordering (cloud request -> cloud then local)
        model = _requested_model(task)
        if model and str(model).endswith(":cloud"):
            chain += ["ollama_cloud", "ollama"]

        # 3) intent/priority heuristics (starter rules; can evolve)
        intent = (task.intent or "").lower()
        if intent in {"code", "coding", "patch"}:
            chain += ["openai", "ollama"]
        else:
            chain += ["ollama", "openai"]

        # 4) configured defaults next
        chain += self.default_chain

        # 5) finally: any remaining available providers
        chain += available_names

        # de-dup while preserving order, keep only existing
        seen = set()
        uniq: List[str] = []
        for name in chain:
            if name and name not in seen and name in by_name:
                seen.add(name)
                uniq.append(name)

        return [by_name[n] for n in uniq]
