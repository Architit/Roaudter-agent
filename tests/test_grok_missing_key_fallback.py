from roaudter_agent import build_default_router, TaskEnvelope


def test_missing_grok_key_falls_back_to_ollama(monkeypatch):
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    r = build_default_router()
    t = TaskEnvelope(task_id="t1", agent="comm", intent="chat", payload={"msg": "Say only: pong"})
    res = r.route(t)

    assert res.status == "ok"
    assert res.provider_used == "ollama"
    assert res.result is not None
    assert res.result.get("text") is not None
