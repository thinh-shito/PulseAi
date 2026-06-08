"""
conftest.py — Pytest global configuration for PulseAI backend tests.

- Sets ENVIRONMENT=test to avoid loading .env secrets
- Configures asyncio event loop scope for pytest-asyncio
"""
import os

import pytest

# ── Set test environment BEFORE any app imports ───────────────────────────────
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-chars-for-jwt-signing")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
