"""
Validation Helper.
"""


def validate_non_empty(value: str, field_name: str) -> None:
    """
    Validate that a string value is not empty or whitespace only.
    """
    if not value or not value.strip():
        raise ValueError(f"Field '{field_name}' cannot be empty")