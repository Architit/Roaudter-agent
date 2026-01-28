from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

from roaudter_agent.policy import RouterPolicy
from roaudter_agent.router import RouterAgent
from roaudter_agent.providers.base import ProviderState
from roaudter_agent.providers.ollama import OllamaAdapter


@dataclass(slots=True)
class ProviderConfig:
    ollama_base_url: str = "http://172.31.80.1:11434"


def build_default_router(cfg: ProviderConfig | None = None) -> RouterAgent:
    cfg = cfg or ProviderConfig()

    providers: List[ProviderState] = [
        ProviderState(OllamaAdapter(base_url=cfg.ollama_base_url)),
        # TODO: OpenAIAdapter, GeminiAdapter, ClaudeAdapter, etc
    ]

    policy = RouterPolicy(default_chain=["ollama"])
    return RouterAgent(policy=policy, providers=providers)
