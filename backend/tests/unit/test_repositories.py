import pytest
from unittest.mock import AsyncMock, MagicMock
from app.infra.repositories.user_repository import user_repo
from app.infra.repositories.workflow_repository import workflow_repo
from app.infra.repositories.audit_repository import audit_repo
from app.domain.models.user import User
from app.domain.models.workflow import Workflow
from app.domain.models.audit_log import AuditLog

@pytest.mark.asyncio
async def test_user_repository_get_by_email():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_user = User(email="test@hospital.com", full_name="Test User")
    mock_result.scalars.return_value.first.return_value = mock_user
    db.execute.return_value = mock_result
    
    user = await user_repo.get_by_email(db, "test@hospital.com")
    assert user == mock_user
    db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_audit_repository_immutable():
    db = AsyncMock()
    log = AuditLog(action="create")
    
    with pytest.raises(ValueError, match="Audit logs are immutable and cannot be updated."):
        await audit_repo.update(db, db_obj=log, obj_in={})
        
    with pytest.raises(ValueError, match="Audit logs are immutable and cannot be deleted."):
        await audit_repo.remove(db, id="some-uuid")
