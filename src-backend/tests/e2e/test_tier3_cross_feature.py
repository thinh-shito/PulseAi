"""
test_tier3_cross_feature.py - 5 Cross-feature interaction tests.
"""
import json
import pytest
from httpx import AsyncClient
from app.domain.models.workflow import WorkflowStatus
from app.core.database import get_session_factory
from app.domain.models.workflow import Workflow
from tests.e2e.conftest import make_pdf

@pytest.mark.asyncio
async def test_e2e_t3_01(client: AsyncClient, seeded_users):
    """Admin Template to PDF Export Integration."""
    admin_headers = seeded_users["admin"]["headers"]
    doctor_headers = seeded_users["doctor"]["headers"]
    
    # 1. Admin uploads template
    pdf_bytes = make_pdf(["Aetna PT Form Template"])
    data = {"schema_data": json.dumps({"name": "Aetna PT Form", "fields": ["diagnosis_code", "prior_treatments"]})}
    files = {"file": ("aetna_pt.pdf", pdf_bytes, "application/pdf")}
    create_tpl = await client.post("/api/v1/admin/templates", headers=admin_headers, data=data, files=files)
    assert create_tpl.status_code == 201
    
    # 2. Doctor starts workflow
    create_wf = await client.post("/api/v1/workflow/start", headers=doctor_headers, json={"patient_id": "PT-301", "raw_text": "notes"})
    wf_id = create_wf.json()["id"]
    
    # 3. Doctor patches fields corresponding to template
    await client.patch(f"/api/v1/workflow/{wf_id}/fields", headers=doctor_headers, json={
        "fields": {"diagnosis_code": "M54.5", "prior_treatments": "Ibuprofen"}
    })
    
    # 4. Doctor exports PDF
    export_resp = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=doctor_headers)
    assert export_resp.status_code == 200
    pdf_content = export_resp.read()
    assert b"M54.5" in pdf_content
    assert b"Ibuprofen" in pdf_content

@pytest.mark.asyncio
async def test_e2e_t3_02(client: AsyncClient, seeded_users):
    """Chat Assistant to Workflow Wizard Integration."""
    doctor_headers = seeded_users["doctor"]["headers"]
    
    # 1. Doctor chats and gets suggestion
    chat_payload = {"message": "Patient Jane Doe needs spinal injection under BCBS policy.", "history": []}
    chat_resp = await client.post("/api/v1/chat", headers=doctor_headers, json=chat_payload)
    assert chat_resp.status_code == 200
    assert chat_resp.json()["action"] == "offer_create_workflow"
    
    # 2. Doctor proceeds to create workflow using clinical details from chat
    create_wf = await client.post("/api/v1/workflow/start", headers=doctor_headers, json={
        "patient_id": "PT-302",
        "raw_text": "Patient Jane Doe needs spinal injection under BCBS policy."
    })
    assert create_wf.status_code == 200
    assert create_wf.json()["patient_id"] == "PT-302"

@pytest.mark.asyncio
async def test_e2e_t3_03(client: AsyncClient, seeded_users):
    """Workflow Approval and PDF Export State Synchronization."""
    doctor_headers = seeded_users["doctor"]["headers"]
    
    # 1. Start workflow (initially pending / draft)
    create_wf = await client.post("/api/v1/workflow/start", headers=doctor_headers, json={"patient_id": "PT-303", "raw_text": "notes"})
    wf_id = create_wf.json()["id"]
    
    # Export and check stamp is DRAFT
    export_draft = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=doctor_headers)
    assert b"DRAFT" in export_draft.read()
    
    # 2. Manually transition to awaiting_approval in DB
    factory = get_session_factory()
    async with factory() as db:
        wf = await db.get(Workflow, wf_id)
        wf.status = WorkflowStatus.AWAITING_APPROVAL
        db.add(wf)
        await db.commit()
        
    # 3. Approve workflow
    approve_resp = await client.post(f"/api/v1/workflow/{wf_id}/approve", headers=doctor_headers)
    assert approve_resp.status_code == 200
    
    # 4. Export and check stamp is OFFICIAL APPROVED
    export_approved = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=doctor_headers)
    assert b"OFFICIAL APPROVED" in export_approved.read()

