import logging
import os
import tempfile
from typing import Literal, Dict, Any, Tuple
from langchain_core.output_parsers import PydanticOutputParser

from app.core.chain import extraction_chain
from app.prompts.extraction_prompt import EXTRACTION_PROMPT
from app.models.document_model import get_document_output_model
from app.helpers.phi_helper import anonymize_text_with_mapping, unmask_data
from app.helpers.fill_template_docx import fill_template_docx
from app.helpers.fill_template_pdf import fill_template_pdf
from app.utils.file_processor import convert_file_to_text
from app.utils.db import get_fields_from_db, get_template_from_db

logger = logging.getLogger(__name__)

def to_pascal_case(name: str) -> str:
    """Converts a snake_case string to PascalCase."""
    if not name:
        return "Document"
    # Replace hyphens with underscores, split, and capitalize each segment
    segments = name.replace("-", "_").split("_")
    return "".join(seg.capitalize() for seg in segments if seg)

async def generate_document_workflow(
    template_name: str,
    file_bytes: bytes,
    filename: str,
    language: Literal["en", "vi"]
) -> Tuple[bytes, str]:
    """
    Main workflow of API document_handler:
    - Step 1: load a list of fields from DB based on template_name
    - Step 2: call function in utils to process file to text based on extension
    - Step 3: apply phi_filter to mask PII
    - Step 4: create model_name based on template name
    - Step 5: create document_model = get_document_output_model(fields, model_name) -> create parser = PydanticOutputParser(document_model)
    - Step 6: call extraction_chain that is initialized in chain.py and send these params into EXTRACTION_PROMPT
    - Step 7: unmask PII for llm response
    - Step 8: Load template from another table in DB based on template_name (stored docx/pdf file)
    - Step 9: Fill the template based on extracted fields using fill_template_docx or fill_template_pdf
    - Step 10: Final response of API is the filled template.
    
    Returns:
        A tuple of (filled_file_bytes, file_extension)
    """
    logger.info(f"Starting generate_document_workflow for template_name: {template_name}, language: {language}")

    # Step 1: load a list of fields from DB based on template_name
    fields = get_fields_from_db(template_name)
    logger.info(f"Step 1: Loaded {len(fields)} fields for {template_name}")

    # Step 2: call function in utils to process file.
    text = convert_file_to_text(file_bytes, filename)
    logger.info(f"Step 2: Converted file to text. Length of text: {len(text)}")

    # Step 3: apply phi_filter to mask PII
    masked_text, phi_mapping = anonymize_text_with_mapping(text)
    logger.info(f"Step 3: Masked PII. Found {len(phi_mapping)} placeholders.")

    # Step 4: create model_name based on template name
    model_name = to_pascal_case(template_name)
    logger.info(f"Step 4: Created model name '{model_name}' for template '{template_name}'")

    # Step 5: create document_model = get_document_output_model(fields, model_name) -> create parser = PydanticOutputParser(document_model)
    document_model = get_document_output_model(fields, model_name)
    parser = PydanticOutputParser(pydantic_object=document_model)
    logger.info("Step 5: Dynamic Pydantic model and PydanticOutputParser created.")

    # Step 6: call extraction_chain that is initialized in chain.py and send these params into EXTRACTION_PROMPT
    language_instruction = "Extracted values are in Vietnamese" if language == "vi" else "Extracted values are in English"
    format_instruction = parser.get_format_instructions()
    
    prompt_text = EXTRACTION_PROMPT.format(
        content=masked_text,
        language_instruction=language_instruction,
        format_instruction=format_instruction
    )
    
    logger.info("Step 6: Invoking extraction chain...")
    # Chain can be directly invoked
    llm_response = extraction_chain.invoke(prompt_text)
    
    # Extract text from LLM response
    try:
        response_text = llm_response.content.strip()
    except AttributeError:
        response_text = str(llm_response).strip()
        
    logger.info(f"Received response from LLM: {response_text[:300]}...")
    
    # Parse the response using PydanticOutputParser
    parsed_obj = parser.parse(response_text)
    
    # Convert Pydantic object to dict
    if hasattr(parsed_obj, "model_dump"):
        extracted_dict = parsed_obj.model_dump()
    else:
        extracted_dict = parsed_obj.dict()

    # Step 7: unmask PII for llm response
    unmasked_dict = unmask_data(extracted_dict, phi_mapping)
    logger.info("Step 7: Unmasked PII for LLM response.")

    # Step 8: Load template from another table in DB based on template_name (stored docx/pdf file)
    template_bytes, template_ext = get_template_from_db(template_name)
    logger.info(f"Step 8: Loaded template from DB. Extension: {template_ext}, size: {len(template_bytes)} bytes")

    # Step 9: Fill the template based on extracted fields from step 6 using fill_template_docx or fill_template_pdf in /helpers
    # We will write the template bytes to a temp file, fill it, and read the filled file back.
    filled_bytes = b""
    suffix = f".{template_ext.lower().strip('.')}"
    
    temp_in = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_out = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        temp_in.write(template_bytes)
        temp_in.close()
        temp_out.close() # filler will write to it
        
        logger.info(f"Step 9: Filling template using temporary files {temp_in.name} -> {temp_out.name}")
        if template_ext.lower().strip('.') == "docx":
            fill_template_docx(temp_in.name, unmasked_dict, temp_out.name)
        else:
            # Fallback to pdf
            fill_template_pdf(temp_in.name, unmasked_dict, temp_out.name)
            
        with open(temp_out.name, "rb") as f:
            filled_bytes = f.read()
            
        logger.info(f"Step 10: Completed template filling. Output size: {len(filled_bytes)} bytes")
    finally:
        # Cleanup
        try:
            os.unlink(temp_in.name)
        except OSError:
            pass
        try:
            os.unlink(temp_out.name)
        except OSError:
            pass

    return filled_bytes, template_ext