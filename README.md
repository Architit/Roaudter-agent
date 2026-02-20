# Roaudter-agent (Router Agent)

Minimal skeleton for LAM multi-provider LLM Router Agent.

## Protocol
See [INTERACTION_PROTOCOL.md](INTERACTION_PROTOCOL.md).

## Dev / Tests

- Install (dev + tests):
  - `python -m venv .venv && . .venv/bin/activate`
  - `python -m pip install -e '.[test]'`
- Run tests:
  - `.venv/bin/pytest -q`
  - `scripts/test_entrypoint.sh --all`

- [x] 2026-01-30 — smoke-test: 13 passed (pytest via `.[test]`)
- [x] 2026-02-17 — packaging/import hard-fail removed; 16 passed
