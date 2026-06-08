import json
import re
from app.services_ai.state import AgentState
from app.services_ai.llm_factory import get_llm
from app.domain.phi_filter import anonymize_phi

def clinical_node(state: AgentState) -> dict:
    """
    Clinical Node — extracts ICD-10 codes and a clinical summary from the raw text.
    Ensures PHI is de-identified BEFORE calling the LLM.
    """
    update = {
        "processing_status": "extracting",
        "error_message": None
    }
    
    raw_text = state.get("raw_text", "")
    if not raw_text:
        return {
            "processing_status": "failed",
            "error_message": "Empty raw_text input"
        }
        
    # De-identify PHI first
    anonymized = anonymize_phi(raw_text)
    
    prompt = f"""You are a clinical extraction assistant.
Extract any ICD-10 codes mentioned or relevant to the medical symptoms, and provide a short clinical summary.
Input text: {anonymized}

You MUST return a JSON object with these keys:
- "icd10_codes": a list of strings (e.g. ["M54.16"])
- "summary": a short clinical summary string
- "confidence_score": a float from 0.0 to 1.0 representing extraction confidence

Return only valid JSON. Do not write anything else.
"""
    try:
        llm = get_llm(temperature=0.0)
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # Clean markdown code block wraps if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n", "", content)
            content = re.sub(r"\n```$", "", content)
            content = content.strip()
            
        data = json.loads(content)
        update["icd10_codes"] = data.get("icd10_codes", [])
        update["summary"] = data.get("summary", "")
        update["confidence_score"] = float(data.get("confidence_score", 0.0))
        update["processing_status"] = "routing"
    except Exception as e:
        update["processing_status"] = "failed"
        update["error_message"] = f"Clinical extraction failed: {str(e)}"
        update["icd10_codes"] = []
        update["summary"] = ""
        update["confidence_score"] = 0.0
        
    return update
