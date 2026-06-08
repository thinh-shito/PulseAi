import pytest
from unittest.mock import patch
from app.services_ai.state import AgentState
from app.services_ai.nodes.clinical_node import clinical_node
from app.services_ai.nodes.payer_router_node import payer_router_node
from app.services_ai.nodes.form_filler_node import fill_form_generic, bcbs_form_node
from app.services_ai.nodes.quality_node import quality_node
from app.services_ai.graph_builder import build_graph
from tests.mocks.mock_tools import get_mock_llm

def test_clinical_node_success():
    mock_response = '{"icd10_codes": ["M54.16"], "summary": "Lumbar radiculopathy", "confidence_score": 0.98}'
    mock_llm = get_mock_llm(mock_response)
    
    state = {
        "patient_id": "test-patient-uuid",
        "raw_text": "Patient has severe back pain due to lumbar radiculopathy.",
        "workflow_id": "test-workflow-uuid",
        "retry_count": 0
    }
    
    with patch("app.services_ai.nodes.clinical_node.get_llm", return_value=mock_llm):
        result = clinical_node(state)
        
    assert result["processing_status"] == "routing"
    assert result["icd10_codes"] == ["M54.16"]
    assert result["summary"] == "Lumbar radiculopathy"
    assert result["confidence_score"] == 0.98
    assert result["error_message"] is None

def test_payer_router_node():
    # Test BCBS detection
    state = {"raw_text": "Patient has BCBS insurance.", "summary": ""}
    result = payer_router_node(state)
    assert result["payer_type"] == "BCBS"
    
    # Test Aetna detection
    state = {"raw_text": "", "summary": "We need Aetna authorization."}
    result = payer_router_node(state)
    assert result["payer_type"] == "Aetna"

def test_form_filler_node():
    mock_response = '{"diagnosis_code": "M54.16", "procedure_code": "97110", "treating_physician": "Dr. Smith"}'
    mock_llm = get_mock_llm(mock_response)
    
    state = {
        "summary": "Lumbar radiculopathy",
        "raw_text": "Dr. Smith requests prior auth.",
        "payer_type": "BCBS"
    }
    
    with patch("app.services_ai.nodes.form_filler_node.get_llm", return_value=mock_llm):
        result = bcbs_form_node(state)
        
    assert result["processing_status"] == "quality_check"
    assert result["prior_auth_form"]["carrier"] == "BCBS"
    assert result["prior_auth_form"]["fields"]["diagnosis_code"] == "M54.16"

def test_quality_node():
    state = {
        "confidence_score": 0.96,
        "prior_auth_form": {
            "fields": {
                "diagnosis_code": "M54.16",
                "procedure_code": "97110",
                "treating_physician": "Dr. Smith"
            }
        }
    }
    result = quality_node(state)
    assert result["quality_score"] == 96.0
    assert result["processing_status"] == "approved"
    
    # Deductions for missing fields
    state["prior_auth_form"]["fields"]["procedure_code"] = "N/A"
    result = quality_node(state)
    assert result["quality_score"] == 81.0
    assert result["processing_status"] == "awaiting_approval"

@pytest.mark.asyncio
async def test_full_graph_execution():
    mock_clinical = '{"icd10_codes": ["M54.16"], "summary": "Lumbar radiculopathy", "confidence_score": 0.98}'
    mock_form = '{"diagnosis_code": "M54.16", "procedure_code": "97110", "treating_physician": "Dr. Jack"}'
    
    graph = build_graph()
    
    initial_state = {
        "patient_id": "test-uuid",
        "raw_text": "Patient John Doe has back pain. Insurance is BCBS.",
        "workflow_id": "workflow-uuid",
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
    
    # We mock get_llm inside nodes.clinical_node and nodes.form_filler_node
    with patch("app.services_ai.nodes.clinical_node.get_llm", return_value=get_mock_llm(mock_clinical)), \
         patch("app.services_ai.nodes.form_filler_node.get_llm", return_value=get_mock_llm(mock_form)):
        final_state = await graph.ainvoke(initial_state)
        
    assert final_state["payer_type"] == "BCBS"
    assert final_state["quality_score"] == 98.0
    assert final_state["processing_status"] == "approved"
    assert final_state["prior_auth_form"]["fields"]["procedure_code"] == "97110"
