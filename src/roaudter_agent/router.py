from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional

from roaudter_agent.contracts import TaskEnvelope, ResultEnvelope
from roaudter_agent.health import HealthMonitor
from roaudter_agent.policy import RouterPolicy
from roaudter_agent.providers.base import ProviderError, ProviderState


@dataclass(slots=True)
class RouterAgent:
    policy: RouterPolicy
    providers: list[ProviderState]
    health: HealthMonitor = field(default_factory=HealthMonitor)

    def route(self, task: TaskEnvelope) -> ResultEnvelope:
        start = time.time()

        # health filter with TTL/cooldown
        healthy_providers = [p for p in self.providers if p.healthy and self.health.is_healthy(p)]
        chain = self.policy.select_chain(task, healthy_providers)

        last_err: Optional[dict] = None

        for p in chain:
            try:
                out = p.adapter.generate(task)
                latency_ms = int((time.time() - start) * 1000)
                return ResultEnvelope(
                    task_id=task.task_id,
                    status="ok",
                    provider_used=p.adapter.name,
                    latency_ms=latency_ms,
                    result=out,
                )
            except ProviderError as e:
                last_err = e.to_dict(provider=p.adapter.name)
                continue

        latency_ms = int((time.time() - start) * 1000)
        return ResultEnvelope(
            task_id=task.task_id,
            status="error",
            provider_used=None,
            latency_ms=latency_ms,
            error=last_err or {
                "provider": None,
                "code": "no_healthy_providers",
                "http_status": None,
                "retryable": False,
                "message": "no healthy providers",
                "meta": {},
            },
        )
