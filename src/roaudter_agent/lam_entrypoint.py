from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone
import os
import uuid

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


def _set_ctx_best_effort(ctx: Any) -> None:
    """Best-effort: if running inside LAM, populate lam_logging ContextVar."""
    if not isinstance(ctx, dict) or not ctx:
        return
    try:
        from lam_logging import set_context  # type: ignore
        set_context(
            trace_id=ctx.get("trace_id"),
            task_id=ctx.get("task_id"),
            parent_task_id=ctx.get("parent_task_id"),
            span_id=ctx.get("span_id"),
        )
    except Exception:
        return


def _normalize_payload_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    ctx = payload.get("context")
    if not isinstance(ctx, dict):
        ctx = {}

    trace_id = ctx.get("trace_id") or payload.get("trace_id") or uuid.uuid4().hex
    task_id = ctx.get("task_id") or payload.get("task_id") or f"t_{uuid.uuid4().hex[:12]}"
    parent_task_id = ctx.get("parent_task_id") or payload.get("parent_task_id")
    span_id = ctx.get("span_id") or payload.get("span_id")

    ctx["trace_id"] = trace_id
    ctx["task_id"] = task_id
    if parent_task_id is not None:
        ctx["parent_task_id"] = parent_task_id
    if span_id is not None:
        ctx["span_id"] = span_id

    payload["context"] = ctx
    payload["task_id"] = task_id
    return ctx


def _emit_memory_trace_best_effort(
    *,
    ctx: Dict[str, Any],
    task: TaskEnvelope,
    result: Dict[str, Any],
) -> None:
    if os.getenv("ROAUDTER_MEMORY_TRACE", "").strip() != "1":
        return

    try:
        from src.memory_time_manager import MemoryTimeManager  # type: ignore
    except Exception:
        return

    trace_id = ctx.get("trace_id")
    task_id = ctx.get("task_id")
    if not trace_id or not task_id:
        return

    try:
        manager = MemoryTimeManager()
        manager.add_event_memory(
            {
                "name": "roaudter_delivery",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content": {
                    "status": result.get("status"),
                    "provider_used": result.get("provider_used"),
                    "attempts": result.get("attempts"),
                },
                "associations": [str(trace_id), str(task_id)],
                "tags": ["roaudter", "trace", "delivery"],
                "attributes": {
                    "trace_id": str(trace_id),
                    "task_id": str(task_id),
                    "parent_task_id": ctx.get("parent_task_id"),
                    "span_id": ctx.get("span_id"),
                    "intent": task.intent,
                },
            }
        )
    except Exception:
        return


class RoaudterComAgent:
    """
    LAM/comm-agent compatibility layer.
    comm-agent calls: agent.answer(payload_dict) -> reply_dict
    """

    def __init__(self) -> None:
        self.router = build_default_router()

    def answer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(payload or {})
        normalized_ctx = _normalize_payload_context(payload)
        _set_ctx_best_effort(normalized_ctx)
        task = TaskEnvelope(
            task_id=normalized_ctx["task_id"],
            agent=payload.get("agent", "comm-agent"),
            intent=payload.get("intent", "chat"),
            priority=payload.get("priority", 0),
            payload=payload.get("payload", {"msg": payload.get("msg", "")}),
            context=normalized_ctx,
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
                "metrics": dict(res.metrics or {}),
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

        reply = {
            "task_id": res.task_id,
            "status": res.status,
            "provider_used": res.provider_used,
            "latency_ms": res.latency_ms,
            "attempts": res.attempts,
            "selected_chain": res.selected_chain,
            "errors": res.errors,
            "tokens": res.tokens,
            "usage": res.usage,
            "metrics": dict(res.metrics or {}),
            "context": res.context,
            "taskarid": payload.get("taskarid"),
            "result": res.result,
            "error": res.error,
        }
        _emit_memory_trace_best_effort(ctx=ctx, task=task, result=reply)
        return reply
