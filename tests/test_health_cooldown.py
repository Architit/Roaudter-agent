from dataclasses import dataclass

from roaudter_agent.contracts import TaskEnvelope
from roaudter_agent.health import HealthConfig, HealthMonitor
from roaudter_agent.policy import RouterPolicy
from roaudter_agent.router import RouterAgent
from roaudter_agent.providers.base import ProviderState


@dataclass
class FlakyProvider:
    name: str = "ollama"
    checks: int = 0

    def healthcheck(self) -> bool:
        self.checks += 1
        return False  # всегда unhealthy

    def generate(self, task: TaskEnvelope):
        return {"ok": True}


def test_cooldown_prevents_rechecking_immediately():
    p = FlakyProvider()
    monitor = HealthMonitor(HealthConfig(ttl_seconds=0.0, cooldown_seconds=9999.0))
    router = RouterAgent(policy=RouterPolicy(default_chain=[]), providers=[ProviderState(p)], health=monitor)

    t = TaskEnvelope(task_id="t1", agent="comm", intent="chat", payload={"msg": "ping"})

    # 1-й route вызовет healthcheck (и он вернет False)
    res1 = router.route(t)
    # 2-й route не должен снова дергать healthcheck, потому что cooldown активен
    res2 = router.route(t)

    assert p.checks == 1
    assert res1.status == "error"
    assert res2.status == "error"
