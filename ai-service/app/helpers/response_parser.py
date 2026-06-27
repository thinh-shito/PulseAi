"""
Response Parser Helper.
"""
import json
import re
from typing import Any, Dict


def parse_json_response(response: Any) -> Dict[str, Any]:
    """
    Parse a JSON response from an LLM. Handles cases where the response is
    wrapped in markdown code blocks.
    """
    try:
        content = response.content.strip()
    except AttributeError:
        # Fallback if the response is already a string
        content = str(response).strip()

    # Clean markdown code block wraps if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n", "", content)
        content = re.sub(r"\n```$", "", content)
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON response", "raw_content": content}