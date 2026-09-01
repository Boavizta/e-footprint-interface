"""Form data parsing for HTTP requests.

This module handles parsing of HTTP form data into a clean format
that the domain layer can use for object construction. It separates
the HTTP-specific concerns (prefixed keys, nested field grouping)
from domain construction logic.
"""

import json
from typing import Any, Dict, Mapping, get_origin, List

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.builders.timeseries import (
    ExplainableRecurrentQuantitiesFromWeeklyPattern,
    WeeklyPatternValidationError,
)
from efootprint.utils.tools import get_init_signature_params

from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.services.group_membership_service import PARENT_GROUP_MEMBERSHIPS_FIELD
from model_builder.domain.type_annotation_utils import resolve_optional_annotation


_METADATA_ONLY_KEYS = frozenset({"confidence", "comment", "source"})


def _parse_weekly_pattern_input(raw_value: Any, *, can_be_negative: bool) -> dict:
    """Decode a normalized weekly payload and enforce the owning attribute's sign policy."""
    if isinstance(raw_value, str):
        try:
            form_inputs = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise WeeklyPatternValidationError(
                [{"path": "form_inputs", "code": "invalid_json", "message": "Weekly pattern must be valid JSON."}]
            ) from exc
    else:
        form_inputs = raw_value

    # Validate at the HTTP boundary so every malformed or tampered save receives the same
    # normalized path/code/message response instead of falling through to a generic modal.
    ExplainableRecurrentQuantitiesFromWeeklyPattern(form_inputs=form_inputs)

    if not can_be_negative and isinstance(form_inputs, dict):
        errors = []
        profiles = form_inputs.get("profiles")
        if isinstance(profiles, list):
            for profile_index, profile in enumerate(profiles):
                if not isinstance(profile, dict):
                    continue
                baseline = profile.get("baseline")
                if isinstance(baseline, (int, float)) and not isinstance(baseline, bool) and baseline < 0:
                    errors.append(
                        {
                            "path": f"profiles[{profile_index}].baseline",
                            "code": "negative_value_not_allowed",
                            "message": "Baseline must be zero or greater for this field.",
                        }
                    )
                ranges = profile.get("ranges")
                if not isinstance(ranges, list):
                    continue
                for range_index, time_range in enumerate(ranges):
                    if not isinstance(time_range, dict):
                        continue
                    value = time_range.get("value")
                    if isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0:
                        errors.append(
                            {
                                "path": f"profiles[{profile_index}].ranges[{range_index}].value",
                                "code": "negative_value_not_allowed",
                                "message": "Range value must be zero or greater for this field.",
                            }
                        )
        if errors:
            raise WeeklyPatternValidationError(errors)

    return form_inputs


def parse_count(raw_value: Any, *, error_prefix: str) -> float:
    """Parse a non-negative numeric count from raw form input."""
    try:
        parsed = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{error_prefix} must be a number.") from exc

    if parsed < 0:
        raise ValueError(f"{error_prefix} must be positive.")

    return parsed


def _parse_parent_group_memberships(raw_value: Any) -> Dict[str, float]:
    """Parse the `parent_group_memberships` widget payload into a `{parent_id: count}` dict."""
    if raw_value in (None, ""):
        return {}
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{PARENT_GROUP_MEMBERSHIPS_FIELD} must be valid JSON.") from exc
    else:
        parsed = raw_value
    if not isinstance(parsed, dict):
        raise ValueError(f"{PARENT_GROUP_MEMBERSHIPS_FIELD} must be a JSON object.")
    return {
        str(parent_id): parse_count(count, error_prefix=f"{PARENT_GROUP_MEMBERSHIPS_FIELD}[{parent_id}]")
        for parent_id, count in parsed.items()
    }


def _parse_explainable_object_dict_input(
    raw_value: Any, *, field_name: str, default_label: str = "no label"
) -> Dict[str, Dict[str, Any]]:
    """Normalize ExplainableObjectDict widget payloads into canonical parsed data."""
    if raw_value in ("", None):
        return {}

    if isinstance(raw_value, str):
        try:
            raw_mapping = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name} must be valid JSON.") from exc
    else:
        raw_mapping = raw_value

    if not isinstance(raw_mapping, dict):
        raise ValueError(f"{field_name} must be a JSON object.")

    parsed_mapping = {}
    for key_id, explainable_value in raw_mapping.items():
        if isinstance(explainable_value, dict):
            if "value" not in explainable_value:
                raise ValueError(f"{field_name}[{key_id}] must contain a value.")
            normalized_value = dict(explainable_value)
            normalized_value.setdefault("label", default_label)
        else:
            normalized_value = {
                "value": parse_count(explainable_value, error_prefix=f"{field_name}[{key_id}]"),
                "unit": "dimensionless",
                "label": default_label,
            }

        parsed_mapping[str(key_id)] = normalized_value

    return parsed_mapping


