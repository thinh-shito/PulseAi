import logging
from typing import Literal
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from fastapi.responses import Response

from app.handlers.document_handler import generate_document_workflow

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/document/generate")
async def generate_document(
    template_name: str = Form(...),
    file: UploadFile = File(...),
    language: Literal["en", "vi"] = Form("en"),
):
    """
    Generate filled medical templates based on extracted values from clinical records.
    Supports dynamic mapping based on database configured fields and templates.
    """
    logger.info(f"Received request to generate document: template_name={template_name}, file={file.filename}, language={language}")
    try:
        file_bytes = await file.read()
        filled_bytes, extension = await generate_document_workflow(
            template_name=template_name,
            file_bytes=file_bytes,
            filename=file.filename,
            language=language
        )
        
        media_type = "application/octet-stream"
        ext = extension.lower().strip('.')
        if ext == "docx":
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == "pdf":
            media_type = "application/pdf"
            
        filename = f"{template_name}_filled.{ext}"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
        
        logger.info(f"Returning filled document response: filename={filename}, size={len(filled_bytes)} bytes")
        return Response(
            content=filled_bytes,
            media_type=media_type,
            headers=headers
        )
    except Exception as e:
        logger.exception("Error occurred in generate_document API endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )