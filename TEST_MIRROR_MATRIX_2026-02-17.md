# Test Mirror Matrix — Roaudter-agent (2026-02-17)

## Coverage Existing

- Routing/fallback smoke.
- Provider hint: local profile preference.
- Missing API key fallback for cloud providers.
- Health TTL/cooldown gating.
- Basic runtime smoke.

## Missing High-Value Tests

| Domain | Missing Test | Priority | Why |
|---|---|---|---|
| Contracts | Reply envelope schema validator (strict key/types) | P0 | Protects inter-agent protocol stability |
| Contracts | Error envelope consistency across provider adapters | P0 | Prevents parser breakage downstream |
| Router FSM | Retry budget exhausted exactly at boundary (`retry_budget_ms`) | P1 | Prevents deadloop/retry storms |
| Router FSM | Mixed errors: retryable transient -> non-retryable hard stop | P1 | Guards fallback correctness |
| Health | Flapping provider health under cooldown | P1 | Avoids oscillation and starvation |
| Observability | Trace mode filters (`all/errors/retries/nonok`) | P2 | Ensures deterministic logging controls |
| Interop | LAM comm-agent payload roundtrip with context propagation | P0 | Central ecosystem contract |
| Security | Payload size/shape guardrails for malformed dict inputs | P2 | Prevents unsafe runtime assumptions |

## Mirror Plan

- Mirror-A (Immediate): P0 tests for contracts + interop.
- Mirror-B (Next): P1 tests for retry boundaries and health flapping.
- Mirror-C (Forecast): P2 tests for observability and malformed payload hardening.