@pytest.mark.asyncio
async def test_e2e_t3_04(client: AsyncClient, seeded_users):
    """Audit Trail of Wizard, Template and Chat Actions."""
    admin_headers = seeded_users["admin"]["headers"]
    doctor_headers = seeded_users["doctor"]["headers"]
    
    # 1. Admin uploads template (creates audit log)
    pdf_bytes = make_pdf(["Template"])
    data = {"schema_data": json.dumps({"name": "Audit Template", "fields": []})}
    files = {"file": ("tpl.pdf", pdf_bytes, "application/pdf")}
    await client.post("/api/v1/admin/templates", headers=admin_headers, data=data, files=files)
    
    # 2. Doctor starts workflow
    create_wf = await client.post("/api/v1/workflow/start", headers=doctor_headers, json={"patient_id": "PT-304", "raw_text": "notes"})
    wf_id = create_wf.json()["id"]
    
    # 3. Doctor updates fields (creates audit log)
    await client.patch(f"/api/v1/workflow/{wf_id}/fields", headers=doctor_headers, json={"fields": {"diagnosis_code": "M54.5"}})
    
    # 4. Doctor chats (creates audit log)
    await client.post("/api/v1/chat", headers=doctor_headers, json={"message": "Help me", "history": []})
    
    # 5. Doctor exports PDF (creates audit log)
    await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=doctor_headers)
    
    # 6. Admin queries audit logs
    audit_resp = await client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    actions = [log["action"] for log in logs]
    
    assert "CREATE_TEMPLATE" in actions
    assert "EDIT_FIELDS" in actions
    assert "CHAT_QUERY" in actions
    assert "EXPORT_PDF" in actions

@pytest.mark.asyncio
async def test_e2e_t3_05(client: AsyncClient, seeded_users):
    """Concurrent Template Updates and Active Workflow Run."""
    admin_headers = seeded_users["admin"]["headers"]
    doctor_headers = seeded_users["doctor"]["headers"]
    
    # 1. Admin uploads template version 1
    pdf_bytes_v1 = make_pdf(["Template V1"])
    data_v1 = {"schema_data": json.dumps({"name": "Template V1", "fields": ["diagnosis_code"]})}
    files_v1 = {"file": ("tpl.pdf", pdf_bytes_v1, "application/pdf")}
    create_v1 = await client.post("/api/v1/admin/templates", headers=admin_headers, data=data_v1, files=files_v1)
    tpl_id_v1 = create_v1.json()["id"]
    
    # 2. Doctor starts workflow
    create_wf = await client.post("/api/v1/workflow/start", headers=doctor_headers, json={"patient_id": "PT-305", "raw_text": "notes"})
    wf_id = create_wf.json()["id"]
    
    # 3. Admin updates/uploads template version 2 (deactivates V1)
    await client.patch(f"/api/v1/admin/templates/{tpl_id_v1}", headers=admin_headers, json={"is_active": False})
    
    pdf_bytes_v2 = make_pdf(["Template V2"])
    data_v2 = {"schema_data": json.dumps({"name": "Template V2", "fields": ["diagnosis_code"]})}
    files_v2 = {"file": ("tpl2.pdf", pdf_bytes_v2, "application/pdf")}
    create_v2 = await client.post("/api/v1/admin/templates", headers=admin_headers, data=data_v2, files=files_v2)
    tpl_id_v2 = create_v2.json()["id"]
    
    # 4. Doctor exports PDF. It should export with active Template version (V2)
    export_resp = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=doctor_headers)
    assert export_resp.status_code == 200
