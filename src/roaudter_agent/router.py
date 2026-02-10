from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from roaudter_agent.contracts import TaskEnvelope, ResultEnvelope
from roaudter_agent.health import HealthMonitor
from roaudter_agent.policy import RouterPolicy
from roaudter_agent.providers.base import ProviderError, ProviderState


def _emit(level: str, event: str, msg: str, **fields) -> None:
    """Best-effort structured logging.
    Uses LAM's lam_logging if available; otherwise no-ops (keeps noise minimal).
    """
    try:
        from lam_logging import log  # type: ignore
        log(level, event, msg, **fields)
    except Exception:
        return


@dataclass(slots=True)
class RouterAgent:
    policy: RouterPolicy
    providers: list[ProviderState]
    health: HealthMonitor = field(default_factory=HealthMonitor)

    # retry/backoff budget (v1)
# - retries only when ProviderError.retryable==True AND http_status in {None, 429, >=500}
# - bounded by retry_max_attempts and retry_budget_ms
# - falls back to next provider after exhaustion
# defaults are tiny to keep tests fast / WSL-friendly
    retry_max_attempts: int = 3
    retry_budget_ms: int = 800
    retry_base_backoff_ms: int = 10
    retry_max_backoff_ms: int = 80

    def route(self, task: TaskEnvelope) -> ResultEnvelope:
        start = time.time()

        # Observability: routing start (filtered by LAM_LOG_LEVEL/LAM_LOG_EVENTS)
        ctx = task.context or (task.payload.get("context") if isinstance(task.payload, dict) else None)
        if not isinstance(ctx, dict):
            ctx = {}
        _emit(
            "info",
            "roaudter.route",
            "route",
            intent=task.intent,
            task_id=task.task_id,
            trace_id=ctx.get("trace_id"),
            parent_task_id=ctx.get("parent_task_id"),
            span_id=ctx.get("span_id"),
        )

        # health filter with TTL/cooldown
        healthy_providers = [p for p in self.providers if p.healthy and self.health.is_healthy(p)]
        chain = self.policy.select_chain(task, healthy_providers)

        selected_chain = [ps.adapter.name for ps in chain]
        attempts = 0
        errors: list[dict] = []

        last_err: Optional[dict] = None

        for p in chain:
            attempt = 0

            while True:
                try:
                    attempts += 1
                    out = p.adapter.generate(task)

                    # unified usage/tokens: lift provider-native usage to envelope level
                    usage = out.get("usage") if isinstance(out, dict) else None
                    if not isinstance(usage, dict):
                        usage = None

                    tokens = None
                    if usage:
                        tokens = (
                            usage.get("total_tokens")
                            or usage.get("total")
                            or usage.get("tokens")
                        )
                        if tokens is None:
                            pt = usage.get("prompt_tokens")
                            ct = usage.get("completion_tokens")
                            if isinstance(pt, int) and isinstance(ct, int):
                                tokens = pt + ct

                    latency_ms = int((time.time() - start) * 1000)
                    _emit(
                        "info",
                        "roaudter.result",
                        "ok",
                        status="ok",
                        provider_used=p.adapter.name,
                        latency_ms=latency_ms,
                        attempts=attempts,
                        task_id=task.task_id,
                        trace_id=ctx.get("trace_id"),
                    )
                    return ResultEnvelope(
                        task_id=task.task_id,
                        context=(task.context or task.payload.get("context")),
                        metrics={
                            "provider_used": p.adapter.name,
                            "latency_ms": latency_ms,
                            "attempts": attempts,
                            "selected_chain": selected_chain,
                            "tokens": tokens,
                            "usage": usage,
                        },
                        status="ok",
                        provider_used=p.adapter.name,
                        latency_ms=latency_ms,
                        attempts=attempts,
                        selected_chain=selected_chain,
                        errors=errors,
                        tokens=tokens,
                        usage=usage,
                        result=out,
                    )

                except ProviderError as e:
                    last_err = e.to_dict(provider=p.adapter.name)
                    errors.append(last_err)

                    # retry only if explicitly retryable AND status is transient
                    status = e.http_status
                    transient = (status is None) or (status == 429) or (isinstance(status, int) and status >= 500)
                    if (not e.retryable) or (not transient):
                        break

                    attempt += 1
                    if attempt >= self.retry_max_attempts:
                        break

                    elapsed_ms = int((time.time() - start) * 1000)
                    if elapsed_ms >= self.retry_budget_ms:
                        break

                    # small exponential backoff (tiny for fast tests)
                    backoff_ms = min(
                        self.retry_base_backoff_ms * (2 ** (attempt - 1)),
                        self.retry_max_backoff_ms,
                    )
                    remaining_ms = self.retry_budget_ms - elapsed_ms
                    if remaining_ms <= 0:
                        break

                    time.sleep(min(backoff_ms, remaining_ms) / 1000.0)
                    continue

            # exhausted this provider -> try next provider in chain
            continue

        latency_ms = int((time.time() - start) * 1000)
        ctx = task.context or (task.payload.get("context") if isinstance(task.payload, dict) else None)
        if not isinstance(ctx, dict):
            ctx = {}
        _emit(
            "info",
            "roaudter.result",
            "error",
            status="error",
            provider_used=None,
            latency_ms=latency_ms,
            attempts=attempts,
            task_id=task.task_id,
            trace_id=ctx.get("trace_id"),
        )
        return ResultEnvelope(
            task_id=task.task_id,
            context=(task.context or task.payload.get("context")),
            metrics={
                "provider_used": None,
                "latency_ms": latency_ms,
                "attempts": attempts,
                "selected_chain": selected_chain,
                "tokens": None,
                "usage": None,
            },
            status="error",
            provider_used=None,
            latency_ms=latency_ms,
            attempts=attempts,
            selected_chain=selected_chain,
            errors=errors,
            error=last_err or {
                "provider": None,
                "code": "no_healthy_providers",
                "http_status": None,
                "retryable": False,
                "message": "no healthy providers",
                "meta": {},
            },
        )
