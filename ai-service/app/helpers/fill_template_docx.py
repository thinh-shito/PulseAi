import re
import copy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from docx import Document
from docx.table import _Row
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement

def sanitize_xml_string(value: str, context: str = "") -> str:
    """
    Strips NULL bytes and XML-incompatible control characters from a string.
    """
    # XML 1.0 allows: #x9 | #xA | #xD | [#x20-#xD7FF] | ...
    invalid_xml_re = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')
    matches = invalid_xml_re.findall(value)
    if matches:
        value = invalid_xml_re.sub('', value)
    return value

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
        # Handle single index cases like [0]
        try:
            val = int(s)
            # We return a slice of length 1 for consistency in looping
            return slice(val, val + 1)
        except ValueError:
            return slice(None)
            
    # Handle standard Python slice syntax: [start:stop:step]
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
    
    Regex breakdown:
    \\{\\{                 - Literal '{{'
    ([a-zA-Z0-9_]+)      - Group 1: collection name (alphanumeric + underscore)
    \\[([^\\]]*)\\]         - Group 2: content between brackets '[' and ']'
    """
    # Regex to catch the collection name and the content inside the brackets
    match = re.search(r'\{\{([a-zA-Z0-9_]+)\[([^\]]*)\]', text)
    if match:
        col, slice_str = match.group(1), match.group(2)
        # If the slice is a pure integer, it's direct index access, not a collection loop
        if slice_str.isdigit():
            return None
        return col, slice_str
    return None


def replace_in_paragraph(para: Paragraph, replace_fn: Callable[[str], str]):
    """
    Replaces placeholders in a paragraph while carefully preserving existing run formatting.
    
    Word documents split text into 'runs' based on formatting changes. A single placeholder
    like {{name}} might be split across multiple runs. This function merges broken 
    placeholders into the first run of the group before applying the replacement.
    """
    if not para.runs:
        return

    # --- Step 1: Handle placeholders split across multiple runs ---
    runs = para.runs
    full_text = ''.join(run.text for run in runs)
    if '{{' in full_text and '}}' in full_text:
        replaced = replace_fn(full_text)
        if replaced != full_text:
            sanitized = sanitize_xml_string(replaced, context=full_text)
            runs[0].text = sanitized
            for run in runs[1:]:
                run.text = ''
            return

    # --- Step 2: Apply the replacement function to each individual run ---
    for run in runs:
        if '{{' in run.text:
            original = run.text
            replaced = replace_fn(run.text)
            sanitized = sanitize_xml_string(replaced, context=original)
            run.text = sanitized


def make_collection_replacer(item_data: Any, collection_name: str, slice_str: str) -> Callable[[str], str]:
    """
    Creates a replacement function for a specific item within a collection.
    Supports {{collection[slice].field}} and {{collection[slice]}} formats.
    """
    def replace_fn(text: str) -> str:
        # Escaping for regex to handle special characters in names
        escaped_name = re.escape(collection_name)
        escaped_slice = re.escape(slice_str)
        
        # Pattern 1: {{collection[slice].field}}
        # Note: We must match the EXACT slice_str part to avoid replacing across different slices
        pattern_field = r'\{\{' + escaped_name + r'\[' + escaped_slice + r'\]\.([^}]+)\}\}'
        for field in re.findall(pattern_field, text):
            val = get_field_value(item_data, field) if isinstance(item_data, dict) else ""
            # Reconstruct the placeholder for exact string replacement
            placeholder = '{{' + collection_name + '[' + slice_str + '].' + field + '}}'
            text = text.replace(placeholder, val)

        # Pattern 2: {{collection[slice]}} (for primitive lists like strings)
        pattern_item = r'\{\{' + escaped_name + r'\[' + escaped_slice + r'\]\}\}'
        if re.search(pattern_item, text):
            val = str(item_data) if item_data is not None else ""
            # Use re.sub to handle the literal replacement of the item placeholder
            text = re.sub(pattern_item, val, text)

        return text
    return replace_fn


def make_simple_replacer(data: Dict[str, Any]) -> Callable[[str], str]:
    """
    Creates a replacement function for top-level placeholders (e.g., {{contact_info.name}}).
    Ignores collection items which are handled by the looping logic.
    """
    def replace_fn(text: str) -> str:
        # Find all top-level placeholders
        for placeholder in re.findall(r'\{\{([^}]+)\}\}', text):
            # Handle direct index access (e.g., {{diagnosis_code[0]}} or {{medications[0].name}})
            if '[' in placeholder:
                match = re.match(r'^([a-zA-Z0-9_]+)\[(\d+)\](?:\.([^}]+))?$', placeholder)
                if match:
                    col_name = match.group(1)
                    idx = int(match.group(2))
                    subfield = match.group(3)
                    
                    items = data.get(col_name)
                    if not isinstance(items, list):
                        val = ""
                    elif idx >= len(items):
                        val = ""
                    else:
                        item = items[idx]
                        if subfield:
                            val = get_field_value(item if isinstance(item, dict) else {}, subfield)
                        else:
                            val = str(item) if item is not None else ""
                    
                    text = text.replace('{{' + placeholder + '}}', val)
                continue
            
            val = get_field_value(data, placeholder)
            text = text.replace('{{' + placeholder + '}}', val)
        return text
    return replace_fn


def replace_placeholders_in_element(
    element: Union[Paragraph, _Row],
    item_data: Any,
    collection_name: str,
    slice_str: str
):
    """
    Helper to apply collection replacements to either a Paragraph or a Table Row.
    """
    replace_fn = make_collection_replacer(item_data, collection_name, slice_str)

    if isinstance(element, Paragraph):
        replace_in_paragraph(element, replace_fn)
    else:
        # For table rows, process every cell
        for cell in element.cells:
            for para in cell.paragraphs:
                replace_in_paragraph(para, replace_fn)


def clone_element(element: Union[Paragraph, _Row]):
    """
    Creates a deep copy of a paragraph or table row by duplicating its underlying XML.
    """
    new_el = copy.deepcopy(element._element)
    if isinstance(element, Paragraph):
        return Paragraph(new_el, element._parent)
    else:
        return _Row(new_el, element._parent)


def fill_checkboxes(doc: Document, data: Dict[str, Any]):
    """
    Finds all checkbox SDTs in the document and toggles their state based on data.
    """
    from docx.oxml.ns import qn, nsmap
    from docx.oxml import OxmlElement
    W14_NS = 'http://schemas.microsoft.com/office/word/2010/wordml'
    # Ensure w14 namespace is registered
    nsmap['w14'] = W14_NS

    body = doc.element.body
    for sdt in body.iter(qn('w:sdt')):
        sdt_pr = sdt.find(qn('w:sdtPr'))
        if sdt_pr is None:
            continue
        
        # Get the tag name (e.g., "is_male" or "{{is_male}}")
        tag_el = sdt_pr.find(qn('w:tag'))
        if tag_el is None:
            continue
        
        tag_val = tag_el.get(qn('w:val'), '')
        # Clean the tag value (strip brackets and spaces)
        field_name = tag_val.strip('{}').strip()
        if not field_name:
            continue
        
        # Look up value in data
        value = get_field_value(data, field_name)
        if not value:
            # Try top-level lookup directly in case it's in a sub-dict
            value = data.get(field_name)
            
        # Convert value to boolean
        if isinstance(value, bool):
            is_checked = value
        elif isinstance(value, str):
            is_checked = value.lower() in ('true', '1', 'yes', 'checked', 'x', '☒')
        elif isinstance(value, (int, float)):
            is_checked = bool(value)
        else:
            is_checked = False
            
        # Set checkbox element values
        checkbox_el = sdt_pr.find(f'{{{W14_NS}}}checkbox')
        if checkbox_el is not None:
            checked_el = checkbox_el.find(f'{{{W14_NS}}}checked')
            if checked_el is None:
                checked_el = OxmlElement('w14:checked')
                checkbox_el.append(checked_el)
            checked_el.set(qn('w14:val'), '1' if is_checked else '0')
            
        # Update sdtContent glyphs
        sdt_content = sdt.find(qn('w:sdtContent'))
        if sdt_content is not None:
            for sym in sdt_content.iter(qn('w:sym')):
                sym.set(qn('w:char'), '2612' if is_checked else '2610')
            for t in sdt_content.iter(qn('w:t')):
                t.text = '☒' if is_checked else '☐'


def fill_template_docx(template_path: str, data: Dict[str, Any], output_path: str) -> str:
    """
    Fills a DOCX template with data, supporting dynamic loops and complex field mapping.
    """
    doc = Document(template_path)

    # --- PART 1: PARAGRAPH LOOPING ---
    # Group contiguous paragraphs that belong to the same collection[slice] marker.
    p_groups = []       # Stores (collection_name, slice_str, [paragraphs])
    current_group = []
    current_collection_info = None

    for p in doc.paragraphs:
        col_info = find_collection_marker(p.text)
        if col_info:
            # If we switch to a different collection or different slice, finalize the previous group
            if current_collection_info and col_info != current_collection_info:
                p_groups.append((current_collection_info[0], current_collection_info[1], current_group))
                current_group = [p]
                current_collection_info = col_info
            else:
                current_group.append(p)
                current_collection_info = col_info
        else:
            # No marker found, finalize group if one was active
            if current_group:
                p_groups.append((current_collection_info[0], current_collection_info[1], current_group))
                current_group = []
                current_collection_info = None
    
    # Final cleanup of grouping
    if current_group:
        p_groups.append((current_collection_info[0], current_collection_info[1], current_group))

    # Process paragraph groups in REVERSE to avoid shifting indices for following blocks
    for col_name, slice_str, paras in reversed(p_groups):
        raw_items = data.get(col_name) or []
        # Apply Python slicing
        items = raw_items[parse_slice_string(slice_str)]
        last_para = paras[-1]

        # For each data item, clone the template block and fill it
        for item in reversed(items):
            for p_template in reversed(paras):
                new_p = clone_element(p_template)
                replace_placeholders_in_element(new_p, item, col_name, slice_str)
                # Insert the new paragraph immediately after the template block's end
                last_para._element.addnext(new_p._element)

        # Cleanup: Remove the original template paragraphs from the document
        for p_template in paras:
            p_template._element.getparent().remove(p_template._element)

    # --- PART 2: TABLE ROW LOOPING ---
    # Similar grouping logic as paragraphs, but applied to rows within each table.
    for table in doc.tables:
        row_groups = []  # Stores (collection_name, slice_str, [rows])
        current_group = []
        current_collection_info = None

        for row in table.rows:
            # Check for markers in any cell of the row
            row_text = "".join(cell.text for cell in row.cells)
            col_info = find_collection_marker(row_text)
            
            if col_info:
                if current_collection_info and col_info != current_collection_info:
                    row_groups.append((current_collection_info[0], current_collection_info[1], current_group))
                    current_group = [row]
                    current_collection_info = col_info
                else:
                    current_group.append(row)
                    current_collection_info = col_info
            else:
                if current_group:
                    row_groups.append((current_collection_info[0], current_collection_info[1], current_group))
                    current_group = []
                    current_collection_info = None
        
        if current_group:
            row_groups.append((current_collection_info[0], current_collection_info[1], current_group))

        # Replace row groups in reverse
        for col_name, slice_str, rows in reversed(row_groups):
            raw_items = data.get(col_name) or []
            items = raw_items[parse_slice_string(slice_str)]
            last_row = rows[-1]

            for item in reversed(items):
                for row_template in reversed(rows):
                    new_row = clone_element(row_template)
                    replace_placeholders_in_element(new_row, item, col_name, slice_str)
                    last_row._element.addnext(new_row._element)

            # Cleanup: Remove original rows
            for row_template in rows:
                table._tbl.remove(row_template._element)

    # --- PART 3: TOP-LEVEL FIELD REPLACEMENTS ---
    # After loops are processed, fill the remaining static placeholders (e.g., header/footer info)
    simple_replace = make_simple_replacer(data)

    # Process all resulting paragraphs
    for p in doc.paragraphs:
        if '{{' in p.text:
            replace_in_paragraph(p, simple_replace)

    # Process all cells in all tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if '{{' in para.text:
                        replace_in_paragraph(para, simple_replace)

    # Process checkboxes
    fill_checkboxes(doc, data)

    # Final save
    doc.save(output_path)
    return str(Path(output_path).resolve())