from roaudter_agent.contracts import ResultEnvelope
from roaudter_agent.lam_entrypoint import RoaudterComAgent


class _FakeRouter:
    def route(self, _task):  # type: ignore[no-untyped-def]
        return ResultEnvelope(
            task_id="t1",
            status="ok",
            context={"trace_id": "abc", "task_id": "t1"},
            metrics={"sentinel": 1},
            result={"ok": True},
            error=None,
        )


def test_lam_entrypoint_metrics_passthrough_v1() -> None:
    a = RoaudterComAgent()
    a.router = _FakeRouter()  # type: ignore[assignment]

    out = a.answer({"task_id": "t1", "context": {"trace_id": "abc", "task_id": "t1"}, "msg": "ping"})
    assert out["metrics"]["sentinel"] == 1
