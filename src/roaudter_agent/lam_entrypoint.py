from __future__ import annotations

from typing import Any, Dict
import os

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

        # optional runtime trace: export ROAUDTER_TRACE=1
        if os.getenv("ROAUDTER_TRACE") == "1":
            mode = os.getenv("ROAUDTER_TRACE_ONLY", "nonok").lower()
            errors_n = len(res.errors or [])
            should_print = True
            if mode == "errors":
                should_print = errors_n > 0
            elif mode == "retries":
                should_print = (res.attempts or 0) > 1
            elif mode == "nonok":
                should_print = (res.status != "ok") or errors_n > 0 or (res.attempts or 0) > 1
            elif mode == "all":
                should_print = True
            if not should_print:
                return {
                    "task_id": res.task_id,
                    "status": res.status,
                    "provider_used": res.provider_used,
                    "latency_ms": res.latency_ms,
                    "attempts": res.attempts,
                    "selected_chain": res.selected_chain,
                    "errors": res.errors,
                    "tokens": res.tokens,
                    "usage": res.usage,
                    "result": res.result,
                    "error": res.error,
                }
            last = (res.errors[-1] if res.errors else None)
            last_s = None
            if isinstance(last, dict):
                last_s = {
                    "provider": last.get("provider"),
                    "code": last.get("code"),
                    "http_status": last.get("http_status"),
                }
            print(
                "[roaudter] status=%s provider=%s attempts=%s intent=%s hint=%s chain=%s last_err=%s"
                % (
                    res.status,
                    res.provider_used,
                    res.attempts,
                    task.intent,
                    task.provider_hint,
                    res.selected_chain,
                    last_s,
                )
            )

        return {
            "task_id": res.task_id,
            "status": res.status,
            "provider_used": res.provider_used,
            "latency_ms": res.latency_ms,
            "attempts": res.attempts,
            "selected_chain": res.selected_chain,
            "errors": res.errors,
            "tokens": res.tokens,
            "usage": res.usage,
            "result": res.result,
            "error": res.error,
        }
