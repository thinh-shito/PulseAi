"""
LangGraph medical chat agent for the /chat API.

The agent uses the configured LLM (see chain.py) and a small set of safe tools:
- HIS medical document search through db-query-agent
- Prior authorization readiness assessment
- Clinical/payer text summarization
"""
from typing import Annotated, Any, AsyncIterator, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.core.chain import chat_agent_llm
from app.domain.phi_filter import anonymize_phi
from app.domain.tools.search_tool import search_medical_documents
from app.prompts.chat_prompt import MEDICAL_CHAT_SYSTEM_PROMPT


class ChatAgentState(TypedDict):
    """State passed between LangGraph chat-agent nodes."""

    messages: Annotated[List[AnyMessage], add_messages]
    session_id: Optional[str]


@tool
async def search_medical_documents_tool(query: str) -> Dict[str, Any]:
    """
    Search HIS/PostgreSQL medical documents and return sanitized findings.

    Use this when the user asks about patient records, prior authorization status,
    clinical notes, diagnoses, procedures, medications, insurance, or stored documents.
    """
    return await search_medical_documents(query=query)


@tool
def assess_prior_authorization_readiness(case_summary: str) -> Dict[str, Any]:
    """
    Assess whether a case summary appears ready for prior authorization submission.

    This is a lightweight checklist tool and does not replace payer policy review.
    """
    safe_summary = anonymize_phi(case_summary).lower()

    checklist = {
        "diagnosis_or_icd_code": any(term in safe_summary for term in ["icd", "diagnosis", "dx"]),
        "requested_service_or_cpt": any(
            term in safe_summary for term in ["cpt", "procedure", "service", "therapy", "mri", "ct", "medication"]
        ),
        "medical_necessity": any(
            term in safe_summary
            for term in ["medical necessity", "failed", "conservative", "contraindication", "severity", "symptom"]
        ),
        "supporting_documentation": any(
            term in safe_summary for term in ["note", "lab", "imaging", "report", "document", "history"]
        ),
        "payer_or_plan": any(term in safe_summary for term in ["payer", "insurance", "plan", "policy"]),
    }

    missing_items = [name for name, present in checklist.items() if not present]
    status = "ready_for_review" if not missing_items else "missing_information"

    return {
        "status": status,
        "checklist": checklist,
        "missing_items": missing_items,
        "recommendation": (
            "Case appears ready for clinician/authorization review."
            if status == "ready_for_review"
            else "Collect missing items before PA submission."
        ),
    }


@tool
def summarize_medical_text(text: str) -> Dict[str, Any]:
    """
    Summarize medical or payer-policy text into concise operational bullets.

    Use this for long clinical notes, payer policies, or prior authorization criteria.
    """
    safe_text = anonymize_phi(text)
    sentences = [part.strip() for part in safe_text.replace("\n", " ").split(".") if part.strip()]
    bullets = sentences[:5]

    return {
        "summary": bullets,
        "truncated": len(sentences) > len(bullets),
    }


TOOLS = [
    search_medical_documents_tool,
    assess_prior_authorization_readiness,
    summarize_medical_text,
]

_AGENT_LLM_WITH_TOOLS = chat_agent_llm.bind_tools(TOOLS)
_TOOL_NODE = ToolNode(TOOLS)


async def _call_model(state: ChatAgentState) -> Dict[str, List[AnyMessage]]:
    """Call the LLM with the system prompt and current conversation state."""
    messages = [SystemMessage(content=MEDICAL_CHAT_SYSTEM_PROMPT), *state["messages"]]
    response = await _AGENT_LLM_WITH_TOOLS.ainvoke(messages)
    return {"messages": [response]}


def _should_continue(state: ChatAgentState) -> str:
    """Route to tools when the model requests tool calls; otherwise finish."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return END


def _build_graph() -> Any:
    """Build and compile the LangGraph chat agent."""
    graph = StateGraph(ChatAgentState)
    graph.add_node("agent", _call_model)
    graph.add_node("tools", _TOOL_NODE)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile()


CHAT_AGENT_GRAPH = _build_graph()


async def run_chat_agent(message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the medical chat agent and return the final assistant reply.

    User text is PHI-anonymized before being sent to the LLM.
    """
    safe_message = anonymize_phi(message)
    result = await CHAT_AGENT_GRAPH.ainvoke(
        {
            "messages": [HumanMessage(content=safe_message)],
            "session_id": session_id,
        }
    )

    messages = result["messages"]
    final_message = messages[-1]
    reply = final_message.content if isinstance(final_message.content, str) else str(final_message.content)

    return {
        "reply": anonymize_phi(reply).strip(),
        "session_id": session_id,
    }


async def stream_chat_agent(message: str, session_id: Optional[str] = None) -> AsyncIterator[str]:
    """
    Stream chat-agent events as text chunks.

    The current implementation streams finalized node outputs so clients can receive
    tool-progress and final-answer events without changing the agent graph.
    """
    safe_message = anonymize_phi(message)

    async for event in CHAT_AGENT_GRAPH.astream(
        {
            "messages": [HumanMessage(content=safe_message)],
            "session_id": session_id,
        },
        stream_mode="updates",
    ):
        if "tools" in event:
            yield "Searching medical records and checking context...\n"

        if "agent" in event:
            messages = event["agent"].get("messages", [])
            if not messages:
                continue

            message_chunk = messages[-1]
            content = getattr(message_chunk, "content", "")
            if content:
                yield f"{anonymize_phi(str(content)).strip()}\n"