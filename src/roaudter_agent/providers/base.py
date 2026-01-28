from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, Optional


class ProviderError(RuntimeError):
    """
    Structured provider error for routing / fallback decisions.
    """
    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        http_status: Optional[int] = None,
        retryable: bool = False,
        meta: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.retryable = retryable
        self.meta = meta or {}

    def to_dict(self, *, provider: Optional[str] = None) -> dict[str, Any]:
        return {
            "provider": provider,
            "code": self.code,
            "http_status": self.http_status,
            "retryable": self.retryable,
            "message": str(self),
            "meta": self.meta,
        }


class ProviderAdapter(Protocol):
    name: str

    def healthcheck(self) -> bool: ...
    def generate(self, task) -> Any: ...


@dataclass(slots=True)
class ProviderState:
    adapter: ProviderAdapter
    healthy: bool = True
