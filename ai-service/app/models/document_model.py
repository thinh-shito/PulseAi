import datetime
from datetime import time
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, ValidationInfo, create_model, field_validator, ConfigDict


class DocumentBaseModel(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    @field_validator("*", mode="before")
    @classmethod
    def preprocess_fields(cls, v: Any, info: ValidationInfo) -> Any:
        """
        Enforce empty list for List field types if None is provided,
        and convert strings back to datetime/time if the target field type is temporal.
        """
        field_info = cls.model_fields.get(info.field_name)
        if not field_info:
            return v
            
        annotation = field_info.annotation
        
        # Enforce empty list strictly if the value is None and the field type expects a list
        if v is None:
            anno_str = str(annotation).lower()
            if "list[" in anno_str or "typing.list" in anno_str:
                return []
            return v

        if not isinstance(v, str):
            return v

        # Check if the annotation is datetime or time (including Optional/Union variants)
        is_datetime_type = False
        is_time_type = False

        if annotation is datetime.datetime:
            is_datetime_type = True
        elif annotation is time:
            is_time_type = True
        else:
            # Handle Optional / Union / | types
            origin = getattr(annotation, "__origin__", None)
            args = getattr(annotation, "__args__", ())
            if origin is Union:
                if datetime.datetime in args:
                    is_datetime_type = True
                if time in args:
                    is_time_type = True
            else:
                # Fallback for Python 3.10+ | syntax or other variant representations
                anno_str = str(annotation)
                if "datetime.datetime" in anno_str or "datetime" in anno_str:
                    is_datetime_type = True
                elif "datetime.time" in anno_str or "time" in anno_str:
                    is_time_type = True

        if is_datetime_type:
            try:
                # Handle ISO format strings, including 'Z' suffix
                return datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return v

        if is_time_type:
            try:
                # Handle ISO format time strings (e.g., "14:30:00")
                return time.fromisoformat(v)
            except (ValueError, TypeError):
                return v

        return v


def get_document_output_model(
    fields: List[Dict[str, Any]], model_name: str = "DocumentOutputModel"
) -> Type[BaseModel]:
    """
    Dynamically creates a Pydantic model for LLM output based on field definitions.

    Args:
        fields: A list of dictionaries containing 'name', 'type', 'description', and optionally 'sub_fields'.
        model_name: The name of the generated model class.

    Returns:
        A dynamically generated Pydantic model class.
    """
    type_mapping = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "datetime": datetime.datetime,
        "time": time,
        "None": type(None),
    }

    dyn_fields = {}
    for f in fields:
        f_name = f.get("name")
        if not f_name:
            continue

        f_type_str = f.get("type", "str")
        f_desc = f.get("description", "")

        if f_type_str == "list" or f_type_str.startswith("list[") or f_type_str.startswith("List["):
            sub_fields = f.get("sub_fields")
            if sub_fields and isinstance(sub_fields, list):
                # Create a sub-model name based on the field name (e.g. working_histories -> WorkingHistoriesItemModel)
                sub_model_name = "".join(x.capitalize() or "_" for x in f_name.split("_")) + "ItemModel"
                sub_model = get_document_output_model(sub_fields, model_name=sub_model_name)
                dyn_fields[f_name] = (Optional[List[sub_model]], Field(default=[], description=f_desc))
            else:
                inner_type = str
                if "[" in f_type_str and f_type_str.endswith("]"):
                    inner_type_str = f_type_str[f_type_str.find("[") + 1 : -1]
                    inner_type = type_mapping.get(inner_type_str, str)
                dyn_fields[f_name] = (Optional[List[inner_type]], Field(default=None, description=f_desc))
        elif f_type_str in ["object", "dict"]:
            sub_fields = f.get("sub_fields")
            if sub_fields and isinstance(sub_fields, list):
                sub_model_name = "".join(x.capitalize() or "_" for x in f_name.split("_")) + "Model"
                sub_model = get_document_output_model(sub_fields, model_name=sub_model_name)
                dyn_fields[f_name] = (Optional[sub_model], Field(default={}, description=f_desc))
            else:
                dyn_fields[f_name] = (Optional[Dict[str, Any]], Field(default=None, description=f_desc))
        else:
            f_type = type_mapping.get(f_type_str, str)
            # Using Optional[f_type] with default None ensures the model can handle missing values
            dyn_fields[f_name] = (Optional[f_type], Field(default=None, description=f_desc))

    # Create the dynamic model using DocumentBaseModel as the base class
    return create_model(model_name, __base__=DocumentBaseModel, **dyn_fields)