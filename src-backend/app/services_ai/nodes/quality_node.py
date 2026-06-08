from app.services_ai.state import AgentState

def quality_node(state: AgentState) -> dict:
    """
    Quality Node — evaluates prior auth extraction and form filling quality.
    If quality_score < 95, status changes to "awaiting_approval".
    Otherwise, status changes to "approved".
    """
    confidence = state.get("confidence_score", 1.0)
    base_score = confidence * 100.0
    
    # Deduct points if fields are missing or N/A
    form = state.get("prior_auth_form")
    deductions = 0
    if form and isinstance(form, dict):
        fields = form.get("fields", {})
        if isinstance(fields, dict):
            for val in fields.values():
                if not val or val == "N/A":
                    deductions += 15
                    
    quality_score = max(0.0, min(100.0, base_score - deductions))
    
    status = "approved" if quality_score >= 95 else "awaiting_approval"
    
    return {
        "quality_score": quality_score,
        "processing_status": status
    }
