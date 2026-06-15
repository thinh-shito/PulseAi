"""Tool: generate_prior_auth — Extract prior authorization fields from patient notes."""

import json
import logging
import os
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

# Fields to extract for prior authorization
PRIOR_AUTH_FIELDS = [
    {"name": "patient_name", "description": "Full name of the patient"},
    {"name": "patient_dob", "description": "Patient date of birth (MM/DD/YYYY)"},
    {"name": "patient_id", "description": "Patient ID or MRN number"},
    {"name": "patient_insurance_id", "description": "Patient insurance member ID"},
    {"name": "patient_insurance_plan", "description": "Insurance plan name"},
    {"name": "patient_address", "description": "Patient home address"},
    {"name": "patient_phone", "description": "Patient phone number"},
    {"name": "provider_name", "description": "Requesting physician or provider full name"},
    {"name": "provider_npi", "description": "Provider NPI number"},
    {"name": "provider_phone", "description": "Provider phone number"},
    {"name": "provider_fax", "description": "Provider fax number"},
    {"name": "provider_address", "description": "Provider office address"},
    {"name": "diagnosis_code", "description": "Primary ICD-10 diagnosis code"},
    {"name": "diagnosis_description", "description": "Description of the primary diagnosis"},
    {"name": "requested_service", "description": "Service, procedure, or medication being requested"},
    {"name": "service_code", "description": "CPT or HCPCS code for the requested service"},
    {"name": "urgency", "description": "Urgency level: Routine, Urgent, or Emergent"},
    {"name": "clinical_justification", "description": "Clinical rationale and medical necessity for the request"},
    {"name": "prior_treatments", "description": "Previous treatments tried and their outcomes"},
    {"name": "start_date", "description": "Requested start date of service (MM/DD/YYYY)"},
]


def generate_prior_auth(patient_note: str) -> str:
    """
    Extract structured prior authorization fields from a patient clinical note.

    Args:
        patient_note: Text content of the patient note

    Returns:
        JSON string with extracted prior authorization fields
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    fields_description = "\n".join(
        f"- {f['name']}: {f['description']}" for f in PRIOR_AUTH_FIELDS
    )
    field_names = [f["name"] for f in PRIOR_AUTH_FIELDS]

    system_prompt = f"""You are a clinical data extraction specialist. Extract information from patient notes to fill a prior authorization form.

Extract the following fields from the patient note:
{fields_description}

Return a JSON object with exactly these keys: {json.dumps(field_names)}
If a field cannot be found in the note, use an empty string "".
Do not add extra fields. Return only valid JSON, no markdown code blocks."""

    logger.info("Calling OpenAI to extract prior auth fields from patient note")

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"## Patient Note\n\n{patient_note}"},
            ],
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content
        extracted = json.loads(result_text)

        # Ensure all expected fields are present
        for field in field_names:
            if field not in extracted:
                extracted[field] = ""

        logger.info(f"Successfully extracted {len(extracted)} prior auth fields")
        return json.dumps(extracted, indent=2)

    except Exception as e:
        logger.error(f"Error extracting prior auth fields: {e}")
        raise