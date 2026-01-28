from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, Tuple

from roaudter_agent.providers.base import ProviderState


@dataclass(slots=True)
class HealthConfig:
    ttl_seconds: float = 10.0      # как часто можно реально дергать healthcheck
    cooldown_seconds: float = 30.0 # если провайдер упал — сколько времени не трогаем его


class HealthMonitor:
    """
    Caches healthcheck results with TTL and applies cooldown on failures.
    Avoids calling adapter.healthcheck() on every request.
    """
    def __init__(self, cfg: HealthConfig | None = None) -> None:
        self.cfg = cfg or HealthConfig()
        # name -> (last_check_ts, healthy, cooldown_until_ts)
        self._state: Dict[str, Tuple[float, bool, float]] = {}

    def is_healthy(self, p: ProviderState) -> bool:
        name = p.adapter.name
        now = time.time()

        last_check, healthy, cooldown_until = self._state.get(name, (0.0, True, 0.0))

        # during cooldown, treat as unhealthy without re-checking
        if now < cooldown_until:
            return False

        # TTL: reuse cached value
        if now - last_check < self.cfg.ttl_seconds:
            return healthy

        # perform real check
        try:
            ok = bool(p.adapter.healthcheck())
        except Exception:
            ok = False

        cooldown = (now + self.cfg.cooldown_seconds) if not ok else 0.0
        self._state[name] = (now, ok, cooldown)
        return ok
