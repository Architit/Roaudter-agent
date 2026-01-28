from dataclasses import dataclass

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.policy import RouterPolicy
from roaudter_agent.router import RouterAgent
from roaudter_agent.providers.base import ProviderError, ProviderState


@dataclass
class CloudQuotaProvider:
    name: str = "ollama_cloud"
    def healthcheck(self) -> bool: return True
    def generate(self, task: TaskEnvelope):
        raise ProviderError(
            "quota exhausted",
            code="quota_exhausted",
            http_status=429,
            retryable=False,
            meta={"model": "glm-4.7:cloud"},
        )


@dataclass
class LocalOkProvider:
    name: str = "ollama"
    def healthcheck(self) -> bool: return True
    def generate(self, task: TaskEnvelope):
        return {"text": "pong-local"}


def test_cloud_quota_falls_back_to_local():
    policy = RouterPolicy(default_chain=[])
    router = RouterAgent(
        policy=policy,
        providers=[ProviderState(CloudQuotaProvider()), ProviderState(LocalOkProvider())],
    )

    # просим cloud модель -> policy поставит cloud перед local
    task = TaskEnvelope(
        task_id="t1",
        agent="comm-agent",
        intent="chat",
        payload={"msg": "ping"},
        constraints={"model": "glm-4.7:cloud"},
    )
    res = router.route(task)

    assert res.status == "ok"
    assert res.provider_used == "ollama"
    assert res.result == {"text": "pong-local"}
