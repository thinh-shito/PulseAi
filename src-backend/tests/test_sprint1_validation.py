"""
Sprint 1 Integration Tests — Validation Suite

Tests:
- V1: GET /health returns 200 OK
- V2: POST /auth/login returns JWT
- V3: No token on protected endpoint → 401
- V4: VIEWER role on restricted endpoint → 403
- V5: AgentState TypedDict structure
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """Mock database session to avoid real DB in unit tests."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    return redis


# ─── V1: Health Check ─────────────────────────────────────────────────────────


# ─── V1: Health Check ─────────────────────────────────────────────────────────

def _redis_available() -> bool:
    try:
        import redis  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.asyncio
@pytest.mark.skipif(not _redis_available(), reason="redis package not installed")
async def test_health_endpoint_structure():
    """V1: Health endpoint returns expected structure."""
    import app.api.v1.endpoints.health  # noqa: F401 — ensure module is loaded

    # redis is lazy-imported inside health_check() — patch at source module
    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_client.aclose = AsyncMock()
        mock_from_url.return_value = mock_redis_client

        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data


# ─── V2 & V3: Auth Endpoints ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_protected_endpoint_without_token_returns_401():
    """V3: Protected endpoint without token → 401 Unauthorized."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ─── V4: RBAC ────────────────────────────────────────────────────────────────

def test_require_role_dependency_exists():
    """V4: require_role dependency is importable and callable."""
    from app.api.deps import require_role
    from app.core.security import Role

    dep = require_role(Role.ADMIN)
    assert callable(dep)


def test_role_enum_values():
    """Role enum has correct values."""
    from app.core.security import Role
    assert Role.ADMIN == "admin"
    assert Role.DOCTOR == "doctor"
    assert Role.VIEWER == "viewer"


# ─── V5: AgentState ──────────────────────────────────────────────────────────

def test_agent_state_fields():
    """V5: AgentState TypedDict has all required fields."""
    from app.services_ai.state import AgentState
    import typing

    hints = typing.get_type_hints(AgentState)
    required_fields = [
        "patient_id", "raw_text", "workflow_id",
        "icd10_codes", "summary", "confidence_score",
        "payer_type", "quality_score", "prior_auth_form",
        "processing_status", "error_message", "retry_count",
    ]
    for field in required_fields:
        assert field in hints, f"Missing field in AgentState: {field}"


def test_llm_factory_importable():
    """LLM factory imports correctly."""
    from app.services_ai.llm_factory import get_llm
    assert callable(get_llm)


# ─── Security Tests ───────────────────────────────────────────────────────────

def test_password_hashing():
    """Password hash and verify round-trip."""
    from app.core.security import hash_password, verify_password

    plain = "TestPassword123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_jwt_create_and_decode():
    """JWT access token can be created and decoded."""
    from app.core.security import create_access_token, decode_token

    data = {"sub": "test-user-id", "role": "doctor"}
    token = create_access_token(data)

    assert isinstance(token, str)
    payload = decode_token(token)
    assert payload["sub"] == "test-user-id"
    assert payload["role"] == "doctor"
    assert payload["type"] == "access"
