"""
test_tier4_workloads.py - 5 Real-world workload scenarios.
"""
import json
import uuid
import pytest
from httpx import AsyncClient
from app.domain.models.workflow import WorkflowStatus
from app.core.database import get_session_factory
from app.domain.models.workflow import Workflow
from tests.e2e.conftest import make_pdf

@pytest.mark.asyncio
async def test_e2e_t4_01(client: AsyncClient, seeded_users):
    """End-to-End Workflow Run."""
    headers = seeded_users["doctor"]["headers"]
    
    # 1. Upload clinical notes PDF
    pdf_bytes = make_pdf(["Patient Jane Doe. CPT: 97110."])
    files = {"file": ("note.pdf", pdf_bytes, "application/pdf")}
    upload_resp = await client.post("/api/v1/workflow/upload-document", headers=headers, files=files)
    assert upload_resp.status_code == 200
    extracted_text = upload_resp.json()["text"]
    
    # 2. Start workflow
    create_wf = await client.post("/api/v1/workflow/start", headers=headers, json={
        "patient_id": "PT-401",
        "raw_text": extracted_text
    })
    assert create_wf.status_code == 200
    wf_id = create_wf.json()["id"]
    
    # 3. Stream progress via SSE
    async with client.stream("GET", f"/api/v1/workflow/{wf_id}/stream", headers=headers) as stream_resp:
        assert stream_resp.status_code == 200
        async for line in stream_resp.aiter_lines():
            if "status" in line:
                break
                
    # 4. Edit fields & save
    patch_resp = await client.patch(f"/api/v1/workflow/{wf_id}/fields", headers=headers, json={
        "fields": {"diagnosis_code": "M54.5", "procedure_code": "97110"}
    })
    assert patch_resp.status_code == 200
    
    # 5. Export PDF
    export_resp = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=headers)
    assert export_resp.status_code == 200
    assert b"%PDF-" in export_resp.read()

@pytest.mark.asyncio
async def test_e2e_t4_02(client: AsyncClient, seeded_users):
    """Clinical Query via Chat."""
    headers = seeded_users["doctor"]["headers"]
    
    # 1. Ask about Jane Doe diagnosis -> de-identifies name
    response = await client.post("/api/v1/chat", headers=headers, json={
        "message": "What do the guidelines say for Jane Doe with low back pain?",
        "history": []
    })
    assert response.status_code == 200
    assert "[PERSON]" in response.json()["anonymized"]
    
    # 2. Initiate workflow trigger query
    response_trigger = await client.post("/api/v1/chat", headers=headers, json={
        "message": "Let's start a new case for Jane Doe",
        "history": []
    })
    assert response_trigger.status_code == 200
    assert response_trigger.json()["action"] == "offer_create_workflow"

@pytest.mark.asyncio
async def test_e2e_t4_03(client: AsyncClient, seeded_users):
    """Admin Template Provisioning."""
    admin_headers = seeded_users["admin"]["headers"]
    doctor_headers = seeded_users["doctor"]["headers"]
    
    # 1. Admin uploads template PDF and coordinates schema
    pdf_bytes = make_pdf(["Template content"])
    data = {"schema_data": json.dumps({"name": "Admin Template", "fields": ["member_id"]})}
    files = {"file": ("tpl.pdf", pdf_bytes, "application/pdf")}
    create_resp = await client.post("/api/v1/admin/templates", headers=admin_headers, data=data, files=files)
    assert create_resp.status_code == 201
    tpl_id = create_resp.json()["id"]
    
    # 2. Verify template is active in GET list
    list_resp = await client.get("/api/v1/templates", headers=doctor_headers)
    assert tpl_id in [t["id"] for t in list_resp.json()]
    
    # 3. Download blank version to check
    blank_resp = await client.get(f"/api/v1/templates/{tpl_id}/download-blank", headers=doctor_headers)
    assert blank_resp.status_code == 200
    assert b"%PDF-" in blank_resp.read()

