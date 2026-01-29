from roaudter_agent import build_default_router
from roaudter_agent.contracts import TaskEnvelope


def test_context_trace_task_roundtrip() -> None:
    router = build_default_router()

    ctx = {"trace_id": "abc", "task_id": "t1", "parent_task_id": "root", "span_id": "s1"}
    t = TaskEnvelope(
        task_id="t1",
        agent="comm",
        intent="chat",
        payload={"msg": "Say only: pong", "provider_hint": "ollama"},
        context=ctx,
    )

    res = router.route(t)
    assert res.context == ctx
