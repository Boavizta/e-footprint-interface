"""Form data parsing for HTTP requests.

This module handles parsing of HTTP form data into a clean format
that the domain layer can use for object construction. It separates
the HTTP-specific concerns (prefixed keys, nested field grouping)
from domain construction logic.
"""
import json
from typing import Any, Dict, Mapping, get_origin, List

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT


def parse_form_data(form_data: Mapping[str, Any], object_type: str) -> Dict[str, Any]:
    """Parse form data into clean attribute dict.

    Handles both prefixed keys (from HTTP forms) and unprefixed keys (from internal calls).

    Transforms form data like:
        {
            "Server_name": "My Server",
            "Server_cpu_cores": "4",
            "Server_cpu_cores_unit": "core",
            "Server_hourly_usage__start_date": "2024-01-01",
            "Server_hourly_usage__duration": "365",
        }

    Or unprefixed:
        {
            "name": "My Server",
            "cpu_cores": "4",
        }

    Into:
        {
            "name": "My Server",
            "cpu_cores": {
                "value": 4.0,
                "unit": "core"
            }
            "hourly_usage": {
                "start_date": "2024-01-01",
                "duration": "365"
            },
        }

    Args:
        form_data: Raw form data with prefixed or unprefixed keys
        object_type: The object type prefix to remove (e.g., "Server")

    Returns:
        Dict with clean attribute names, grouped nested fields, and unit mappings
    """
    prefix = f"{object_type}_"
    parsed = {}

    new_efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[object_type]
    init_sig_params = get_init_signature_params(new_efootprint_obj_class)

    for key, value in form_data.items():
        if key.startswith("select-new-object"):
            continue
        # Remove prefix if present
        if key.startswith(prefix):
            attr_key = key[len(prefix):]
        else:
            attr_key = key

        annotation = None
        if attr_key in init_sig_params:
            annotation = init_sig_params[attr_key].annotation
        if "__" in attr_key:
            base_attr, field_name = attr_key.split("__", 1)
            if base_attr not in parsed:
                parsed[base_attr] = {"form_inputs": {}, "label": "no label"}
            parsed[base_attr]["form_inputs"][field_name] = value
        # Check for unit suffix (only for non-nested fields)
        # For example, "hourly_usage__modeling_duration_unit" won’t match here.
        elif attr_key.endswith("_unit"):
            base_attr = attr_key[:-5]  # Remove "_unit"
            # value should already have been parsed
            parsed[base_attr]["value"] = float(parsed[base_attr]["value"])
            parsed[base_attr]["unit"] = value
        elif key.endswith("_form_data") and isinstance(value, str):
            parsed_key, parsed_form = _parse_inline_form_data(key, value)
            parsed[parsed_key] = parsed_form
        elif attr_key in ["name", "id", "type_object_available", "efootprint_id_of_parent_to_link_to",
                          "csrfmiddlewaretoken", "recomputation"]:
            parsed[attr_key] = value
        elif get_origin(annotation) and get_origin(annotation) in (list, List):
            # List attribute - split by semicolon
            parsed[attr_key] = [v for v in str(value).split(";") if v]
        elif annotation is None:
            # Case of JobWeb form: some fields like server_or_external_api or service_or_external_api are resolved
            # in the pre_create hook and thus not annotated in the JobWeb __init__. We want to pass them through as-is.
            parsed[attr_key] = value
        elif issubclass(annotation, ModelingObject):
            parsed[attr_key] = value
        elif issubclass(annotation, ExplainableObject):
            parsed[attr_key] = {"value": value, "label": "no label"}
        else:
            raise ValueError(f"Unable to parse {attr_key} in {object_type} form data.")

    return parsed


def _infer_object_type_from_key(key: str) -> str:
    """Infer object type from a nested form data key.

    E.g., 'Storage_form_data' -> 'Storage', 'EdgeStorage_form_data' -> 'EdgeStorage'
    """
    # Remove '_form_data' suffix
    base = key[:-10]  # len('_form_data') == 10
    return base


def _parse_inline_form_data(key: str, value: str) -> Dict[str, Any]:
    """Parse nested form data fields.

    This function parses nested forms and stores them under _parsed_* keys

    The nested form data is parsed and stored so domain hooks can access
    already-parsed data without needing to import adapter code.

    Args:
        key: Original key of the inline form data
        value: Inline for data as string

    Returns:
        Parsed key and form data with nested forms also parsed
    """
    nested_raw = json.loads(value)
    nested_type = nested_raw.get("type_object_available") or _infer_object_type_from_key(key)
    nested_parsed = parse_form_data(nested_raw, nested_type)
    # Store parsed nested data with _parsed_ prefix
    parsed_key = f"_parsed_{key[:-10]}"  # e.g., "_parsed_Storage"

    return parsed_key, nested_parsed
