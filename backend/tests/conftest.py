"""Pytest defaults for IntelLens API tests."""

import os

# Avoid flaky 429s when many auth tests share one TestClient / middleware window.
os.environ.setdefault("AUTH_RATE_LIMIT_RPM", "5000")
os.environ.setdefault("RATE_LIMIT_RPM", "5000")
os.environ.setdefault("INTELLENS_AUTH_DEV_TOKENS", "1")
os.environ.setdefault("INTELLENS_ABUSE_OFF", "1")
os.environ.setdefault("INTELLENS_LLM_RATE_PER_MIN", "0")
# Refresh tests must not baseline Monitors into packaged data; Monitor tests call the processor directly.
os.environ.setdefault("ANALYST_MONITORS", "0")
# Startup must not seed team accounts into the shared test auth DB; tests call the function directly.
os.environ.setdefault("CITEALPHA_PROTECTED_USERS", "0")
# Exercise SQL auth backend (SQLite) in CI without requiring Postgres.
os.environ.setdefault("USE_DB_AUTH", "1")
os.environ.setdefault(
    "AUTH_SQLITE_PATH",
    os.path.join(os.path.dirname(__file__), "_test_auth.db"),
)
