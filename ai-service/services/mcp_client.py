"""MCP client for communicating with the FastMCP tool server."""
import httpx
from typing import Dict, Any, List
from core.config import settings


class MCPClient:
    """Client for calling MCP server tools via HTTP."""
    
    def __init__(self):
        self.base_url = settings.mcp_server_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout for tool execution
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from the MCP server."""
        response = await self.client.get(f"{self.base_url}/tools")
        response.raise_for_status()
        return response.json()["tools"]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a specific MCP tool with the given arguments."""
        response = await self.client.post(
            f"{self.base_url}/tools/{tool_name}",
            json={"arguments": arguments}
        )
        response.raise_for_status()
        result = response.json()
        
        # Return the result as a JSON string for the agent
        import json
        return json.dumps(result)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global MCP client instance
_mcp_client: MCPClient | None = None


async def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def close_mcp_client():
    """Close the global MCP client instance."""
    global _mcp_client
    if _mcp_client is not None:
        await _mcp_client.close()
        _mcp_client = None