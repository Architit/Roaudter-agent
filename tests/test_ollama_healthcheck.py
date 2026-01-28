from roaudter_agent.providers.ollama import OllamaAdapter

def test_ollama_healthcheck_runs():
    a = OllamaAdapter()
    ok = a.healthcheck()
    assert ok in (True, False)  # главное: не падает
