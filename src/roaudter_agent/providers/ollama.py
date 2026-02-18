from __future__ import annotations
import json
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.providers.base import ProviderError


@dataclass(slots=True)
class OllamaAdapter:
    name: str = "ollama"
    base_url: str = "http://172.31.80.1:11434"
    default_model: str = "llama3.2:1b"  # локальная по умолчанию

    @staticmethod
    def _offline_test_mode() -> bool:
        return os.getenv("ROAUDTER_OFFLINE_TEST_MODE", "").strip() == "1"

    def healthcheck(self) -> bool:
        if self._offline_test_mode():
            return True
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2) as r:
                return 200 <= r.status < 300
        except Exception:
            return False

    def generate(self, task: TaskEnvelope) -> Any:
        msg = task.payload.get("msg") or task.payload.get("text") or ""
        if not msg:
            raise ProviderError("empty payload.msg/text", code="bad_request", retryable=False)

        requested_model = (
            task.constraints.get("model")
            or task.payload.get("model")
            or task.payload.get("llm_model")
        )

        # Provider-aware model selection:
        # - local adapter ("ollama") must NOT use *:cloud requests
        # - cloud adapter ("ollama_cloud") should prefer *:cloud requests
        if self.name == "ollama" and requested_model and str(requested_model).endswith(":cloud"):
            model = self.default_model
        elif self.name == "ollama_cloud" and requested_model and not str(requested_model).endswith(":cloud"):
            model = self.default_model
        else:
            model = requested_model or self.default_model

        body = {
            "model": model,
            "messages": [{"role": "user", "content": msg}],
            "temperature": task.constraints.get("temperature", 0.2),
        }

        if self._offline_test_mode():
            return {
                "provider": "ollama",
                "model": model,
                "latency_ms": 1,
                "text": "pong",
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                "raw": {"mode": "offline_test"},
            }

        req = urllib.request.Request(
            url=f"{self.base_url}/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        # retry только для "временных" 429/сетевых (но не для cloud-квоты)
        backoffs = [0.2, 0.6, 1.5]
        last_exc: Exception | None = None

        for i, delay in enumerate([0.0] + backoffs):
            if delay:
                time.sleep(delay)

            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    raw = r.read().decode("utf-8")
                    data = json.loads(raw)

                content = None
                try:
                    content = data["choices"][0]["message"]["content"]
                except Exception:
                    pass

                return {
                    "provider": "ollama",
                    "model": model,
                    "latency_ms": int((time.time() - t0) * 1000),
                    "text": content,
                    "raw": data,
                }

            except urllib.error.HTTPError as e:
                # Cloud лимит — НЕ ретраим, сразу отдаём структурированную ошибку
                if e.code == 429 and str(model).endswith(":cloud"):
                    raise ProviderError(
                        "ollama cloud quota exhausted",
                        code="quota_exhausted",
                        http_status=429,
                        retryable=False,
                        meta={"model": model},
                    ) from e

                # обычный 429 может быть “server busy” → ретрай
                if e.code == 429 and i < len(backoffs):
                    last_exc = e
                    continue

                raise ProviderError(
                    f"ollama v1 call failed: HTTP {e.code} {e.reason}",
                    code="http_error",
                    http_status=e.code,
                    retryable=False,
                    meta={"model": model},
                ) from e

            except Exception as e:
                last_exc = e
                if i < len(backoffs):
                    continue
                raise ProviderError(
                    f"ollama v1 call failed: {e}",
                    code="network_error",
                    retryable=True,
                    meta={"model": model},
                ) from e

        raise ProviderError(
            f"ollama v1 call failed: {last_exc}",
            code="unknown_error",
            retryable=False,
            meta={"model": model},
        )
