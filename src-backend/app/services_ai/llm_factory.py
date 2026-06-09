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
import json

from app.core.config import settings


class MockLLM:
    """Mock LLM class for dev/demo runs when no API keys are configured."""
    def __init__(self, temperature: float = 0.0):
        self.temperature = temperature

    def invoke(self, prompt: str):
        class MockResponse:
            def __init__(self, content):
                self.content = content

        prompt_lower = prompt.lower()

        # Clinical Node extraction
        if "clinical extraction assistant" in prompt_lower:
            icd10 = ["M54.5"]
            summary = "Patient reports back pain, routed to default template."
            confidence = 0.98

            if "lumbar" in prompt_lower or "back" in prompt_lower:
                icd10 = ["M54.5", "M51.36"]
                summary = "Lumbar disc degeneration and low back pain."
                confidence = 0.96
            elif "knee" in prompt_lower:
                icd10 = ["M17.11"]
                summary = "Unilateral primary osteoarthritis of right knee."
                confidence = 0.97
            elif "chest" in prompt_lower or "cardiac" in prompt_lower:
                icd10 = ["R07.9"]
                summary = "Chest pain, unspecified, requiring prior authorization."
                confidence = 0.95

            return MockResponse(
                json.dumps(
                    {
                        "icd10_codes": icd10,
                        "summary": summary,
                        "confidence_score": confidence,
                    }
                )
            )

        # Form Filler Node
        elif "medical billing assistant" in prompt_lower:
            fields = {}
            if "bcbs" in prompt_lower:
                fields = {
                    "diagnosis_code": "M54.5 (Low back pain)",
                    "procedure_code": "97110 (Therapeutic exercise)",
                    "treating_physician": "Dr. Emily Chen",
                }
            elif "aetna" in prompt_lower:
                fields = {
                    "diagnosis_code": "M54.5",
                    "clinical_notes": "Patient has severe back pain, recommended for physical therapy.",
                    "prior_treatments": "NSAIDs for 2 weeks, minimal relief.",
                }
            elif "uhc" in prompt_lower:
                fields = {
                    "member_id": "UHC-999238",
                    "diagnosis_code": "M54.5",
                    "procedure_code": "97110",
                }
            elif "bhyt_vn" in prompt_lower or "bảo hiểm y tế" in prompt_lower:
                fields = {
                    "ma_the_bhyt": "GD4797910200234",
                    "ma_icd10": "M54.5",
                    "don_vi_kham": "Bệnh viện Chợ Rẫy",
                }
            else:
                fields = {
                    "diagnosis_code": "M54.5",
                    "procedure_code": "97110",
                }
            return MockResponse(json.dumps(fields))

        # Default fallback
        return MockResponse("{}")


def get_llm(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    streaming: bool = False,
    provider: Optional[str] = None,
):
    # Fallback to MockLLM in dev/demo environment if no real API keys are configured
    api_key_placeholder = "your-openai-key-for-dev-only"
    if (
        not settings.azure_openai_api_key
        and (not settings.openai_api_key or settings.openai_api_key == api_key_placeholder)
    ):
        return MockLLM(temperature=temperature)
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
