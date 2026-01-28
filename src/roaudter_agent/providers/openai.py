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
class OpenAIAdapter:
    name: str = "openai"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o-mini"

    def _api_key(self) -> Optional[str]:
        return os.environ.get(self.api_key_env)

    def healthcheck(self) -> bool:
        # Не делаем сетевой healthcheck (дорого/лимиты). Достаточно наличия ключа.
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
            "messages": [{"role": "user", "content": msg}],
            "temperature": task.constraints.get("temperature", 0.2),
        }

        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8")
                data = json.loads(raw)
        except urllib.error.HTTPError as e:
            # 401/403: ключ/доступ; 429: rate limit; 5xx: transient
            retryable = e.code in (429, 500, 502, 503, 504)
            code = "rate_limited" if e.code == 429 else "http_error"
            raise ProviderError(
                f"openai call failed: HTTP {e.code} {e.reason}",
                code=code,
                http_status=e.code,
                retryable=retryable,
                meta={"model": model},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"openai call failed: {e}",
                code="network_error",
                retryable=True,
                meta={"model": model},
            ) from e

        text = None
        try:
            text = data["choices"][0]["message"]["content"]
        except Exception:
            pass

        usage = data.get("usage")
        return {
            "provider": "openai",
            "model": model,
            "latency_ms": int((time.time() - t0) * 1000),
            "text": text,
            "usage": usage,
            "raw": data,
        }
