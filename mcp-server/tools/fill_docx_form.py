"""Tool: fill_docx_form — Fill a DOCX prior authorization template with extracted data."""

import base64
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Default template path inside the container
TEMPLATES_DIR = Path(os.environ.get("TEMPLATES_DIR", "/app/templates"))


def fill_docx_form(data: str, template_name: str = "prior_authorization_template.docx") -> dict:
    """
    Fill a prior authorization DOCX template with extracted clinical data.

    Args:
        data: JSON string with field values (output from generate_prior_auth)
        template_name: Name of the template file in the templates directory

    Returns:
        dict with 'filename' and 'content_base64' keys
    """
    try:
        field_values = json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in data parameter: {e}")

    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        # Fallback: look in the mcp-server directory tree
        base = Path(__file__).parent.parent
        candidates = list(base.rglob("*.docx"))
        template_candidates = [p for p in candidates if "template" in p.name.lower()]
        if not template_candidates:
            raise FileNotFoundError(
                f"Template '{template_name}' not found in {TEMPLATES_DIR}. "
                "Please ensure the templates directory is mounted correctly."
            )
        template_path = template_candidates[0]
        logger.warning(f"Template not found at expected path; using fallback: {template_path}")

    logger.info(f"Filling DOCX template: {template_path}")

    from utils.document_processor import fill_docx_template

    filled_bytes = fill_docx_template(str(template_path), field_values)

    # Derive output filename from patient name if available
    patient_name = field_values.get("patient_name", "").strip().replace(" ", "_") or "patient"
    filename = f"prior_authorization_{patient_name}.docx"

    content_b64 = base64.b64encode(filled_bytes).decode("utf-8")

    logger.info(f"DOCX form filled successfully: {filename} ({len(filled_bytes)} bytes)")

    return {
        "filename": filename,
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "content_base64": content_b64,
        "message": f"Prior authorization form generated successfully: {filename}",
    }