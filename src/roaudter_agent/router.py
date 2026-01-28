from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from roaudter_agent.contracts import TaskEnvelope, ResultEnvelope
from roaudter_agent.policy import RouterPolicy
from roaudter_agent.providers.base import ProviderError, ProviderState


@dataclass(slots=True)
class RouterAgent:
    policy: RouterPolicy
    providers: list[ProviderState]

    def route(self, task: TaskEnvelope) -> ResultEnvelope:
        start = time.time()
        chain = self.policy.select_chain(task, self.providers)

        last_err: Optional[str] = None
        for p in chain:
            try:
                out: Any = p.adapter.generate(task)
                latency_ms = int((time.time() - start) * 1000)
                return ResultEnvelope(
                    task_id=task.task_id,
                    status="ok",
                    provider_used=p.adapter.name,
                    latency_ms=latency_ms,
                    result=out,
                )
            except ProviderError as e:
                last_err = f"{p.adapter.name}: {e}"
                continue

        latency_ms = int((time.time() - start) * 1000)
        return ResultEnvelope(
            task_id=task.task_id,
            status="error",
            provider_used=None,
            latency_ms=latency_ms,
            error=last_err or "no healthy providers",
        )
