from app.services_ai.state import AgentState


def payer_router_node(state: AgentState) -> dict:
    """
    Payer Router Node — detects the insurance carrier from the text and summary.
    Supported: BCBS, Aetna, UHC, BHYT_VN.
    """
    search_text = f"{state.get('raw_text', '')} {state.get('summary', '')}".lower(
    )

    payer_type = None
    if "bcbs" in search_text or "blue cross" in search_text or "blue shield" in search_text:
        payer_type = "BCBS"
    elif "aetna" in search_text:
        payer_type = "Aetna"
    elif "uhc" in search_text or "unitedhealthcare" in search_text or "united healthcare" in search_text:
        payer_type = "UHC"
    elif "bhyt" in search_text or "bảo hiểm y tế" in search_text or "bao hiem y te" in search_text:
        payer_type = "BHYT_VN"

    return {
        "payer_type": payer_type,
        "processing_status": "routing"
    }
