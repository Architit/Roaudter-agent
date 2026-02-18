from __future__ import annotations

import os


# Deterministic local fallback in CI/sandbox where local Ollama may be unavailable.
os.environ.setdefault("ROAUDTER_OFFLINE_TEST_MODE", "1")
