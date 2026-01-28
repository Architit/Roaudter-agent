from __future__ import annotations
from dataclasses import dataclass
from typing import List

from roaudter_agent.policy import RouterPolicy
from roaudter_agent.router import RouterAgent
from roaudter_agent.providers.base import ProviderState
from roaudter_agent.providers.ollama import OllamaAdapter
from roaudter_agent.providers.openai import OpenAIAdapter
from roaudter_agent.providers.gemini import GeminiAdapter
from roaudter_agent.providers.claude import ClaudeAdapter
from roaudter_agent.providers.grok import GrokAdapter


@dataclass(slots=True)
class ProviderConfig:
    ollama_base_url: str = "http://172.31.80.1:11434"
    ollama_local_model: str = "llama3.2:1b"
    ollama_cloud_model: str = "glm-4.7:cloud"

    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-1.5-flash"
    claude_model: str = "claude-3-5-haiku-latest"
    grok_model: str = "grok-2-latest"


def build_default_router(cfg: ProviderConfig | None = None) -> RouterAgent:
    cfg = cfg or ProviderConfig()

    providers: List[ProviderState] = [
        ProviderState(GrokAdapter(default_model=cfg.grok_model)),
        ProviderState(ClaudeAdapter(default_model=cfg.claude_model)),
        ProviderState(GeminiAdapter(default_model=cfg.gemini_model)),
        ProviderState(OpenAIAdapter(default_model=cfg.openai_model)),
        ProviderState(OllamaAdapter(name="ollama", base_url=cfg.ollama_base_url, default_model=cfg.ollama_local_model)),
        ProviderState(OllamaAdapter(name="ollama_cloud", base_url=cfg.ollama_base_url, default_model=cfg.ollama_cloud_model)),
    ]

    policy = RouterPolicy(default_chain=["grok", "claude", "gemini", "openai", "ollama", "ollama_cloud"])
    return RouterAgent(policy=policy, providers=providers)
