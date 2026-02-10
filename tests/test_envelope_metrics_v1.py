from roaudter_agent import build_default_router
from roaudter_agent.contracts import TaskEnvelope


def test_result_envelope_metrics_present_v1() -> None:
    r = build_default_router()
    t = TaskEnvelope(task_id="t1", agent="comm", intent="chat", payload={"msg": "ping"})
    res = r.route(t)

    assert isinstance(res.metrics, dict)
    assert "latency_ms" in res.metrics
    assert "attempts" in res.metrics
    assert "selected_chain" in res.metrics
