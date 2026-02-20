from __future__ import annotations

from roaudter_agent.contracts import ResultEnvelope
from roaudter_agent.lam_entrypoint import RoaudterComAgent


class _FakeRouter:
    def route(self, task):
        assert task.provider_hint == "local_only"
        assert task.context.get("trace_id") == "tr-1"
        assert task.context.get("task_id") == "t42"
        return ResultEnvelope(
            task_id=task.task_id,
            status="ok",
            context=task.context,
            provider_used="ollama",
            latency_ms=3,
            attempts=1,
            selected_chain=["ollama", "openai"],
            errors=[],
            tokens=7,
            usage={"total_tokens": 7},
            result={"text": "pong"},
        )


def test_answer_returns_transport_contract(monkeypatch):
    monkeypatch.setattr(
        "roaudter_agent.lam_entrypoint.build_default_router",
        lambda: _FakeRouter(),
    )

    agent = RoaudterComAgent()
    reply = agent.answer(
        {
            "task_id": "t42",
            "taskarid": "legacy-42",
            "agent": "comm-agent",
            "intent": "chat",
            "provider_hint": "local_only",
            "payload": {"msg": "ping"},
            "context": {"trace_id": "tr-1"},
        }
    )

    assert reply["task_id"] == "t42"
    assert reply["status"] == "ok"
    assert reply["provider_used"] == "ollama"
    assert reply["attempts"] == 1
    assert reply["result"] == {"text": "pong"}
    assert reply["taskarid"] == "legacy-42"
