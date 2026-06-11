from typing import Literal, Optional, TypedDict


class AgentState(TypedDict):
    """
    Central state object passed between all LangGraph nodes.

    SECURITY NOTE:
    - raw_text must be anonymized via PHIFilter BEFORE being stored here
    - patient_id is always a UUID/anonymous token, NEVER a real name
    - All fields typed strictly — LangGraph enforces this at runtime
    """

    # Input
    patient_id: str                  # UUID — never real patient name
    raw_text: str                    # PHI-anonymized text from doctor's note
    workflow_id: str                 # UUID of the Workflow record in DB

    # Clinical extraction output
    icd10_codes: list[str]           # e.g. ["M54.16", "G43.909"]
    summary: str                     # Clinical summary (anonymized)
    confidence_score: float          # 0.0 to 1.0

    # Routing
    # "BCBS" | "Aetna" | "UHC" | "BHYT_VN" | None
    payer_type: Optional[str]

    # Quality
    # 0 to 100 — below 95 triggers human review
    quality_score: Optional[float]

    # Form output
    prior_auth_form: Optional[dict]  # Filled PA form fields

    # Processing state
    processing_status: Literal[
        "pending",
        "extracting",
        "routing",
        "filling_form",
        "quality_check",
        "awaiting_approval",
        "approved",
        "rejected",
        "completed",
        "failed",
    ]

    # Error handling
    error_message: Optional[str]
    retry_count: int
