import re
from pathlib import Path
from typing import Any, Dict, Optional
from pypdf import PdfReader, PdfWriter

def get_field_value(data: Dict[str, Any], path: str) -> str:
    """
    Retrieves a value from a nested dictionary structure using a dot-separated path.
    Example: get_field_value(data, 'contact_info.name') -> "John Doe"
    """
    keys = path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return ""
    
    if current is None:
        return ""
    return str(current)


def parse_slice_string(s: str) -> slice:
    """
    Parses a Python-style slice string (e.g., 'n', ':3', '1:5') into a slice object.
    'n' is treated as a shortcut for the full range ':'.
    """
    if s == 'n' or not s:
        return slice(None)
    
    if ':' not in s:
        try:
            val = int(s)
            return slice(val, val + 1)
        except ValueError:
            return slice(None)
            
    parts = s.split(':')
    def safe_int(idx):
        try:
            return int(parts[idx]) if len(parts) > idx and parts[idx] else None
        except ValueError:
            return None
            
    start = safe_int(0)
    stop = safe_int(1)
    step = safe_int(2)
    return slice(start, stop, step)


def find_collection_marker(text: str) -> Optional[tuple[str, str]]:
    """
    Identifies if a text contains a collection placeholder with slicing.
    Matches {{collection[slice].field}} and returns (collection, slice_str).
    """
    match = re.search(r'\{\{([a-zA-Z0-9_]+)\[([^\]]*)\]', text)
    if match:
        return match.group(1), match.group(2)
    return None


def resolve_path(data: Any, path: str) -> str:
    """
    Resolves a path with nested dictionaries and list indexing from data.
    Example:
      resolve_path(data, "contact_info.name")
      resolve_path(data, "medications[0].name")
      resolve_path(data, "allergies[1]")
    """
    parts = path.split('.')
    current = data
    for part in parts:
        # Check if the part has list indexing, e.g. "medications[0]"
        match = re.match(r'^([a-zA-Z0-9_]+)((?:\[\d+\])+)$', part)
        if match:
            name = match.group(1)
            indices_str = match.group(2)
            if isinstance(current, dict):
                current = current.get(name)
            else:
                return ""
            
            # Extract all indices as integers
            indices = [int(idx) for idx in re.findall(r'\[(\d+)\]', indices_str)]
            for idx in indices:
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return ""
        else:
            # Simple dictionary access
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return ""
                
    if current is None:
        return ""
    return str(current)


def resolve_pdf_field(field_name: str, data: Dict[str, Any]) -> str:
    """
    Resolves the value for a PDF field from data.
    Supports:
    1. Field names that are placeholders: e.g., '{{contact_info.name}}' or '{{medications[0].name}}'
    2. Field names that are direct paths: e.g., 'contact_info.name' or 'medications[0].name'
    """
    if "{{" in field_name:
        def sub_match(match):
            placeholder_content = match.group(1).strip()
            
            # Check if it is a collection placeholder, e.g., collection[slice].field
            col_info = find_collection_marker("{{" + placeholder_content + "}}")
            if col_info:
                col_name, slice_str = col_info
                raw_items = data.get(col_name) or []
                sliced_items = raw_items[parse_slice_string(slice_str)]
                if sliced_items:
                    item_data = sliced_items[0]
                    if "." in placeholder_content:
                        rest = placeholder_content.split("]")[-1]
                        if rest.startswith("."):
                            field = rest[1:]
                            return get_field_value(item_data, field) if isinstance(item_data, dict) else ""
                    else:
                        return str(item_data)
                return ""
            
            return resolve_path(data, placeholder_content)
            
        return re.sub(r'\{\{([^}]+)\}\}', sub_match, field_name)
    else:
        return resolve_path(data, field_name.strip())


def fill_template_pdf(template_path: str, data: Dict[str, Any], output_path: str) -> str:
    """
    Fills a PDF template's interactive form fields with data from data.
    
    Args:
        template_path: Path to the input PDF template.
        data: Dictionary containing replacement data.
        output_path: Path where the filled PDF should be saved.
        
    Returns:
        The resolved absolute path of the generated PDF file.
    """
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)
    
    fields = reader.get_fields()
    if not fields:
        with open(output_path, "wb") as f:
            writer.write(f)
        return str(Path(output_path).resolve())
        
    updates = {}
    for field_name in fields.keys():
        val = resolve_pdf_field(field_name, data)
        if val != "":
            updates[field_name] = val
            
    for page in writer.pages:
        writer.update_page_form_field_values(page, updates)
        
    with open(output_path, "wb") as f:
        writer.write(f)
        
    return str(Path(output_path).resolve())