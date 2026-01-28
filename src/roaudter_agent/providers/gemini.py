from __future__ import annotations
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Optional

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.providers.base import ProviderError


@dataclass(slots=True)
class GeminiAdapter:
    """
    Uses Google Generative Language API (Gemini).
    Auth: GEMINI_API_KEY (query param key=...)
    Endpoint (widely supported): /v1beta/models/{model}:generateContent
    """
    name: str = "gemini"
    api_key_env: str = "GEMINI_API_KEY"
    base_url: str = "https://generativelanguage.googleapis.com"
    default_model: str = "gemini-1.5-flash"

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

        # Gemini generateContent format
        body = {
            "contents": [{"role": "user", "parts": [{"text": msg}]}],
        }

        qs = urllib.parse.urlencode({"key": api_key})
        url = f"{self.base_url}/v1beta/models/{model}:generateContent?{qs}"

        req = urllib.request.Request(
            url=url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
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
                f"gemini call failed: HTTP {e.code} {e.reason}",
                code=code,
                http_status=e.code,
                retryable=retryable,
                meta={"model": model},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"gemini call failed: {e}",
                code="network_error",
                retryable=True,
                meta={"model": model},
            ) from e

        # Extract text
        text = None
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            pass

        return {
            "provider": "gemini",
            "model": model,
            "latency_ms": int((time.time() - t0) * 1000),
            "text": text,
            "raw": data,
        }
