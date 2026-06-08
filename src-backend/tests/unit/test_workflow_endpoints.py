import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from app.domain.models.user import User
from app.domain.models.workflow import Workflow, WorkflowStatus
from app.core.security import Role
from app.api.deps import get_current_user
from app.main import app

@pytest.fixture
def mock_current_user():
    return User(
        id=uuid.uuid4(),
        email="doctor@hospital.com",
        full_name="Doctor Strange",
        role=Role.DOCTOR,
        is_active=True
    )

@pytest.fixture
def mock_viewer_user():
    return User(
        id=uuid.uuid4(),
        email="viewer@hospital.com",
        full_name="Viewer Patient",
        role=Role.VIEWER,
        is_active=True
    )

@pytest.mark.asyncio
async def test_start_workflow_success(mock_current_user):
    # Setup override
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    mock_workflow = Workflow(
        id=uuid.uuid4(),
        patient_id="patient-123",
        created_by=mock_current_user.id,
        status=WorkflowStatus.PENDING
    )
    
    with patch("app.api.v1.endpoints.workflow.workflow_repo.create", return_value=mock_workflow), \
         patch("app.api.v1.endpoints.workflow.run_workflow_pipeline", new_callable=AsyncMock) as mock_pipeline:
         
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/workflow/start",
                headers={"Authorization": "Bearer some-mock-token"},
                json={"patient_id": "patient-123", "raw_text": "Doctor notes with BCBS"}
            )
            
    # Clean up overrides
    app.dependency_overrides.clear()
            
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "patient-123"
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_get_workflow_not_found(mock_current_user):
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    with patch("app.api.v1.endpoints.workflow.workflow_repo.get", return_value=None):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/workflow/{uuid.uuid4()}",
                headers={"Authorization": "Bearer some-mock-token"}
            )
            
    app.dependency_overrides.clear()
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_approve_workflow_restricted(mock_viewer_user):
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/workflow/{uuid.uuid4()}/approve",
            headers={"Authorization": "Bearer some-mock-token"}
        )
            
    app.dependency_overrides.clear()
    assert response.status_code == 403
