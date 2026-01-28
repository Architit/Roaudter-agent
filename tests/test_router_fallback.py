from dataclasses import dataclass

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.policy import RouterPolicy
from roaudter_agent.router import RouterAgent
from roaudter_agent.providers.base import ProviderError, ProviderState


@dataclass
class BoomProvider:
    name: str = "ollama"
    def healthcheck(self) -> bool: return True
    def generate(self, task: TaskEnvelope):
        raise ProviderError("boom", code="boom", retryable=False)


@dataclass
class OkProvider:
    name: str = "openai"
    def healthcheck(self) -> bool: return True
    def generate(self, task: TaskEnvelope):
        return {"text": "pong"}


def test_fallback_to_second_provider():
    policy = RouterPolicy(default_chain=[])
    router = RouterAgent(
        policy=policy,
        providers=[ProviderState(BoomProvider()), ProviderState(OkProvider())],
    )
    task = TaskEnvelope(task_id="t1", agent="comm-agent", intent="chat", payload={"msg": "ping"})
    res = router.route(task)

    assert res.status == "ok"
    assert res.provider_used == "openai"
    assert res.result == {"text": "pong"}
