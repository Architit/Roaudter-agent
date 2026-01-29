from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Optional

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.providers.base import ProviderState


def _requested_model(task: TaskEnvelope) -> str | None:
    return (
        task.constraints.get("model")
        or task.payload.get("model")
        or task.payload.get("llm_model")
    )


def _hint(task: TaskEnvelope) -> Optional[str]:
    # allow hint to come either from TaskEnvelope or payload
    return (task.provider_hint or task.payload.get("provider_hint") or "").strip().lower() or None


PROFILE_CHAINS: dict[str, list[str]] = {
    # strict local: never use paid APIs
    "local_only": ["ollama"],

    # cheap: start local, then generally low-cost, then others
    "cheap": ["ollama", "gemini", "openai", "claude", "grok", "deepseek", "ollama_cloud"],

    # best: prioritize higher quality (subjective, but practical default)
    "best": ["claude", "openai", "gemini", "grok", "deepseek", "ollama", "ollama_cloud"],

    # fast: prioritize low-latency models (default assumptions)
    "fast": ["gemini", "openai", "ollama", "claude", "grok", "deepseek", "ollama_cloud"],
}


@dataclass(slots=True)
class RouterPolicy:
    """
    Policy v2 + profiles:
    - provider_hint can be:
        - exact provider name (e.g., "openai")
        - profile name: local_only/cheap/best/fast
    - model=:cloud => prefer ollama_cloud then ollama (but profiles can override via order)
    - health filtering happens outside (HealthMonitor)
    """
    default_chain: List[str]

    def select_chain(self, task: TaskEnvelope, providers: Iterable[ProviderState]) -> List[ProviderState]:
        available = list(providers)
        by_name = {p.adapter.name: p for p in available}
        available_names = [p.adapter.name for p in available]

        chain: List[str] = []

        # 1) hint/profile first
        hint = _hint(task)
        if hint:
            if hint in PROFILE_CHAINS:
                chain += PROFILE_CHAINS[hint]
            else:
                # treat as explicit provider name
                chain.append(hint)

        # 2) model-driven ordering (cloud request -> cloud then local)
        model = _requested_model(task)
        if model and str(model).endswith(":cloud"):
            chain += ["ollama_cloud", "ollama"]

        # 3) intent heuristic (light touch; profiles/hints come first anyway)
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
