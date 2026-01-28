from __future__ import annotations
from dataclasses import dataclass
from typing import List

from roaudter_agent.policy import RouterPolicy
from roaudter_agent.router import RouterAgent
from roaudter_agent.providers.base import ProviderState
from roaudter_agent.providers.ollama import OllamaAdapter
from roaudter_agent.providers.openai import OpenAIAdapter


@dataclass(slots=True)
class ProviderConfig:
    ollama_base_url: str = "http://172.31.80.1:11434"
    ollama_local_model: str = "llama3.2:1b"
    ollama_cloud_model: str = "glm-4.7:cloud"

    openai_model: str = "gpt-4o-mini"


def build_default_router(cfg: ProviderConfig | None = None) -> RouterAgent:
    cfg = cfg or ProviderConfig()

    providers: List[ProviderState] = [
        # OpenAI (если нет ключа, healthcheck вернет False и монитор отфильтрует)
        ProviderState(OpenAIAdapter(default_model=cfg.openai_model)),

        # Локальная Ollama (всегда доступна в твоей схеме)
        ProviderState(OllamaAdapter(name="ollama", base_url=cfg.ollama_base_url, default_model=cfg.ollama_local_model)),

        # Cloud Ollama (опционально)
        ProviderState(OllamaAdapter(name="ollama_cloud", base_url=cfg.ollama_base_url, default_model=cfg.ollama_cloud_model)),
    ]

    # По умолчанию: openai → local ollama → cloud
    policy = RouterPolicy(default_chain=["openai", "ollama", "ollama_cloud"])
    return RouterAgent(policy=policy, providers=providers)
