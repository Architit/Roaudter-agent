from __future__ import annotations

from typing import Any, Dict
import os

from roaudter_agent import TaskEnvelope, build_default_router


def _emit(level: str, event: str, msg: str, **fields: Any) -> None:
    """
    Try ecosystem logger (LAM) if available; otherwise fallback to a simple print.
    """
    try:
        from lam_logging import log  # type: ignore
        log(level, event, msg, **fields)
        return
    except Exception:
        # minimal fallback, still grep-friendly
        print(f"[{event}] level={level} msg={msg} fields={fields}")


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
            context=payload.get("context"),
            constraints=payload.get("constraints", {}),
            provider_hint=payload.get("provider_hint"),
        )

        res = self.router.route(task)

        # optional runtime trace: export ROAUDTER_TRACE=1
        
        def _trace_should_log(mode: str, reply: dict) -> bool:
            mode = (mode or "nonok").lower()
            status = res.status
            attempts = int(res.attempts or 0)
            errors = res.errors or []
            if mode == "all":
                return True
            if mode == "errors":
                return bool(errors)
            if mode == "retries":
                return attempts > 1
            # default + "nonok"
            return status != "ok"

        if os.getenv("ROAUDTER_TRACE") == "1":
            mode = os.getenv("ROAUDTER_TRACE_ONLY", "nonok").lower()
            reply_dict = {
                "status": res.status,
                "provider_used": res.provider_used,
                "latency_ms": res.latency_ms,
                "attempts": res.attempts,
                "selected_chain": res.selected_chain,
                "errors": res.errors,
                "tokens": res.tokens,
                "usage": res.usage,
                "metrics": {
                    "provider_used": res.provider_used,
                    "latency_ms": res.latency_ms,
                    "attempts": res.attempts,
                    "selected_chain": res.selected_chain,
                    "tokens": res.tokens,
                    "usage": res.usage,
                },
                "context": res.context,
                "task_id": res.task_id,
                "provider_hint": task.provider_hint,
            }
            if _trace_should_log(mode, reply_dict):
                _emit("info", "roaudter.trace", "route_summary", **reply_dict)


        # Observability: reply delivered back to comm-agent layer
        ctx = res.context if isinstance(res.context, dict) else {}
        _emit(
            "info",
            "roaudter.deliver",
            "deliver",
            recipient=task.agent,
            status=res.status,
            provider_used=res.provider_used,
            latency_ms=res.latency_ms,
            attempts=res.attempts,
            task_id=res.task_id,
            trace_id=ctx.get("trace_id"),
            parent_task_id=ctx.get("parent_task_id"),
            span_id=ctx.get("span_id"),
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
            "metrics": {
                "provider_used": res.provider_used,
                "latency_ms": res.latency_ms,
                "attempts": res.attempts,
                "selected_chain": res.selected_chain,
                "tokens": res.tokens,
                "usage": res.usage,
            },
            "context": res.context,
            "taskarid": payload.get("taskarid"),
            "result": res.result,
            "error": res.error,
        }
