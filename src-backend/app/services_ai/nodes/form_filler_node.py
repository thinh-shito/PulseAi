import json
import re
from app.services_ai.state import AgentState
from app.services_ai.llm_factory import get_llm
from app.domain.phi_filter import anonymize_phi

MOCK_INSURANCE_DB = {
    "BCBS": {
        "name": "Blue Cross Blue Shield",
        "form_template": "bcbs_prior_auth_v3.json",
        "required_fields": ["diagnosis_code", "procedure_code", "treating_physician"],
    },
    "Aetna": {
        "name": "Aetna Health",
        "form_template": "aetna_pa_2024.json",
        "required_fields": ["diagnosis_code", "clinical_notes", "prior_treatments"],
    },
    "UHC": {
        "name": "UnitedHealthcare",
        "form_template": "uhc_auth_form.json",
        "required_fields": ["member_id", "diagnosis_code", "procedure_code"],
    },
    "BHYT_VN": {
        "name": "Bảo hiểm Y tế Việt Nam",
        "form_template": "mau_05_byt_2024.json",
        "required_fields": ["ma_the_bhyt", "ma_icd10", "don_vi_kham"],
    },
}

def fill_form_generic(state: AgentState, carrier: str) -> dict:
    db_entry = MOCK_INSURANCE_DB.get(carrier, {})
    required = db_entry.get("required_fields", [])
    template = db_entry.get("form_template", "generic_form.json")
    
    raw_text = state.get("raw_text", "")
    anonymized = anonymize_phi(raw_text)
    summary = state.get("summary", "")
    
    prompt = f"""You are a medical billing assistant.
We are filling a prior authorization form for {carrier}.
Required fields to fill: {required}

Clinical summary of the patient:
{summary}

Raw doctor's notes (anonymized):
{anonymized}

Extract and fill values for the required fields.
Return a JSON object where the keys are exactly: {required}.
If a field cannot be found, set its value to "N/A" or a best-effort guess.
Return only valid JSON. Do not write anything else.
"""
    try:
        llm = get_llm(temperature=0.0)
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n", "", content)
            content = re.sub(r"\n```$", "", content)
            content = content.strip()
            
        form_data = json.loads(content)
    except Exception:
        # Fallback values
        form_data = {field: "N/A" for field in required}
        
    return {
        "prior_auth_form": {
            "template": template,
            "carrier": carrier,
            "fields": form_data
        },
        "processing_status": "quality_check"
    }

def bcbs_form_node(state: AgentState) -> dict:
    return fill_form_generic(state, "BCBS")

def aetna_form_node(state: AgentState) -> dict:
    return fill_form_generic(state, "Aetna")

def uhc_form_node(state: AgentState) -> dict:
    return fill_form_generic(state, "UHC")

def bhyt_form_node(state: AgentState) -> dict:
    return fill_form_generic(state, "BHYT_VN")
