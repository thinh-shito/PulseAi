"""
Mock Tools — Sprint 1/2/3 Development & Testing

Use these mocks to test the backend without calling real APIs.
This prevents costs and allows offline development.
"""
from typing import Optional
from unittest.mock import MagicMock


# ─── Mock Insurance DB ──────────────────────────────────────────────────────

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


# ─── Mock Clinical Extraction Results ──────────────────────────────────────

MOCK_CLINICAL_RESULT = {
    "icd10_codes": ["M54.16", "G43.909"],
    "summary": "Patient presents with lumbar radiculopathy and chronic migraine.",
    "confidence_score": 0.94,
    "payer_type": "BCBS",
}

MOCK_CLINICAL_RESULT_LOW_QUALITY = {
    "icd10_codes": ["M54.16"],
    "summary": "Incomplete extraction.",
    "confidence_score": 0.61,
    "payer_type": "Aetna",
}


# ─── Mock PHI Filter ────────────────────────────────────────────────────────

def mock_phi_anonymize(text: str) -> str:
    """Mock PHI filter that replaces common PII patterns."""
    import re
    text = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[PERSON]', text)
    text = re.sub(r'\b\d{10,12}\b', '[ID_NUMBER]', text)
    text = re.sub(r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b', '[PHONE]', text)
    return text