def parse_form_data(form_data: Mapping[str, Any], object_type: str) -> Dict[str, Any]:
    """Parse form data into clean attribute dict.

    Handles both prefixed keys (from HTTP forms) and unprefixed keys (from internal calls).

    Transforms form data like:
        {
            "Server_name": "My Server",
            "Server_cpu_cores": "4",
            "Server_cpu_cores__unit": "core",
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
            attr_key = key[len(prefix) :]
        else:
            attr_key = key

        annotation = None
        annotation_origin = None
        if attr_key in init_sig_params:
            annotation = init_sig_params[attr_key].annotation
            annotation = resolve_optional_annotation(annotation)
            annotation_origin = get_origin(annotation)
        if attr_key.endswith("__unit"):
            base_attr = attr_key[:-6]
            if base_attr not in parsed or "value" not in parsed[base_attr]:
                raise ValueError(f"Received unit field for unknown quantity {base_attr} in {object_type} form data.")
            parsed[base_attr]["value"] = float(parsed[base_attr]["value"])
            parsed[base_attr]["unit"] = value
        elif attr_key.endswith("__confidence"):
            base_attr = attr_key[: -len("__confidence")]
            parsed.setdefault(base_attr, {})["confidence"] = value if value else None
        elif attr_key.endswith("__comment"):
            base_attr = attr_key[: -len("__comment")]
            parsed.setdefault(base_attr, {})["comment"] = value if value else None
        elif attr_key.endswith("__source_id"):
            base_attr = attr_key[: -len("__source_id")]
            parsed.setdefault(base_attr, {}).setdefault("source", {})["id"] = value if value else None
        elif attr_key.endswith("__source_name"):
            base_attr = attr_key[: -len("__source_name")]
            parsed.setdefault(base_attr, {}).setdefault("source", {})["name"] = value if value else None
        elif attr_key.endswith("__source_link"):
            base_attr = attr_key[: -len("__source_link")]
            parsed.setdefault(base_attr, {}).setdefault("source", {})["link"] = value if value else None
        elif attr_key.endswith("__builder_selector"):
            # Builder selectors are UI-only and normally have no name; tolerate a submitted one without leaking it.
            continue
        elif attr_key.endswith("__weekly_pattern"):
            base_attr = attr_key[: -len("__weekly_pattern")]
            form_inputs = _parse_weekly_pattern_input(
                value,
                can_be_negative=base_attr in new_efootprint_obj_class.attributes_that_can_have_negative_values(),
            )
            parsed.setdefault(base_attr, {}).update({"form_inputs": form_inputs, "label": "no label"})
        elif "__" in attr_key:
            base_attr, field_name = attr_key.split("__", 1)
            parsed_value = parsed.setdefault(base_attr, {})
            parsed_value.setdefault("form_inputs", {})[field_name] = value
            parsed_value.setdefault("label", "no label")
        elif key.endswith("_form_data") and isinstance(value, str):
            parsed_key, parsed_form = _parse_inline_form_data(key, value)
            parsed[parsed_key] = parsed_form
        elif attr_key == PARENT_GROUP_MEMBERSHIPS_FIELD:
            parsed[attr_key] = _parse_parent_group_memberships(value)
        elif attr_key == "parent_link_count":
            # UI-only creation field: weight of the new entry in the parent's weighted dict.
            parsed[attr_key] = parse_count(value, error_prefix="Count") if value not in ("", None) else None
        elif attr_key in [
            "name",
            "id",
            "type_object_available",
            "efootprint_id_of_parent_to_link_to",
            "csrfmiddlewaretoken",
            "recomputation",
        ]:
            parsed[attr_key] = value
        elif annotation_origin and annotation_origin in (list, List):
            # List attribute - split by semicolon
            parsed[attr_key] = [v for v in str(value).split(";") if v]
        elif (
            annotation_origin is not None
            and isinstance(annotation_origin, type)
            and issubclass(annotation_origin, ExplainableObjectDict)
        ) or (
            annotation is not None and isinstance(annotation, type) and issubclass(annotation, ExplainableObjectDict)
        ):
            # Plain-number widget payloads become weights labeled with the relationship's static
            # count wording (e.g. "Times per journey"), matching the library's weight labels.
            count_label = FieldUIConfigProvider.get_config(attr_key, object_type).get("count_label", "no label")
            parsed[attr_key] = _parse_explainable_object_dict_input(
                value, field_name=attr_key, default_label=count_label
            )
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

    for attr_value in parsed.values():
        if isinstance(attr_value, dict) and attr_value and attr_value.keys() <= _METADATA_ONLY_KEYS:
            attr_value["_metadata_only"] = True

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
