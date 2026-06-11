from app.services_ai.state import AgentState
from app.services_ai.nodes.clinical_node import clinical_node
from app.services_ai.nodes.payer_router_node import payer_router_node
from app.services_ai.nodes.form_filler_node import (
    bcbs_form_node,
    aetna_form_node,
    uhc_form_node,
    bhyt_form_node,
)
from app.services_ai.nodes.quality_node import quality_node


def route_by_payer(state: AgentState) -> str:
    """Determine the next node path based on payer type."""
    payer = state.get("payer_type")
    if payer == "BCBS":
        return "bcbs"
    elif payer == "Aetna":
        return "aetna"
    elif payer == "UHC":
        return "uhc"
    elif payer == "BHYT_VN":
        return "bhyt"
    return "quality"


def build_graph():
    """
    Builds and compiles the prior authorization LangGraph StateGraph.
    Uses lazy imports for LangGraph packages to keep startup lightweight.
    """
    from langgraph.graph import StateGraph, END

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("clinical", clinical_node)
    workflow.add_node("router", payer_router_node)
    workflow.add_node("bcbs", bcbs_form_node)
    workflow.add_node("aetna", aetna_form_node)
    workflow.add_node("uhc", uhc_form_node)
    workflow.add_node("bhyt", bhyt_form_node)
    workflow.add_node("quality", quality_node)

    # Set entry point
    workflow.set_entry_point("clinical")

    # Define simple edges
    workflow.add_edge("clinical", "router")

    # Define conditional branching edges
    workflow.add_conditional_edges(
        "router",
        route_by_payer,
        {
            "bcbs": "bcbs",
            "aetna": "aetna",
            "uhc": "uhc",
            "bhyt": "bhyt",
            "quality": "quality",
        }
    )

    # Link all form fillers to quality check
    workflow.add_edge("bcbs", "quality")
    workflow.add_edge("aetna", "quality")
    workflow.add_edge("uhc", "quality")
    workflow.add_edge("bhyt", "quality")

    # Quality check goes to the end
    workflow.add_edge("quality", END)

    return workflow.compile()
