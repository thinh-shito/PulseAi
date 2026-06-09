import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db, get_session_factory
from app.core.security import Role
from app.domain.models.user import User
from app.domain.models.workflow import Workflow, WorkflowStatus
from app.infra.repositories.workflow_repository import workflow_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])

# In-memory queues for real-time SSE updates
active_streams: Dict[str, asyncio.Queue] = {}

# ─── Pydantic Schemas ────────────────────────────────────────────────────────



class WorkflowStartRequest(BaseModel):
    patient_id: str = Field(..., json_schema_extra={"example": "patient-123"})
    raw_text: str = Field(..., json_schema_extra={"example": "Patient John Doe has back pain. Insurance: BCBS."})

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
