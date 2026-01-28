from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict

from roaudter_agent import TaskEnvelope, build_default_router


class RoaudterComAgent:
    """
    LAM/comm-agent compatibility layer.
    comm-agent calls: agent.answer(payload_dict) -> reply_dict
    """
    def __init__(self) -> None:
        self.router = build_default_router()

    def answer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = TaskEnvelope(
            task_id=payload.get("task_id", "t1"),
            agent=payload.get("agent", "comm-agent"),
            intent=payload.get("intent", "chat"),
            priority=payload.get("priority", 0),
            payload=payload.get("payload", {"msg": payload.get("msg", "")}),
            constraints=payload.get("constraints", {}),
            provider_hint=payload.get("provider_hint"),
        )

        res = self.router.route(task)
        return {
            "task_id": res.task_id,
            "status": res.status,
            "provider_used": res.provider_used,
            "latency_ms": res.latency_ms,
            "tokens": res.tokens,
            "result": res.result,
            "error": res.error,
        }
