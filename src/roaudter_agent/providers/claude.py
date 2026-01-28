from __future__ import annotations
import json
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Optional

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.providers.base import ProviderError


@dataclass(slots=True)
class ClaudeAdapter:
    """
    Anthropic Messages API.
    Auth: ANTHROPIC_API_KEY via header x-api-key
    Endpoint: POST https://api.anthropic.com/v1/messages
    """
    name: str = "claude"
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str = "https://api.anthropic.com/v1"
    default_model: str = "claude-3-5-haiku-latest"
    anthropic_version: str = "2023-06-01"

    def _api_key(self) -> Optional[str]:
        return os.environ.get(self.api_key_env)

    def healthcheck(self) -> bool:
        # Avoid network calls; key presence is enough to enable.
        return bool(self._api_key())

    def generate(self, task: TaskEnvelope) -> Any:
        api_key = self._api_key()
        if not api_key:
            raise ProviderError(
                f"missing env {self.api_key_env}",
                code="missing_api_key",
                retryable=False,
                meta={"env": self.api_key_env},
            )

        msg = task.payload.get("msg") or task.payload.get("text") or ""
        if not msg:
            raise ProviderError("empty payload.msg/text", code="bad_request", retryable=False)

        model = (
            task.constraints.get("model")
            or task.payload.get("model")
            or task.payload.get("llm_model")
            or self.default_model
        )

        body = {
            "model": model,
            "max_tokens": int(task.constraints.get("max_tokens", 256)),
            "messages": [{"role": "user", "content": msg}],
        }

        req = urllib.request.Request(
            url=f"{self.base_url}/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": self.anthropic_version,
            },
            method="POST",
        )

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8")
                data = json.loads(raw)
        except urllib.error.HTTPError as e:
            retryable = e.code in (429, 500, 502, 503, 504)
            code = "rate_limited" if e.code == 429 else "http_error"
            raise ProviderError(
                f"claude call failed: HTTP {e.code} {e.reason}",
                code=code,
                http_status=e.code,
                retryable=retryable,
                meta={"model": model},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"claude call failed: {e}",
                code="network_error",
                retryable=True,
                meta={"model": model},
            ) from e

        # Extract text
        text = None
        try:
            # Typically: {"content":[{"type":"text","text":"..."}], ...}
            parts = data.get("content") or []
            if parts and isinstance(parts, list):
                text = parts[0].get("text")
        except Exception:
            pass

        usage = data.get("usage")
        return {
            "provider": "claude",
            "model": model,
            "latency_ms": int((time.time() - t0) * 1000),
            "text": text,
            "usage": usage,
            "raw": data,
        }
