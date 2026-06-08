import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from app.domain.models.user import User
from app.core.security import Role
from app.api.deps import get_current_user
from app.main import app

@pytest.fixture
def mock_admin_user():
    return User(
        id=uuid.uuid4(),
        email="admin@pulseai.hospital",
        full_name="System Admin",
        role=Role.ADMIN,
        is_active=True
    )

@pytest.fixture
def mock_viewer_user():
    return User(
        id=uuid.uuid4(),
        email="viewer@pulseai.hospital",
        full_name="Viewer Patient",
        role=Role.VIEWER,
        is_active=True
    )

@pytest.mark.asyncio
async def test_admin_users_list_restricted(mock_viewer_user):
    """Viewers should be blocked from admin endpoints."""
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": "Bearer some-mock-token"}
        )
        
    app.dependency_overrides.clear()
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_admin_users_list_success(mock_admin_user):
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    
    with patch("app.api.v1.endpoints.admin.user_repo.get_multi", return_value=[mock_admin_user]):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/admin/users",
                headers={"Authorization": "Bearer some-mock-token"}
            )
            
    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == "admin@pulseai.hospital"

@pytest.mark.asyncio
async def test_admin_create_user_success(mock_admin_user):
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    
    new_user = User(
        id=uuid.uuid4(),
        email="new_doctor@pulseai.hospital",
        full_name="New Doctor",
        role=Role.DOCTOR,
        is_active=True
    )
    
    with patch("app.api.v1.endpoints.admin.user_repo.get_by_email", return_value=None), \
         patch("app.api.v1.endpoints.admin.user_repo.create", return_value=new_user):
         
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/admin/users",
                headers={"Authorization": "Bearer some-mock-token"},
                json={
                    "email": "new_doctor@pulseai.hospital",
                    "password": "SecretPass123!",
                    "full_name": "New Doctor",
                    "role": "doctor"
                }
            )
            
    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new_doctor@pulseai.hospital"
    assert data["role"] == "doctor"
