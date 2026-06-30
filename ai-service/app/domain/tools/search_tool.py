"""
Medical document search tool.

This module wraps db-query-agent for read-only natural-language querying
against an external HIS PostgreSQL database. The HIS database is separate
from PulseAI's application database.
"""
import json
import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from db_query_agent import DatabaseQueryAgent

from app.core.config import settings
from app.domain.phi_filter import anonymize_phi

logger = logging.getLogger(__name__)


class MedicalDocumentSearchError(RuntimeError):
    """Raised when the medical document search tool cannot complete a query."""


@lru_cache(maxsize=1)
def _get_database_query_agent() -> DatabaseQueryAgent:
    """
    Create a cached read-only DatabaseQueryAgent for the external HIS database.

    The factory avoids exposing a mutable module-level database client while
    still reusing the agent connection pool/cache across requests.
    """
    if not settings.his_database_url:
        raise MedicalDocumentSearchError("HIS_DATABASE_URL is not configured.")

    openai_api_key = settings.openai_api_key
    if not openai_api_key:
        raise MedicalDocumentSearchError(
            "OPENAI_API_KEY is required for HIS database search."
        )

    return DatabaseQueryAgent(
        database_url=settings.his_database_url,
        openai_api_key=openai_api_key,
        fast_model=settings.his_db_query_fast_model,
        read_only=True,
        enable_cache=True,
    )


def _anonymize_value(value: Any) -> Any:
    """Recursively anonymize string values in tool results."""
    if isinstance(value, str):
        return anonymize_phi(value)

    if isinstance(value, list):
        return [_anonymize_value(item) for item in value]

    if isinstance(value, dict):
        return {key: _anonymize_value(item) for key, item in value.items()}

    return value


async def search_medical_documents(
    query: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search medical documents in the external HIS database using natural language.

    Args:
        query: User search question. This will be PHI-anonymized before it is
            sent to the LLM-backed query agent.
        session_id: Optional session identifier for multi-turn database chat.

    Returns:
        A dictionary containing a natural-language answer, generated SQL, and
        sanitized raw metadata returned by db-query-agent.
    """
    if not query.strip():
        return {
            "natural_response": "Please provide a search query.",
            "sql": None,
            "raw": {},
        }

    safe_query = anonymize_phi(query)

    try:
        agent = _get_database_query_agent()

        if session_id:
            session = agent.create_session(session_id=session_id)
            result = await session.ask(safe_query)
        else:
            result = await agent.query(safe_query)

        sanitized_result = _anonymize_value(result)

        if not isinstance(sanitized_result, dict):
            return {
                "natural_response": anonymize_phi(str(sanitized_result)),
                "sql": None,
                "raw": {"result": sanitized_result},
            }

        natural_response = sanitized_result.get("natural_response")
        if natural_response is None:
            natural_response = json.dumps(sanitized_result, ensure_ascii=False)

        return {
            "natural_response": anonymize_phi(str(natural_response)),
            "sql": sanitized_result.get("sql"),
            "raw": sanitized_result,
        }

    except MedicalDocumentSearchError:
        raise
    except Exception as exc:
        logger.exception("HIS medical document search failed")
        raise MedicalDocumentSearchError("Unable to search HIS medical documents.") from exc