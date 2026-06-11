import asyncio
import io
import json
import logging
import base64
from typing import Dict, Any, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_current_user, require_role
from app.core.database import get_db, get_session_factory
from app.core.security import Role
from app.domain.models.user import User
from app.domain.models.workflow import Workflow, WorkflowStatus
from app.domain.models.audit_log import AuditLog
from app.domain.models.pa_templates import PATemplate
from app.infra.repositories.workflow_repository import workflow_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])

# In-memory queues for real-time SSE updates
active_streams: Dict[str, asyncio.Queue] = {}

# ─── Pydantic Schemas ────────────────────────────────────────────────────────



class WorkflowStartRequest(BaseModel):
    patient_id: str = Field(..., json_schema_extra={"example": "patient-123"})
    raw_text: str = Field(..., json_schema_extra={"example": "Patient John Doe has back pain. Insurance: BCBS."})

class WorkflowFieldsUpdateRequest(BaseModel):
    fields: Dict[str, str]

class WorkflowResponse(BaseModel):
    id: uuid.UUID
    patient_id: str
    created_by: uuid.UUID
    status: str
    quality_score: Optional[float] = None
    payer_type: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)

# ─── Background Pipeline runner ──────────────────────────────────────────────

async def run_workflow_pipeline(workflow_id: str, patient_id: str, raw_text: str, created_by: str):
    """Executes the LangGraph Prior Auth pipeline in the background and streams progress."""
    from app.services_ai.graph_builder import build_graph
    
    session_factory = get_session_factory()
    graph = build_graph()
    
    initial_state = {
        "patient_id": patient_id,
        "raw_text": raw_text,
        "workflow_id": workflow_id,
        "retry_count": 0,
        "icd10_codes": [],
        "summary": "",
        "confidence_score": 0.0,
        "payer_type": None,
        "quality_score": None,
        "prior_auth_form": None,
        "processing_status": "pending",
        "error_message": None
    }
    
    queue = active_streams.get(workflow_id)

    async def update_state(status_str: str, updates: Optional[dict] = None):
        if updates is None:
            updates = {}
            
        # Write to db
        async with session_factory() as db:
            db_wf = await workflow_repo.get(db, uuid.UUID(workflow_id))
            if db_wf:
                db_wf.status = WorkflowStatus(status_str)
                if updates.get("payer_type"):
                    db_wf.payer_type = updates["payer_type"]
                if updates.get("quality_score") is not None:
                    db_wf.quality_score = updates["quality_score"]
                if updates.get("prior_auth_form"):
                    db_wf.result_data = updates["prior_auth_form"]
                db.add(db_wf)
                await db.commit()
                
            # Create ClinicalRecord if finalized
            if status_str in ["completed", "approved", "awaiting_approval"]:
                # Ensure we don't save duplicate clinical records
                existing_record = await workflow_repo.get_clinical_record(db, workflow_id=uuid.UUID(workflow_id))
                if not existing_record:
                    clinical_data = {
                        "workflow_id": uuid.UUID(workflow_id),
                        "patient_id": patient_id,
                        "icd10_codes": updates.get("icd10_codes", []),
                        "summary": updates.get("summary", ""),
                        "confidence_score": updates.get("confidence_score", 0.0),
                    }
                    await workflow_repo.create_clinical_record(db, obj_in=clinical_data)

        # Notify queue
        if queue:
            await queue.put({
                "status": status_str,
                "payer_type": updates.get("payer_type"),
                "quality_score": updates.get("quality_score"),
                "prior_auth_form": updates.get("prior_auth_form"),
                "icd10_codes": updates.get("icd10_codes"),
                "summary": updates.get("summary"),
            })

    try:
        await update_state("processing")
        
        # Execute graph
        async for event in graph.astream(initial_state):
            node_name = list(event.keys())[0]
            node_output = event[node_name]
            
            # Map node names to database workflow statuses
            status_map = {
                "clinical": "processing",
                "router": "processing",
                "bcbs": "processing",
                "aetna": "processing",
                "uhc": "processing",
                "bhyt": "processing",
                "quality": "processing"
            }
            
            # Update state with outputs
            initial_state.update(node_output)
            await update_state(status_map.get(node_name, "processing"), initial_state)
            
        # Graph complete, map processing status to final database status
        final_status = initial_state.get("processing_status", "completed")
        if final_status == "awaiting_approval":
            await update_state("awaiting_approval", initial_state)
        elif final_status == "approved":
            await update_state("approved", initial_state)
        else:
            await update_state("completed", initial_state)

    except Exception as e:
        logger.error(f"Error in workflow background run: {e}", exc_info=True)
        await update_state("failed", {"error_message": str(e)})
    finally:
        # Close the stream
        if queue:
            await queue.put(None)

# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/start", response_model=WorkflowResponse)
async def start_workflow(
    request: WorkflowStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Starts the Prior Authorization pipeline asynchronously."""
    # Create the workflow record in PENDING state
    workflow_data = {
        "patient_id": request.patient_id,
        "created_by": current_user.id,
        "status": WorkflowStatus.PENDING,
    }
    db_wf = await workflow_repo.create(db, obj_in=workflow_data)
    
    # Initialize the SSE queue
    wf_id_str = str(db_wf.id)
    active_streams[wf_id_str] = asyncio.Queue()
    
    # Enqueue pipeline run in background tasks
    background_tasks.add_task(
        run_workflow_pipeline,
        workflow_id=wf_id_str,
        patient_id=request.patient_id,
        raw_text=request.raw_text,
        created_by=str(current_user.id)
    )
    
    return db_wf

@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists workflows created by the current user, or all workflows for doctor/admin."""
    if current_user.role in [Role.ADMIN, Role.DOCTOR]:
        return await workflow_repo.get_multi(db, skip=skip, limit=limit)
    return await workflow_repo.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)

@router.get("/{id}", response_model=WorkflowResponse)
async def get_workflow(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves current workflow status and data."""
    wf = await workflow_repo.get(db, id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf

@router.get("/{id}/stream")
async def stream_workflow_progress(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    """Streams real-time updates of the workflow execution using Server-Sent Events."""
    wf_id_str = str(id)
    if wf_id_str not in active_streams:
        # Fallback: if pipeline is not active, return a one-off response of final status
        async def single_event_generator():
            yield "data: {\"status\": \"completed\", \"message\": \"Workflow is already complete\"}\n\n"
        return StreamingResponse(single_event_generator(), media_type="text/event-stream")

    queue = active_streams[wf_id_str]

    async def event_generator():
        try:
            while True:
                msg = await queue.get()
                if msg is None:
                    # Clean up
                    active_streams.pop(wf_id_str, None)
                    yield "data: {\"status\": \"done\"}\n\n"
                    break
                yield f"data: {json.dumps(msg)}\n\n"
        except asyncio.CancelledError:
            # Client disconnected
            active_streams.pop(wf_id_str, None)
            logger.info(f"SSE stream client disconnected for workflow {wf_id_str}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/{id}/approve", response_model=WorkflowResponse)
async def approve_workflow(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.DOCTOR, Role.ADMIN)),
):
    """Manually approve a workflow in awaiting_approval state."""
    wf = await workflow_repo.get(db, id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status != WorkflowStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Workflow is not in awaiting_approval state")
    
    updated = await workflow_repo.update(db, db_obj=wf, obj_in={"status": WorkflowStatus.APPROVED})
    return updated

@router.post("/{id}/reject", response_model=WorkflowResponse)
async def reject_workflow(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.DOCTOR, Role.ADMIN)),
):
    """Manually reject a workflow in awaiting_approval state."""
    wf = await workflow_repo.get(db, id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status != WorkflowStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Workflow is not in awaiting_approval state")
    
    updated = await workflow_repo.update(db, db_obj=wf, obj_in={"status": WorkflowStatus.REJECTED})
    return updated


@router.patch("/{id}/fields", response_model=WorkflowResponse)
async def update_workflow_fields(
    id: uuid.UUID,
    request: WorkflowFieldsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates the extracted fields in workflow.result_data["fields"].
    Recalculates quality score.
    """
    from sqlalchemy.orm.attributes import flag_modified
    
    wf = await workflow_repo.get(db, id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not wf.result_data:
        raise HTTPException(status_code=400, detail="Workflow does not have result data")
        
    # Update the fields
    if "fields" not in wf.result_data:
        wf.result_data["fields"] = {}
    
    for k, v in request.fields.items():
        wf.result_data["fields"][k] = v
        
    flag_modified(wf, "result_data")
    
    # Recalculate quality score
    clinical_record = await workflow_repo.get_clinical_record(db, workflow_id=id)
    confidence = clinical_record.confidence_score if (clinical_record and clinical_record.confidence_score is not None) else 1.0
    
    deductions = 0
    for key, val in wf.result_data["fields"].items():
        if val is None or str(val).strip() == "" or str(val).strip().upper() == "N/A":
            deductions += 15
            
    quality_score = max(0.0, min(100.0, (confidence * 100.0) - deductions))
    wf.quality_score = quality_score
    
    # Audit log creation for fields edit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="EDIT_FIELDS",
        patient_id=wf.patient_id,
        workflow_id=wf.id,
        resource_type="workflow",
        resource_id=str(wf.id)
    )
    db.add(audit_log)
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    
    return wf


@router.get("/{id}/export-pdf")
async def export_workflow_pdf(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and streams the prior authorization PDF report.
    """
    wf = await workflow_repo.get(db, id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not wf.result_data:
        raise HTTPException(status_code=400, detail="Workflow does not have result data")
        
    fields = wf.result_data.get("fields", {})
    payer_type = wf.payer_type
    quality_score = wf.quality_score or 0.0
    patient_id = wf.patient_id

    # Log EXPORT_PDF audit log and commit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="EXPORT_PDF",
        patient_id=wf.patient_id,
        workflow_id=wf.id,
        resource_type="workflow",
        resource_id=str(wf.id)
    )
    db.add(audit_log)
    await db.commit()

    # Look up active template matching workflow's payer_type case-insensitively
    template = None
    if payer_type:
        result = await db.execute(
            select(PATemplate).where(
                PATemplate.is_active == True,
                func.lower(PATemplate.name) == payer_type.lower()
            )
        )
        template = result.scalars().first()
        
        if not template:
            result = await db.execute(
                select(PATemplate).where(
                    PATemplate.is_active == True,
                    func.lower(PATemplate.name).contains(payer_type.lower())
                )
            )
            template = result.scalars().first()
            
        if not template:
            result = await db.execute(
                select(PATemplate).where(PATemplate.is_active == True)
            )
            active_templates = result.scalars().all()
            for t in active_templates:
                if t.name.lower() in payer_type.lower() or payer_type.lower() in t.name.lower():
                    template = t
                    break

    # If matching template exists: overlay on template
    if template:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from pypdf import PdfReader, PdfWriter
            
            template_bytes = base64.b64decode(template.file_content)
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=letter)
            
            default_coordinates = {
                "diagnosis_code": (100, 600),
                "procedure_code": (100, 550),
                "prior_treatments": (100, 500),
                "clinical_notes": (100, 450),
                "patient_id": (100, 700),
                "member_id": (100, 650),
                "treating_physician": (100, 400),
                "ma_the_bhyt": (100, 600),
                "ma_icd10": (100, 550),
                "don_vi_kham": (100, 500),
            }
            
            field_coords = {}
            field_coords.update(default_coordinates)
            
            if isinstance(template.fields, dict):
                for field_key, field_val in template.fields.items():
                    if isinstance(field_val, dict) and "x" in field_val and "y" in field_val:
                        field_coords[field_key] = (float(field_val["x"]), float(field_val["y"]))
            elif isinstance(template.fields, list):
                for item in template.fields:
                    if isinstance(item, dict) and "name" in item and "x" in item and "y" in item:
                        field_coords[item["name"]] = (float(item["x"]), float(item["y"]))
            
            wf_metadata = wf.result_data.get("metadata", {}) if wf.result_data else {}
            wf_coords = wf_metadata.get("coordinates", {}) if isinstance(wf_metadata, dict) else {}
            if isinstance(wf_coords, dict):
                for field_key, field_val in wf_coords.items():
                    if isinstance(field_val, (list, tuple)) and len(field_val) == 2:
                        field_coords[field_key] = (float(field_val[0]), float(field_val[1]))
                    elif isinstance(field_val, dict) and "x" in field_val and "y" in field_val:
                        field_coords[field_key] = (float(field_val["x"]), float(field_val["y"]))
                        
            y_fallback = 500
            for field_name, field_value in fields.items():
                if field_value is None:
                    field_value = "N/A"
                if field_name in field_coords:
                    x, y = field_coords[field_name]
                else:
                    x, y = 100, y_fallback
                    y_fallback -= 30
                c.setFont("Helvetica", 10)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(x, y, str(field_value))
                
            # Stamp OFFICIAL APPROVED (green) or DRAFT (red)
            if wf.status == WorkflowStatus.APPROVED or wf.status == "approved":
                stamp_text = "OFFICIAL APPROVED"
                c.setFillColorRGB(0.0, 0.6, 0.0)
            else:
                stamp_text = "DRAFT"
                c.setFillColorRGB(0.8, 0.0, 0.0)
                
            c.setFont("Helvetica-Bold", 36)
            c.saveState()
            c.translate(300, 400)
            c.rotate(30)
            c.drawCentredString(0, 0, stamp_text)
            c.restoreState()
            
            c.save()
            packet.seek(0)
            
            new_pdf = PdfReader(packet)
            canvas_page = new_pdf.pages[0]
            
            template_reader = PdfReader(io.BytesIO(template_bytes))
            writer = PdfWriter()
            
            template_page = template_reader.pages[0]
            template_page.merge_page(canvas_page)
            writer.add_page(template_page)
            
            for i in range(1, len(template_reader.pages)):
                writer.add_page(template_reader.pages[i])
                
            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            pdf_bytes = output_buffer.getvalue()
            
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=prior_auth_{id}.pdf"}
            )
        except Exception as e:
            logger.error(f"Failed to generate template-based PDF: {e}", exc_info=True)

    # Fallback/No template: draw plain text PDF report
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Prior Authorization Report")
        
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 80, f"Workflow ID: {str(wf.id)}")
        c.drawString(50, height - 95, f"Patient ID: {patient_id}")
        c.drawString(50, height - 110, f"Payer: {payer_type or 'N/A'}")
        c.drawString(50, height - 125, f"Quality Score: {quality_score:.1f}%")
        
        c.drawString(50, height - 155, "Extracted Fields:")
        y = height - 175
        for key, val in fields.items():
            c.drawString(70, y, f"{key}: {val or 'N/A'}")
            y -= 15
            if y < 100:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 50
                
            # Stamp OFFICIAL APPROVED (green) or DRAFT (red)
        if wf.status == WorkflowStatus.APPROVED or wf.status == "approved":
            stamp_text = "OFFICIAL APPROVED"
            c.setFillColorRGB(0.0, 0.6, 0.0)
        else:
            stamp_text = "DRAFT"
            c.setFillColorRGB(0.8, 0.0, 0.0)
            
        c.setFont("Helvetica-Bold", 36)
        c.saveState()
        c.translate(300, 400)
        c.rotate(30)
        c.drawCentredString(0, 0, stamp_text)
        c.restoreState()
        
        c.save()
        pdf_bytes = buffer.getvalue()
    except Exception:
        # Fallback to raw PDF generation without reportlab
        lines = [
            "Prior Authorization Report",
            "==========================",
            f"Workflow ID: {str(wf.id)}",
            f"Patient ID: {patient_id}",
            f"Payer: {payer_type or 'N/A'}",
            f"Quality Score: {quality_score:.1f}%",
            "",
            "Extracted Fields:",
        ]
        for key, val in fields.items():
            lines.append(f"  {key}: {val or 'N/A'}")
            
        stream_content = b"BT\n/F1 12 Tf\n14 Tl\n50 750 Td\n"
        for line in lines:
            escaped_line = line.replace("(", "\\(").replace(")", "\\)")
            stream_content += f"({escaped_line}) Tj T*\n".encode("utf-8")
        stream_content += b"ET\n"
        
        obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj2 = b"<< /Type /Pages /Kids [ 3 0 R ] /Count 1 >>"
        obj3 = b"<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [ 0 0 612 792 ] /Contents 5 0 R >>"
        obj4 = b"<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Courier >> >> >>"
        obj5 = f"<< /Length {len(stream_content)} >>\nstream\n".encode("utf-8") + stream_content + b"\nendstream"
        
        all_objs = [obj1, obj2, obj3, obj4, obj5]
        
        pdf_bytes = b"%PDF-1.4\n"
        offsets = {}
        for i, obj in enumerate(all_objs, 1):
            offsets[i] = len(pdf_bytes)
            pdf_bytes += f"{i} 0 obj\n".encode("utf-8") + obj + b"\nendobj\n"
            
        xref_pos = len(pdf_bytes)
        pdf_bytes += b"xref\n"
        pdf_bytes += f"0 {len(all_objs) + 1}\n".encode("utf-8")
        pdf_bytes += b"0000000000 65535 f \n"
        for i in range(1, len(all_objs) + 1):
            pdf_bytes += f"{offsets[i]:010d} 00000 n \n".encode("utf-8")
            
        pdf_bytes += b"trailer\n"
        pdf_bytes += f"<< /Size {len(all_objs) + 1} /Root 1 0 R >>\n".encode("utf-8")
        pdf_bytes += b"startxref\n"
        pdf_bytes += f"{xref_pos}\n".encode("utf-8")
        pdf_bytes += b"%%EOF\n"
        
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=prior_auth_{id}.pdf"}
    )


def extract_text_from_file(file_name: str, content: bytes) -> str:
    ext = file_name.split(".")[-1].lower()
    if ext == "txt":
        return content.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    elif ext == "docx":
        import docx
        import io
        doc = docx.Document(io.BytesIO(content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    elif ext in ["png", "jpg", "jpeg", "gif", "bmp"]:
        # Mock OCR extraction for clinical demo
        return (
            "PATIENT DEMOGRAPHICS:\n"
            "Name: Jane Doe\n"
            "Date of Birth: 12/05/1980\n"
            "Insurance Provider: Aetna\n"
            "Policy Number: AET-88992-XYZ\n\n"
            "CLINICAL FINDINGS & DIAGNOSES:\n"
            "Chief Complaint: Persistent lower back pain radiating down left thigh for 3 weeks.\n"
            "Diagnosis: Herniated lumbar disc at L4-L5 with radiculopathy (ICD-10: M54.5, M51.36).\n"
            "Planned Procedure: Physical therapy sessions, including therapeutic exercise (CPT: 97110).\n"
            "Prior Treatments attempted: Patient tried oral NSAIDs (Ibuprofen) for 2 weeks with minimal relief."
        )
    else:
        raise ValueError(f"Unsupported file format: .{ext}. Please upload .txt, .pdf, .docx, or an image.")


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Accepts a clinical file upload (PDF, DOCX, TXT, Image) and extracts its text contents
    to populate the prior auth notes field.
    """
    try:
        content = await file.read()
        extracted_text = extract_text_from_file(file.filename, content)
        return {"text": extracted_text}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error reading file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
