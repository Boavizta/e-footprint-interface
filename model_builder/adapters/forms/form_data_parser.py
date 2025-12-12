"""Form data parsing for HTTP requests.

This module handles parsing of HTTP form data into a clean format
that the domain layer can use for object construction. It separates
the HTTP-specific concerns (prefixed keys, nested field grouping)
from domain construction logic.
"""
import json
from typing import Any, Dict, Mapping


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
            "cpu_cores": "4",
            "hourly_usage": {
                "start_date": "2024-01-01",
                "duration": "365"
            },
            "_units": {"cpu_cores": "core"}
        }

    Args:
        form_data: Raw form data with prefixed or unprefixed keys
        object_type: The object type prefix to remove (e.g., "Server")

    Returns:
        Dict with clean attribute names, grouped nested fields, and unit mappings
    """
    prefix = f"{object_type}_"
    parsed = {}
    nested_fields = {}  # attr_name -> {field_name: value}
    units = {}  # attr_name -> unit string

    for key, value in form_data.items():
        # Remove prefix if present
        if key.startswith(prefix):
            attr_key = key[len(prefix):]
        else:
            attr_key = key

        # Check for nested field pattern FIRST (attr__field)
        # This must come before unit check to handle nested fields like
        # "hourly_usage__modeling_duration_unit" correctly
        if "__" in attr_key:
            base_attr, field_name = attr_key.split("__", 1)
            if base_attr not in nested_fields:
                nested_fields[base_attr] = {}
            nested_fields[base_attr][field_name] = value
        # Check for unit suffix (only for non-nested fields)
        elif attr_key.endswith("_unit"):
            base_attr = attr_key[:-5]  # Remove "_unit"
            units[base_attr] = value
        else:
            parsed[attr_key] = value

    # Merge nested fields into parsed dict
    for attr_name, fields in nested_fields.items():
        parsed[attr_name] = fields

    # Attach units as metadata
    if units:
        parsed["_units"] = units

    return parsed


def _infer_object_type_from_key(key: str) -> str:
    """Infer object type from a nested form data key.

    Converts snake_case key to PascalCase object type.
    E.g., 'storage_form_data' -> 'Storage', 'edge_storage_form_data' -> 'EdgeStorage'
    """
    # Remove '_form_data' suffix
    base = key[:-10]  # len('_form_data') == 10
    # Convert snake_case to PascalCase
    return "".join(word.capitalize() for word in base.split("_"))


def parse_form_data_with_nested(form_data: Mapping[str, Any], object_type: str) -> Dict[str, Any]:
    """Parse form data including any nested form data fields.

    This function handles the full parsing of HTTP form data:
    1. Parses the main form data with parse_form_data
    2. Finds any *_form_data fields containing JSON-encoded nested form data
    3. Parses those nested forms and stores them under _parsed_* keys

    The nested form data is parsed and stored so domain hooks can access
    already-parsed data without needing to import adapter code.

    Args:
        form_data: Raw HTTP form data (QueryDict or dict)
        object_type: The main object type (e.g., "Server")

    Returns:
        Parsed form data with nested forms also parsed under _parsed_* keys
    """
    # Use type_object_available if present (concrete type has the actual prefix)
    actual_type = form_data.get("type_object_available", object_type)

    # First parse the main form data
    parsed = parse_form_data(form_data, actual_type)

    # Find and parse any nested form data fields
    # These are JSON strings in the original form_data (not in parsed)
    for key, value in form_data.items():
        if key.endswith("_form_data") and isinstance(value, str):
            try:
                nested_raw = json.loads(value)
                nested_type = nested_raw.get("type_object_available") or _infer_object_type_from_key(key)
                nested_parsed = parse_form_data(nested_raw, nested_type)
                # Store parsed nested data with _parsed_ prefix
                parsed_key = f"_parsed_{key[:-10]}"  # e.g., "_parsed_storage"
                parsed[parsed_key] = nested_parsed
            except (json.JSONDecodeError, TypeError):
                pass  # Invalid JSON - skip this field

    return parsed
