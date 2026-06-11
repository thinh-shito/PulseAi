"""
test_tier2_boundary.py - 25 Boundary & Corner case tests (5 tests per Sprint 5 feature).
"""
import asyncio
import json
import uuid
import pytest
from httpx import AsyncClient
from app.domain.models.workflow import WorkflowStatus
from app.core.database import get_session_factory
from app.domain.models.workflow import Workflow
from tests.e2e.conftest import make_pdf

# ─── Feature 1: Review & Edit Wizard ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_t2_f1_01(client: AsyncClient, seeded_users):
    """Upload document with unsupported extension."""
    headers = seeded_users["doctor"]["headers"]
    files = {"file": ("clinical.exe", b"malicious binary content", "application/x-msdownload")}
    response = await client.post("/api/v1/workflow/upload-document", headers=headers, files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

@pytest.mark.asyncio
async def test_e2e_t2_f1_02(client: AsyncClient, seeded_users):
    """Upload empty file content."""
    headers = seeded_users["doctor"]["headers"]
    files = {"file": ("clinical.txt", b"", "text/plain")}
    response = await client.post("/api/v1/workflow/upload-document", headers=headers, files=files)
    # The application can either accept empty string or reject with 400
    assert response.status_code in [200, 400]

@pytest.mark.asyncio
async def test_e2e_t2_f1_03(client: AsyncClient, seeded_users):
    """Start workflow with missing patient ID."""
    headers = seeded_users["doctor"]["headers"]
    payload = {"raw_text": "Clinical notes."}
    response = await client.post("/api/v1/workflow/start", headers=headers, json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_e2e_t2_f1_04(client: AsyncClient, seeded_users):
    """Start workflow with empty raw text."""
    headers = seeded_users["doctor"]["headers"]
    payload = {"patient_id": "PT-B1", "raw_text": ""}
    response = await client.post("/api/v1/workflow/start", headers=headers, json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_e2e_t2_f1_05(client: AsyncClient, seeded_users):
    """Stream workflow updates for invalid UUID."""
    headers = seeded_users["doctor"]["headers"]
    # Should handle gracefully, returns completed or one-off message, or 404
    response = await client.get(f"/api/v1/workflow/{uuid.uuid4()}/stream", headers=headers)
    assert response.status_code in [200, 404]

# ─── Feature 2: Inline Edit & Save Fields ────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_t2_f2_01(client: AsyncClient, seeded_users):
    """Patch fields for invalid workflow UUID."""
    headers = seeded_users["doctor"]["headers"]
    payload = {"fields": {"diagnosis_code": "M54.5"}}
    response = await client.patch(f"/api/v1/workflow/{uuid.uuid4()}/fields", headers=headers, json=payload)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_e2e_t2_f2_02(client: AsyncClient, seeded_users):
    """Patch fields with invalid request structure."""
    headers = seeded_users["doctor"]["headers"]
    payload = {"fields": "should be dict, not string"}
    response = await client.patch(f"/api/v1/workflow/{uuid.uuid4()}/fields", headers=headers, json=payload)
    assert response.status_code in [400, 422]

@pytest.mark.asyncio
async def test_e2e_t2_f2_03(client: AsyncClient, seeded_users):
    """Double approval action."""
    headers = seeded_users["doctor"]["headers"]
    factory = get_session_factory()
    wf_id = uuid.uuid4()
    async with factory() as db:
        wf = Workflow(
            id=wf_id,
            patient_id="PT-B2",
            created_by=seeded_users["doctor"]["id"],
            status=WorkflowStatus.APPROVED
        )
        db.add(wf)
        await db.commit()

    # Call approve on already approved workflow
    response = await client.post(f"/api/v1/workflow/{wf_id}/approve", headers=headers)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_e2e_t2_f2_04(client: AsyncClient, seeded_users):
    """Non-doctor tries to approve workflow."""
    headers = seeded_users["viewer"]["headers"]
    response = await client.post(f"/api/v1/workflow/{uuid.uuid4()}/approve", headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_e2e_t2_f2_05(client: AsyncClient, seeded_users):
    """Patch fields with massive JSON payload."""
    headers = seeded_users["doctor"]["headers"]
    # Create workflow
    create_resp = await client.post("/api/v1/workflow/start", headers=headers, json={"patient_id": "PT-B3", "raw_text": "notes"})
    wf_id = create_resp.json()["id"]

    # Massive payload
    massive_string = "X" * 10000
    payload = {"fields": {"notes": massive_string}}
    response = await client.patch(f"/api/v1/workflow/{wf_id}/fields", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["result_data"]["fields"]["notes"] == massive_string

# ─── Feature 3: PA Template System Admin ─────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_t2_f3_01(client: AsyncClient, seeded_users):
    """Admin uploads template with invalid JSON schema."""
    headers = seeded_users["admin"]["headers"]
    pdf_bytes = make_pdf(["Blank Template"])
    data = {"schema_data": "{invalid-json}"}
    files = {"file": ("tpl.pdf", pdf_bytes, "application/pdf")}
    response = await client.post("/api/v1/admin/templates", headers=headers, data=data, files=files)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_e2e_t2_f3_02(client: AsyncClient, seeded_users):
    """Upload template with empty binary file."""
    headers = seeded_users["admin"]["headers"]
    data = {"schema_data": json.dumps({"name": "Empty PDF Template", "fields": []})}
    files = {"file": ("tpl.pdf", b"", "application/pdf")}
    response = await client.post("/api/v1/admin/templates", headers=headers, data=data, files=files)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_e2e_t2_f3_03(client: AsyncClient, seeded_users):
    """Upload template using a non-PDF document (DOCX)."""
    headers = seeded_users["admin"]["headers"]
    data = {"schema_data": json.dumps({"name": "Docx Template", "fields": []})}
    files = {"file": ("tpl.docx", b"docx-fake-bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = await client.post("/api/v1/admin/templates", headers=headers, data=data, files=files)
    assert response.status_code == 400
    assert "PDF format" in response.json()["detail"]

@pytest.mark.asyncio
async def test_e2e_t2_f3_04(client: AsyncClient, seeded_users):
    """Toggle active status for invalid template ID."""
    headers = seeded_users["admin"]["headers"]
    response = await client.patch("/api/v1/admin/templates/99999", headers=headers, json={"is_active": False})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_e2e_t2_f3_05(client: AsyncClient, seeded_users):
    """Fetch non-existent template detail/blank download."""
    headers = seeded_users["doctor"]["headers"]
    response = await client.get("/api/v1/templates/00000/download-blank", headers=headers)
    assert response.status_code == 404

# ─── Feature 4: PDF Export ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_t2_f4_01(client: AsyncClient, seeded_users):
    """Export PDF for workflow without fields saved."""
    headers = seeded_users["doctor"]["headers"]
    create_resp = await client.post("/api/v1/workflow/start", headers=headers, json={"patient_id": "PT-B4", "raw_text": "notes"})
    wf_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert b"%PDF-" in response.read()

@pytest.mark.asyncio
async def test_e2e_t2_f4_02(client: AsyncClient, seeded_users):
    """Export PDF containing special Unicode characters."""
    headers = seeded_users["doctor"]["headers"]
    create_resp = await client.post("/api/v1/workflow/start", headers=headers, json={"patient_id": "PT-B5", "raw_text": "notes"})
    wf_id = create_resp.json()["id"]

    # Special characters: Vietnamese, Chinese, Russian
    special_text = "Thịnh - 🩺 - 临床的 - клинический"
    await client.patch(f"/api/v1/workflow/{wf_id}/fields", headers=headers, json={"fields": {"diagnosis_code": special_text}})

    response = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

@pytest.mark.asyncio
async def test_e2e_t2_f4_03(client: AsyncClient, seeded_users):
    """Viewer downloads PDF."""
    headers = seeded_users["doctor"]["headers"]
    viewer_headers = seeded_users["viewer"]["headers"]
    create_resp = await client.post("/api/v1/workflow/start", headers=headers, json={"patient_id": "PT-B6", "raw_text": "notes"})
    wf_id = create_resp.json()["id"]

    # Viewer role can download
    response = await client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=viewer_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

@pytest.mark.asyncio
async def test_e2e_t2_f4_04(client: AsyncClient, seeded_users):
    """Concurrent PDF exports."""
    headers = seeded_users["doctor"]["headers"]
    create_resp = await client.post("/api/v1/workflow/start", headers=headers, json={"patient_id": "PT-B7", "raw_text": "notes"})
    wf_id = create_resp.json()["id"]

    tasks = [client.get(f"/api/v1/workflow/{wf_id}/export-pdf", headers=headers) for _ in range(5)]
    responses = await asyncio.gather(*tasks)
    for resp in responses:
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_e2e_t2_f4_05(client: AsyncClient, seeded_users):
    """Export PDF when template is deactivated."""
    admin_headers = seeded_users["admin"]["headers"]
    doctor_headers = seeded_users["doctor"]["headers"]
    
    # Upload template
    pdf_bytes = make_pdf(["Template contents"])
    data = {"schema_data": json.dumps({"name": "Deactivatable Template", "fields": ["diagnosis_code"]})}
    files = {"file": ("tpl.pdf", pdf_bytes, "application/pdf")}
    create_resp = await client.post("/api/v1/admin/templates", headers=admin_headers, data=data, files=files)
    tpl_id = create_resp.json()["id"]

    # Deactivate it
    await client.patch(f"/api/v1/admin/templates/{tpl_id}", headers=admin_headers, json={"is_active": False})

    # Download blank fails
    response = await client.get(f"/api/v1/templates/{tpl_id}/download-blank", headers=doctor_headers)
    assert response.status_code == 404

# ─── Feature 5: Chat Assistant ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_t2_f5_01(client: AsyncClient, seeded_users):
    """Chat payload exceeds token constraints."""
    headers = seeded_users["doctor"]["headers"]
    long_msg = "word " * 1200
    payload = {"message": long_msg, "history": []}
    response = await client.post("/api/v1/chat", headers=headers, json=payload)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_e2e_t2_f5_02(client: AsyncClient, seeded_users):
    """Chat message empty."""
    headers = seeded_users["doctor"]["headers"]
    payload = {"message": "", "history": []}
    response = await client.post("/api/v1/chat", headers=headers, json=payload)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_e2e_t2_f5_03(client: AsyncClient, seeded_users):
    """Chat with invalid workflow ID."""
    headers = seeded_users["doctor"]["headers"]
    payload = {
        "message": "Hello",
        "workflow_id": "99999",
        "history": []
    }
    response = await client.post("/api/v1/chat", headers=headers, json=payload)
    assert response.status_code == 200
    assert "No matching workflow" in response.json()["reply"]

@pytest.mark.asyncio
async def test_e2e_t2_f5_04(client: AsyncClient, seeded_users):
    """Chat PHI edge cases (compound names)."""
    headers = seeded_users["doctor"]["headers"]
    payload = {
        "message": "Case for Dr. Jean-Pierre d'Artois-Smith with patient Martin Luther King Jr.",
        "history": []
    }
    response = await client.post("/api/v1/chat", headers=headers, json=payload)
    assert response.status_code == 200
    anonymized = response.json()["anonymized"]
    assert "[PERSON]" in anonymized
    assert "Martin" not in anonymized

@pytest.mark.asyncio
async def test_e2e_t2_f5_05(client: AsyncClient, seeded_users):
    """Invalid roles in chat history."""
    headers = seeded_users["doctor"]["headers"]
    payload = {
        "message": "Continue",
        "history": [
            {"role": "admin", "content": "Hello"}
        ]
    }
    response = await client.post("/api/v1/chat", headers=headers, json=payload)
    assert response.status_code == 422
