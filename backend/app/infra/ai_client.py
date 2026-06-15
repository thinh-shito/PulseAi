import httpx
from app.core.config import settings

class AIClient:
    """
    HTTP Client for calling AI agent APIs.
    """
    def __init__(self) -> None:
        self.base_url = settings.ai_agent_url
        self.timeout = httpx.Timeout(60.0, connect=10.0)

    async def call_chat(self, session_id: str, message: str) -> str:
        """
        Call the AI agent chat endpoint.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"session_id": session_id, "message": message}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
            except Exception as e:
                # Fallback / Error handling placeholder
                return f"Error communicating with AI agent: {str(e)}"

    async def trigger_workflow(self, workflow_id: str) -> dict:
        """
        Call the AI agent to trigger the prior authorization workflow.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/workflow/process",
                    json={"workflow_id": workflow_id}
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return {"status": "failed", "error": str(e)}

ai_client = AIClient()