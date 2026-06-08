"""
LLM Factory — returns the appropriate LLM instance based on provider/model.

Priority:
1. Azure OpenAI (production — use when AZURE_OPENAI_ENDPOINT is configured)
2. OpenAI (dev fallback)
3. Gemini (dev fallback)

NEVER call Azure OpenAI without first running text through PHIFilter.

NOTE: Heavy imports (langchain_openai, langchain_google_genai) are deferred to
      function call time — this allows unit tests to import this module without
      requiring the full LangChain stack to be installed.
"""
from typing import Optional

from app.core.config import settings


def get_llm(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    streaming: bool = False,
    provider: Optional[str] = None,
):
    """
    LLM Factory — returns the appropriate LLM instance based on provider/model.
    Imports are lazy so unit tests can import this module without langchain installed.
    """
    resolved_provider = provider or _detect_provider(model_name)

    if resolved_provider == "azure" or (
        settings.azure_openai_endpoint and resolved_provider != "gemini"
    ):
        from langchain_openai import AzureChatOpenAI  # lazy import
        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=model_name or settings.azure_openai_deployment,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            temperature=temperature,
            streaming=streaming,
        )

    m = (model_name or "gpt-4o-mini").lower()

    if "gemini" in m:
        from langchain_google_genai import ChatGoogleGenerativeAI  # lazy import
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=settings.gemini_api_key,
            streaming=streaming,
        )

    # Default: OpenAI
    from langchain_openai import ChatOpenAI  # lazy import
    return ChatOpenAI(
        model=model_name or "gpt-4o-mini",
        temperature=temperature,
        api_key=settings.openai_api_key,
        streaming=streaming,
    )


def _detect_provider(model_name: Optional[str]) -> str:
    """Infer provider from model name string."""
    if not model_name:
        return "azure" if settings.azure_openai_endpoint else "openai"
    m = model_name.lower()
    if "gemini" in m:
        return "gemini"
    if "deepseek" in m:
        return "openai"  # DeepSeek is OpenAI-compatible
    return "azure" if settings.azure_openai_endpoint else "openai"
