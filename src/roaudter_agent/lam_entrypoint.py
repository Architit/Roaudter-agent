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
            constraints=payload.get("constraints", {}),
            provider_hint=payload.get("provider_hint"),
        )

        res = self.router.route(task)

        # optional runtime trace: export ROAUDTER_TRACE=1
        if os.getenv("ROAUDTER_TRACE") == "1":
            mode = os.getenv("ROAUDTER_TRACE_ONLY", "nonok").lower()
            errors_n = len(res.errors or [])
            attempts_n = (res.attempts or 0)

            if mode == "errors":
                should_print = errors_n > 0
            elif mode == "retries":
                should_print = attempts_n > 1
            elif mode == "nonok":
                should_print = (res.status != "ok") or errors_n > 0 or attempts_n > 1
            else:  # "all"
                should_print = True

            if should_print:
                last = (res.errors[-1] if res.errors else None)
                last_s = None
                if isinstance(last, dict):
                    last_s = {
                        "provider": last.get("provider"),
                        "code": last.get("code"),
                        "http_status": last.get("http_status"),
                    }

                # map to levels (noise control)
                level = "info"
                if res.status != "ok":
                    level = "error"
                elif errors_n > 0 or attempts_n > 1:
                    level = "warn"

                _emit(
                    level,
                    "roaudter",
                    "route",
                    status=res.status,
                    provider=res.provider_used,
                    attempts=attempts_n,
                    intent=task.intent,
                    hint=task.provider_hint,
                    chain=res.selected_chain,
                    errors=errors_n,
                    last_err=last_s,
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
            "context": payload.get("context"),
            "taskarid": payload.get("taskarid"),
            "result": res.result,
            "error": res.error,
        }
