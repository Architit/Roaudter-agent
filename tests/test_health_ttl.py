from dataclasses import dataclass

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.health import HealthConfig, HealthMonitor
from roaudter_agent.policy import RouterPolicy
from roaudter_agent.router import RouterAgent
from roaudter_agent.providers.base import ProviderState


@dataclass
class CountingProvider:
    name: str = "ollama"
    checks: int = 0

    def healthcheck(self) -> bool:
        self.checks += 1
        return True

    def generate(self, task: TaskEnvelope):
        return {"ok": True}


def test_healthcheck_is_cached_by_ttl():
    p = CountingProvider()
    monitor = HealthMonitor(HealthConfig(ttl_seconds=9999.0, cooldown_seconds=1.0))
    router = RouterAgent(policy=RouterPolicy(default_chain=[]), providers=[ProviderState(p)], health=monitor)

    t = TaskEnvelope(task_id="t1", agent="comm", intent="chat", payload={"msg": "ping"})
    router.route(t)
    router.route(t)
    router.route(t)

    # healthcheck должен вызваться 1 раз, остальное из кеша TTL
    assert p.checks == 1
