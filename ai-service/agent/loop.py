"""Core agent loop for OpenAI streaming with MCP tool integration."""
import json
from typing import AsyncGenerator, Dict, Any, List
from openai import AsyncOpenAI
from core.config import settings
from core.database import DatabasePool
from services.mcp_client import get_mcp_client
from services.file_export import store_exported_file


client = AsyncOpenAI(api_key=settings.openai_api_key)


async def load_conversation_history(conversation_id: str) -> List[Dict[str, str]]:
    """Load conversation history from the database."""
    pool = await DatabasePool.get_pool()
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content 
            FROM messages_v2 
            WHERE conversation_id = $1 
            ORDER BY id ASC
            """,
            conversation_id
        )
    
    return [{"role": row["role"], "content": row["content"]} for row in rows]


async def save_message(conversation_id: str, role: str, content: str) -> None:
    """Save a message to the database."""
    pool = await DatabasePool.get_pool()
    
    async with pool.acquire() as conn:
        from datetime import datetime
        await conn.execute(
            """
            INSERT INTO messages_v2 (conversation_id, role, content, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            conversation_id,
            role,
            content,
            int(datetime.now().timestamp() * 1000)
        )


async def update_conversation_timestamp(conversation_id: str) -> None:
    """Update the last_message_at timestamp for a conversation."""
    pool = await DatabasePool.get_pool()
    
    async with pool.acquire() as conn:
        from datetime import datetime
        await conn.execute(
            """
            UPDATE conversations_v2 
            SET last_message_at = $1 
            WHERE id = $2
            """,
            int(datetime.now().timestamp() * 1000),
            conversation_id
        )


async def auto_title_conversation(conversation_id: str, user_message: str) -> None:
    """Auto-generate a title for the conversation if it doesn't have one."""
    pool = await DatabasePool.get_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT title FROM conversations_v2 WHERE id = $1",
            conversation_id
        )
        
        if row and (not row["title"] or row["title"] == "New Conversation"):
            # Generate a simple title from the first message
            title = user_message[:50].strip()
            if len(user_message) > 50:
                title += "..."
            
            await conn.execute(
                "UPDATE conversations_v2 SET title = $1 WHERE id = $2",
                title,
                conversation_id
            )


async def run_agent_loop(
    conversation_id: str,
    user_message: str,
    file_content: str | None = None,
    file_name: str | None = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Core agent loop that streams responses from OpenAI and executes MCP tools.
    
    Yields SSE-compatible event dictionaries with keys 'event' and 'data'.
    """
    # Auto-title conversation
    await auto_title_conversation(conversation_id, user_message)
    
    # Build user message content
    user_content = user_message
    if file_content and file_name:
        user_content = (
            f"--- ATTACHED FILE: {file_name} ---\n"
            f"{file_content}\n"
            f"--- END OF FILE ---\n\n"
            f"User message: {user_message}"
        )
    
    # Save user message
    await save_message(conversation_id, "user", user_content)
    
    # Load full history
    history = await load_conversation_history(conversation_id)
    
    # Get MCP tools
    mcp_client = await get_mcp_client()
    try:
        tools_list = await mcp_client.list_tools()
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"]
                }
            }
            for tool in tools_list
        ]
    except Exception as e:
        print(f"[agent] Failed to list MCP tools: {e}")
        openai_tools = []
    
    # System prompt
    system_prompt = """You are a clinical AI assistant helping healthcare professionals with documentation tasks.

You have access to the following tools:
- generate_prior_auth: Extract prior authorization fields from patient clinical notes
- fill_docx_form: Fill a prior authorization DOCX template with extracted data (use after generate_prior_auth)
- generate_handover_report: Generate a structured shift handover report
- generate_discharge_summary: Generate a comprehensive hospital discharge summary

When a user provides clinical notes or asks you to generate a document, use the appropriate tool.
When a tool returns a document (content_base64 field present), acknowledge the file is ready for download.
Always be professional, accurate, and clinically precise in your responses."""
    
    messages = [{"role": "system", "content": system_prompt}, *history]
    
    MAX_ITERATIONS = 10
    iteration = 0
    assistant_final_text = ""
    
    while iteration < MAX_ITERATIONS:
        iteration += 1
        
        full_delta = ""
        tool_calls_accumulator: Dict[int, Dict[str, Any]] = {}
        
        # Stream OpenAI response
        stream = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=openai_tools if openai_tools else None,
            tool_choice="auto" if openai_tools else None,
            stream=True
        )
        
        async for chunk in stream:
            if not chunk.choices:
                continue
            
            choice = chunk.choices[0]
            delta = choice.delta
            
            # Stream text deltas
            if delta.content:
                full_delta += delta.content
                yield {"event": "text_delta", "data": {"delta": delta.content}}
            
            # Accumulate tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_accumulator:
                        tool_calls_accumulator[idx] = {"id": "", "name": "", "arguments": ""}
                    
                    if tc.id:
                        tool_calls_accumulator[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tool_calls_accumulator[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls_accumulator[idx]["arguments"] += tc.function.arguments
        
        tool_calls = list(tool_calls_accumulator.values())
        
        # If no tool calls, we're done
        if not tool_calls:
            assistant_final_text = full_delta
            break
        
        # Append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": full_delta or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]}
                }
                for tc in tool_calls
            ]
        })
        
        # Execute each tool call
        for tc in tool_calls:
            yield {"event": "tool_use_start", "data": {"name": tc["name"], "id": tc["id"]}}
            
            try:
                args = json.loads(tc["arguments"] or "{}")
                tool_result_str = await mcp_client.call_tool(tc["name"], args)
                
                # Check for exported files
                try:
                    parsed = json.loads(tool_result_str)
                    if parsed.get("content_base64") and parsed.get("filename"):
                        file_id = await store_exported_file(
                            conversation_id,
                            parsed["filename"],
                            parsed.get("mime_type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                            parsed["content_base64"]
                        )
                        
                        yield {
                            "event": "file_ready",
                            "data": {
                                "fileId": file_id,
                                "fileName": parsed["filename"],
                                "mimeType": parsed.get("mime_type")
                            }
                        }
                        
                        # Remove base64 from result
                        summary = {k: v for k, v in parsed.items() if k != "content_base64"}
                        tool_result_str = json.dumps(summary)
                except:
                    pass
                
                yield {
                    "event": "tool_result",
                    "data": {
                        "name": tc["name"],
                        "id": tc["id"],
                        "result": tool_result_str[:500]
                    }
                }
            except Exception as e:
                error_msg = str(e)
                tool_result_str = f"Error: {error_msg}"
                yield {
                    "event": "tool_result",
                    "data": {"name": tc["name"], "id": tc["id"], "error": error_msg}
                }
            
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result_str
            })
    
    if iteration >= MAX_ITERATIONS:
        assistant_final_text = "The request is taking too long to complete. Please try again."
        yield {"event": "text_delta", "data": {"delta": assistant_final_text}}
    
    # Save final assistant response
    if assistant_final_text:
        await save_message(conversation_id, "assistant", assistant_final_text)
    
    await update_conversation_timestamp(conversation_id)
    
    yield {"event": "done", "data": {}}