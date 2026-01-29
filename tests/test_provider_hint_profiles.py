from dataclasses import dataclass

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.policy import RouterPolicy
from roaudter_agent.router import RouterAgent
from roaudter_agent.providers.base import ProviderState


@dataclass
class LocalProvider:
    name: str = "ollama"
    def healthcheck(self) -> bool: return True
    def generate(self, task: TaskEnvelope):
        return {"text": "pong-local"}


@dataclass
class RemoteProvider:
    name: str = "openai"
    def healthcheck(self) -> bool: return True
    def generate(self, task: TaskEnvelope):
        return {"text": "pong-remote"}


def test_provider_hint_local_only_routes_to_ollama():
    policy = RouterPolicy(default_chain=[])
    router = RouterAgent(policy=policy, providers=[ProviderState(RemoteProvider()), ProviderState(LocalProvider())])

    t = TaskEnvelope(
        task_id="t1",
        agent="comm",
        intent="chat",
        payload={"msg": "ping", "provider_hint": "local_only"},
    )
    res = router.route(t)

    assert res.status == "ok"
    assert res.provider_used == "ollama"
    assert res.result == {"text": "pong-local"}
