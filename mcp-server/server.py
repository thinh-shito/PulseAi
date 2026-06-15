"""Clinical Assistant MCP Server — FastMCP with SSE transport."""

import logging
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Initialise FastMCP application
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Clinical Assistant",
    instructions=(
        "You are a clinical AI assistant. Use these tools to generate clinical documents "
        "such as prior authorization forms, handover reports, and discharge summaries. "
        "Always extract information accurately from the provided clinical notes."
    ),
)

# ---------------------------------------------------------------------------
# Tool: generate_prior_auth
# ---------------------------------------------------------------------------
@mcp.tool()
def generate_prior_auth(patient_note: str) -> str:
    """Extract structured prior authorization fields from a patient clinical note.

    Use this tool when the user wants to generate a prior authorization form.
    Pass the full text of the patient note as input.

    Args:
        patient_note: Full text content of the patient clinical note

    Returns:
        JSON string with all extracted prior authorization fields
    """
    from tools.generate_prior_auth import generate_prior_auth as _generate
    return _generate(patient_note)


# ---------------------------------------------------------------------------
# Tool: fill_docx_form
# ---------------------------------------------------------------------------
@mcp.tool()
def fill_docx_form(data: str, template_name: str = "prior_authorization_template.docx") -> dict:
    """Fill a prior authorization DOCX template with extracted clinical data.

    Use this tool AFTER generate_prior_auth. Pass the exact JSON output from
    generate_prior_auth as the data parameter.

    Args:
        data: JSON string with field values (exact output from generate_prior_auth)
        template_name: Name of the DOCX template file (default: prior_authorization_template.docx)

    Returns:
        dict with filename, mime_type, content_base64, and message
    """
    from tools.fill_docx_form import fill_docx_form as _fill
    return _fill(data, template_name)


# ---------------------------------------------------------------------------
# Tool: generate_handover_report
# ---------------------------------------------------------------------------
@mcp.tool()
def generate_handover_report(clinical_summary: str, patient_info: str = "") -> dict:
    """Generate a structured clinical handover report for shift transitions.

    Use this tool when a nurse or clinician needs to hand over patient care
    to the next shift. Provide a clinical summary of the patient's current status.

    Args:
        clinical_summary: Clinical summary text describing patient status this shift
        patient_info: Optional additional patient demographic or contextual information

    Returns:
        dict with report data, filename, mime_type, content_base64, and message
    """
    from tools.generate_handover_report import generate_handover_report as _generate
    return _generate(clinical_summary, patient_info)


# ---------------------------------------------------------------------------
# Tool: generate_discharge_summary
# ---------------------------------------------------------------------------
@mcp.tool()
def generate_discharge_summary(
    admission_note: str,
    treatment_course: str = "",
    discharge_plan: str = "",
) -> dict:
    """Generate a comprehensive hospital discharge summary document.

    Use this tool when a patient is being discharged. Provide admission notes,
    treatment course, and discharge plan. A formatted DOCX document will be created.

    Args:
        admission_note: Admission notes and presenting complaints
        treatment_course: Summary of treatment provided during hospitalization
        discharge_plan: Discharge plan including medications and follow-up instructions

    Returns:
        dict with summary data, filename, mime_type, content_base64, and message
    """
    from tools.generate_discharge_summary import generate_discharge_summary as _generate
    return _generate(admission_note, treatment_course, discharge_plan)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    transport = os.environ.get("MCP_TRANSPORT", "sse")

    logger.info(f"Starting Clinical Assistant MCP Server on {host}:{port} (transport={transport})")

    if transport == "sse":
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
