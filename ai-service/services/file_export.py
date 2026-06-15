"""File export service for storing generated documents in the database."""
import uuid
from datetime import datetime
from core.database import DatabasePool


async def store_exported_file(
    conversation_id: str,
    file_name: str,
    mime_type: str,
    content_base64: str
) -> str:
    """
    Store an exported file in the database.
    
    Args:
        conversation_id: The conversation this file belongs to
        file_name: Name of the file
        mime_type: MIME type of the file
        content_base64: Base64 encoded file content
    
    Returns:
        The UUID of the stored file
    """
    pool = await DatabasePool.get_pool()
    file_id = str(uuid.uuid4())
    
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO exported_files_v2 
            (id, conversation_id, file_name, mime_type, content_base64, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            file_id,
            conversation_id,
            file_name,
            mime_type,
            content_base64,
            int(datetime.now().timestamp() * 1000),  # milliseconds
        )
    
    return file_id


async def get_exported_file(file_id: str) -> dict | None:
    """
    Retrieve an exported file from the database.
    
    Args:
        file_id: The UUID of the file to retrieve
    
    Returns:
        Dictionary with file metadata and content, or None if not found
    """
    pool = await DatabasePool.get_pool()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, conversation_id, file_name, mime_type, content_base64, created_at
            FROM exported_files_v2
            WHERE id = $1
            """,
            file_id
        )
    
    if row is None:
        return None
    
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "file_name": row["file_name"],
        "mime_type": row["mime_type"],
        "content_base64": row["content_base64"],
        "created_at": row["created_at"],
    }