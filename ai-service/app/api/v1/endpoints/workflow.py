"""
AI Workflow endpoint — accepts workflow processing requests from the backend.
Runs the LangGraph prior authorization pipeline and returns results.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.domain.phi_filter import anonymize_phi
from app.services_ai.graph_builder import build_graph

router = APIRouter()

# Compile graph once at module level (lazy on first request)
_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


class WorkflowRequest(BaseModel):
    workflow_id: str
    patient_id: str
    raw_text: str
    payer_hint: Optional[str] = None


class WorkflowResponse(BaseModel):
    workflow_id: str
    processing_status: str
    icd10_codes: list[str] = []
    summary: str = ""
    confidence_score: float = 0.0
    payer_type: Optional[str] = None
    quality_score: Optional[float] = None
    prior_auth_form: Optional[dict] = None
    error_message: Optional[str] = None


def _verify_internal_key(x_internal_api_key: Optional[str]) -> None:
    """Verify internal API key for service-to-service communication."""
    if settings.is_production and x_internal_api_key != settings.internal_api_key:
        raise HTTPException(status_code=403, detail="Invalid internal API key")


@router.post("/workflow/process", response_model=WorkflowResponse)
async def process_workflow(
    request: WorkflowRequest,
    x_internal_api_key: Optional[str] = Header(None),
):
    """
    Process a prior authorization workflow through the AI pipeline.
    Called by the NestJS backend service.
    """
    _verify_internal_key(x_internal_api_key)

    # Anonymize PHI before processing
    anonymized_text = anonymize_phi(request.raw_text)

    # Build initial state
    initial_state = {
        "patient_id": request.patient_id,
        "raw_text": anonymized_text,
        "workflow_id": request.workflow_id,
        "icd10_codes": [],
        "summary": "",
        "confidence_score": 0.0,
        "payer_type": request.payer_hint,
        "quality_score": None,
        "prior_auth_form": None,
        "processing_status": "pending",
        "error_message": None,
        "retry_count": 0,
    }

    try:
        graph = _get_graph()
        result = graph.invoke(initial_state)

        return WorkflowResponse(
            workflow_id=result.get("workflow_id", request.workflow_id),
            processing_status=result.get("processing_status", "failed"),
            icd10_codes=result.get("icd10_codes", []),
            summary=result.get("summary", ""),
            confidence_score=result.get("confidence_score", 0.0),
            payer_type=result.get("payer_type"),
            quality_score=result.get("quality_score"),
            prior_auth_form=result.get("prior_auth_form"),
            error_message=result.get("error_message"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI pipeline error: {str(e)}"
        )