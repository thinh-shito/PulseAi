import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings

logger = logging.getLogger(__name__)

# Default fields for fallback/seeding
DEFAULT_FIELDS = {
    "prior_authorization": [
        {"name": "patient_name", "type": "str", "description": "Full name of the patient"},
        {"name": "date_of_birth", "type": "str", "description": "Date of birth of the patient"},
        {"name": "insurance_id", "type": "str", "description": "Insurance policy or member ID number"},
        {"name": "diagnosis", "type": "str", "description": "Primary diagnosis or ICD code"},
        {"name": "treatment_requested", "type": "str", "description": "Requested procedure, medication, or treatment"},
        {"name": "clinical_justification", "type": "str", "description": "Medical necessity or clinical justification for the request"},
    ],
    "discharge_summary": [
        {"name": "patient_name", "type": "str", "description": "Full name of the patient"},
        {"name": "admission_date", "type": "str", "description": "Date the patient was admitted"},
        {"name": "discharge_date", "type": "str", "description": "Date the patient was discharged"},
        {"name": "discharge_diagnosis", "type": "str", "description": "Final diagnosis at the time of discharge"},
        {"name": "hospital_course", "type": "str", "description": "Summary of the treatment and course of hospitalization"},
        {"name": "discharge_medications", "type": "str", "description": "List of medications prescribed upon discharge"},
        {"name": "followup_instructions", "type": "str", "description": "Instructions for follow-up appointments and care"},
    ],
    "shift_handover_report": [
        {"name": "patient_name", "type": "str", "description": "Full name of the patient"},
        {"name": "ward_room", "type": "str", "description": "Ward and room number"},
        {"name": "current_condition", "type": "str", "description": "Current clinical status and stability of the patient"},
        {"name": "recent_treatments", "type": "str", "description": "Treatments or procedures administered during the shift"},
        {"name": "pending_tasks", "type": "str", "description": "Pending tests, tasks, or monitoring for the next shift"},
        {"name": "critical_concerns", "type": "str", "description": "Any critical alerts or warning signs to watch out for"},
    ],
    "transfer_letter": [
        {"name": "patient_name", "type": "str", "description": "Full name of the patient"},
        {"name": "transferring_facility", "type": "str", "description": "Name of the facility transferring the patient"},
        {"name": "receiving_facility", "type": "str", "description": "Name of the facility receiving the patient"},
        {"name": "reason_for_transfer", "type": "str", "description": "Clinical reason for transferring the patient"},
        {"name": "clinical_summary", "type": "str", "description": "Summary of patient's current condition and treatment received"},
        {"name": "active_problems", "type": "str", "description": "Active medical problems or diagnoses"},
    ]
}

# A simple base64 encoded empty/blank 1-page PDF to use as fallback template
MOCK_PDF_BASE64 = (
    "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIg"
    "MCBvYmoKPDYKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBv"
    "YmoKPDYKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA1OTUgODQyXQovQ29u"
    "dGVudHMgNCAwIFIKL1Jlc291cmNlcyA8PAovRm9udCA8PAovRjEgNSAwIFIKPj4KPj4KPj4KZW5kb2Jq"
    "CjQgMCBvYmoKPDwKL0xlbmd0aCA1NQo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZCAoUGVs"
    "c2VBSSBNZWRpY2FsIERvY3VtZW50KSBUagogRVQKZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCjw8Ci9U"
    "eXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL0hlbHZldGljYQo+PgplbmRvYmoKeHJl"
    "ZgowIDYKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTYgMDAw"
    "MDAgbiAKMDAwMDAwMDExMSAwMDAwMCBuIAowMDAwMDAwMjQ0IDAwMDAwIG4gCjAwMDAwMDAzNTYgMDAw"
    "MDAgbiAKdHJhaWxlcgo8PAovU2l6ZSA2Ci9Sb290IDEgMCBSCj4+CnN0YXJ0eHJlZgogNDQxCiUlRU9G"
)

def get_connection():
    """Establishes connection to the PostgreSQL database."""
    return psycopg2.connect(settings.database_url)

def init_db():
    """Initializes tables and seeds them if necessary."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # Create document_fields table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_fields (
                    id SERIAL PRIMARY KEY,
                    template_name VARCHAR(255) UNIQUE NOT NULL,
                    fields JSONB NOT NULL
                );
            """)
            # Create document_templates table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_templates (
                    id SERIAL PRIMARY KEY,
                    template_name VARCHAR(255) UNIQUE NOT NULL,
                    file_content TEXT NOT NULL,
                    file_extension VARCHAR(10) NOT NULL
                );
            """)
            conn.commit()

            # Seed tables if they are empty
            for name, fields in DEFAULT_FIELDS.items():
                cur.execute(
                    "SELECT COUNT(*) FROM document_fields WHERE template_name = %s",
                    (name,)
                )
                if cur.fetchone()[0] == 0:
                    cur.execute(
                        "INSERT INTO document_fields (template_name, fields) VALUES (%s, %s)",
                        (name, json.dumps(fields))
                    )
                    logger.info(f"Seeded document_fields for {name}")

                cur.execute(
                    "SELECT COUNT(*) FROM document_templates WHERE template_name = %s",
                    (name,)
                )
                if cur.fetchone()[0] == 0:
                    cur.execute(
                        "INSERT INTO document_templates (template_name, file_content, file_extension) VALUES (%s, %s, %s)",
                        (name, MOCK_PDF_BASE64, "pdf")
                    )
                    logger.info(f"Seeded document_templates for {name}")
            
            conn.commit()
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

def get_fields_from_db(template_name: str) -> list:
    """Loads a list of fields from DB based on template_name."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT fields FROM document_fields WHERE template_name = %s",
                (template_name,)
            )
            row = cur.fetchone()
            if row:
                return row["fields"]
    except Exception as e:
        logger.error(f"Error fetching fields for {template_name} from DB: {e}")
    finally:
        if conn:
            conn.close()

    # Fallback to hardcoded defaults
    logger.info(f"Using default fallback fields for {template_name}")
    return DEFAULT_FIELDS.get(template_name, [])

def get_template_from_db(template_name: str) -> tuple:
    """Loads template file content (bytes) and extension from DB based on template_name."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT file_content, file_extension FROM document_templates WHERE template_name = %s",
                (template_name,)
            )
            row = cur.fetchone()
            if row:
                import base64
                file_bytes = base64.b64decode(row["file_content"])
                return file_bytes, row["file_extension"]
    except Exception as e:
        logger.error(f"Error fetching template for {template_name} from DB: {e}")
    finally:
        if conn:
            conn.close()

    # Fallback to mock PDF template
    logger.info(f"Using default fallback template for {template_name}")
    import base64
    return base64.b64decode(MOCK_PDF_BASE64), "pdf"