@pytest.mark.asyncio
async def test_e2e_t4_04(client: AsyncClient, seeded_users):
    """Invalid Input Graceful Failure."""
    doctor_headers = seeded_users["doctor"]["headers"]
    viewer_headers = seeded_users["viewer"]["headers"]
    
    # 1. Upload unsupported file format
    files = {"file": ("clinical.exe", b"bytes", "application/octet-stream")}
    upload_resp = await client.post("/api/v1/workflow/upload-document", headers=doctor_headers, files=files)
    assert upload_resp.status_code == 400
    
    # 2. Trigger token limit chat query
    too_long_message = "a " * 1200
    chat_resp = await client.post("/api/v1/chat", headers=doctor_headers, json={"message": too_long_message})
    assert chat_resp.status_code == 400
    
    # 3. Patch fields with invalid request structure
    patch_resp = await client.patch(f"/api/v1/workflow/{uuid.uuid4()}/fields", headers=doctor_headers, json={"fields": "invalid"})
    assert patch_resp.status_code in [400, 404, 422]
    
    # 4. Request non-existent PDF
    pdf_resp = await client.get(f"/api/v1/workflow/{uuid.uuid4()}/export-pdf", headers=doctor_headers)
    assert pdf_resp.status_code == 404
    
    # 5. Attempt admin template upload with doctor/viewer role
    pdf_bytes = make_pdf(["Blank Template"])
    tpl_data = {"schema_data": json.dumps({"name": "No Access", "fields": []})}
    tpl_files = {"file": ("tpl.pdf", pdf_bytes, "application/pdf")}
    tpl_resp = await client.post("/api/v1/admin/templates", headers=viewer_headers, data=tpl_data, files=tpl_files)
    assert tpl_resp.status_code == 403

@pytest.mark.asyncio
async def test_e2e_t4_05(client: AsyncClient, seeded_users):
    """Combined Interactive Session."""
    admin_headers = seeded_users["admin"]["headers"]
    doctor_headers = seeded_users["doctor"]["headers"]
    
    # 1. Admin uploads template
    pdf_bytes = make_pdf(["Template"])
    data = {"schema_data": json.dumps({"name": "Interactive Template", "fields": ["diagnosis_code"]})}
    files = {"file": ("tpl.pdf", pdf_bytes, "application/pdf")}
    create_tpl = await client.post("/api/v1/admin/templates", headers=admin_headers, data=data, files=files)
    assert create_tpl.status_code == 201
    
    # 2. Doctor uploads clinical note
    note_files = {"file": ("note.txt", b"Patient Jane Doe. Diagnosis: low back pain.", "text/plain")}
    upload_resp = await client.post("/api/v1/workflow/upload-document", headers=doctor_headers, files=note_files)
    note_text = upload_resp.json()["text"]
    
    # 3. Doctor starts workflow
    create_wf = await client.post("/api/v1/workflow/start", headers=doctor_headers, json={
        "patient_id": "PT-405",
        "raw_text": note_text
    })
    wf_id = create_wf.json()["id"]
    
    # 4. Doctor streams AI execution
    async with client.stream("GET", f"/api/v1/workflow/{wf_id}/stream", headers=doctor_headers) as stream:
        assert stream.status_code == 200
        async for line in stream.aiter_lines():
            if "status" in line:
                break
                
    # 5. Doctor patches fields
    patch_resp = await client.patch(f"/api/v1/workflow/{wf_id}/fields", headers=doctor_headers, json={
        "fields": {"diagnosis_code": "M54.5"}
    })
    assert patch_resp.status_code == 200
    
    # 6. Doctor chats about case details
    chat_resp = await client.post("/api/v1/chat", headers=doctor_headers, json={
        "message": "Let's check details for Jane Doe",
        "workflow_id": wf_id,
        "history": []
    })
    assert chat_resp.status_code == 200
    
    # 7. Doctor approves workflow
    factory = get_session_factory()
    async with factory() as db:
        wf = await db.get(Workflow, wf_id)
        wf.status = WorkflowStatus.AWAITING_APPROVAL
        db.add(wf)
        await db.commit()
    approve_resp = await client.post(f"/api/v1/workflow/{wf_id}/approve", headers=doctor_headers)
    assert approve_resp.status_code == 200
    
    # 8. Doctor downloads final PDF
    pdf_resp = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=doctor_headers)
    assert pdf_resp.status_code == 200
    assert b"OFFICIAL APPROVED" in pdf_resp.read()
