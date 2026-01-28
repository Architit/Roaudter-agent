from __future__ import annotations
import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.providers.base import ProviderError


@dataclass(slots=True)
class OllamaAdapter:
    name: str = "ollama"
    base_url: str = "http://172.31.80.1:11434"

    def healthcheck(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2) as r:
                return 200 <= r.status < 300
        except Exception:
            return False

    def generate(self, task: TaskEnvelope) -> Any:
        # пока заглушка: позже подключим /v1/chat/completions или /api/generate
        msg = task.payload.get("msg") or task.payload.get("text") or ""
        if not msg:
            raise ProviderError("empty payload.msg/text")
        return {"provider": "ollama", "echo": msg}
