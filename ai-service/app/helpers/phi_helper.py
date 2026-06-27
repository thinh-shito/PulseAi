"""
PHI Filter Helper with placeholder mapping and unmasking.
"""
import re
from typing import Any, Dict, Tuple
from app.domain.phi_filter import EXCLUDE_WORDS, anonymize_phi


def anonymize_text(text: str) -> str:
    """
    Anonymize PHI (Protected Health Information) in medical texts.
    Simple wrapper to maintain compatibility.
    """
    return anonymize_phi(text)


def anonymize_text_with_mapping(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Anonymizes PHI in text and returns both the anonymized text and a mapping
    from placeholders to original values.
    """
    if not text:
        return text, {}

    mapping = {}
    counter = 1

    def replace_with_placeholder(pattern: str, prefix: str, current_text: str) -> str:
        nonlocal counter
        # Find matches and sort by length descending to avoid partial matches
        matches = re.findall(pattern, current_text)
        unique_matches = sorted(list(set(matches)), key=len, reverse=True)
        for m in unique_matches:
            placeholder = f"[{prefix}_{counter}]"
            mapping[placeholder] = m
            current_text = current_text.replace(m, placeholder)
            counter += 1
        return current_text

    # 1. Emails
    text = replace_with_placeholder(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL", text
    )

    # 2. SSN / ID numbers
    text = replace_with_placeholder(r"\b\d{3}-\d{2}-\d{4}\b", "ID_NUMBER", text)
    text = replace_with_placeholder(r"\b\d{9,12}\b", "ID_NUMBER", text)

    # 3. Phone numbers
    text = replace_with_placeholder(r"\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}", "PHONE", text)
    text = replace_with_placeholder(
        r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\d{3}[-.\s]?)?\d{3}[-.\s]?\d{4}\b", "PHONE", text
    )

    # 4. Dates
    text = replace_with_placeholder(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", "DATE", text)
    text = replace_with_placeholder(r"\b\d{4}-\d{1,2}-\d{1,2}\b", "DATE", text)

    # 5. Names (Capitalized Word Sequences)
    name_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"
    names = re.findall(name_pattern, text)
    filtered_names = []
    for name in names:
        words = name.split()
        is_name = True
        for w in words:
            clean_w = re.sub(r"[^\w]", "", w)
            if clean_w in EXCLUDE_WORDS:
                is_name = False
                break
        if is_name:
            filtered_names.append(name)

    unique_names = sorted(list(set(filtered_names)), key=len, reverse=True)
    for name in unique_names:
        placeholder = f"[PERSON_{counter}]"
        mapping[placeholder] = name
        text = text.replace(name, placeholder)
        counter += 1

    return text, mapping


def unmask_data(data: Any, mapping: Dict[str, str]) -> Any:
    """
    Recursively unmasks placeholders in data back to their original values.
    """
    if isinstance(data, str):
        result = data
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        return result
    elif isinstance(data, list):
        return [unmask_data(item, mapping) for item in data]
    elif isinstance(data, dict):
        return {key: unmask_data(val, mapping) for key, val in data.items()}
    else:
        return data