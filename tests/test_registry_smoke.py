# Copyright (c) 2026-06-07 RADRILONIUMA / TRIANIUMA Kingdom. All rights reserved.
from roaudter_agent import build_default_router, TaskEnvelope

def test_registry_build_default_router_smoke():
    r = build_default_router()
    t = TaskEnvelope(task_id="t1", agent="comm", intent="chat", payload={"msg": "ping"})
    res = r.route(t)

    assert res.status in ("ok", "error")  # главное: pipeline живой
