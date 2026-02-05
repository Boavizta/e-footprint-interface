from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity

from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING


def create_post_data_from_class_default_values(
    name: str,
    efootprint_class_name: str,
    **overrides: Any,
) -> dict[str, Any]:
    """Create HTTP-like form data from an e-footprint class default values.

    This helper intentionally mirrors the legacy `tests__old` behavior:
    it produces prefixed keys (e.g., `Server_cpu_cores`) plus `*_unit` fields
    for quantities. Integration tests can then run the real adapter parser
    (`parse_form_data`) on top of it.
    """
    if efootprint_class_name not in MODELING_OBJECT_CLASSES_DICT:
        raise ValueError(f"Class {efootprint_class_name} not found in MODELING_OBJECT_CLASSES_DICT")

    data: dict[str, Any] = {
        "type_object_available": efootprint_class_name,
        f"{efootprint_class_name}_name": name,
    }

    # If web class has default, use them instead of efootprint class defaults
    web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[efootprint_class_name]
    efootprint_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_name]
    class_to_use_for_defaults = efootprint_class
    if efootprint_class_name in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING and len(web_class.default_values) >= 1:
        class_to_use_for_defaults = web_class

    form_inputs_overrides = {}
    for key, value in overrides.items():
        if "__" in key:
            base_key, sub_key = key.split("__", 1)
            form_inputs_overrides[base_key] = {sub_key: value}

    for attr_name, default_value in class_to_use_for_defaults.default_values.items():
        if attr_name in overrides or attr_name in web_class.attributes_to_skip_in_forms:
            continue
        form_inputs = {}
        if attr_name in form_inputs_overrides:
            # Case of form_inputs
            form_inputs = deepcopy(default_value.form_inputs)
            form_inputs.update(form_inputs_overrides[attr_name])
        if hasattr(default_value, "form_inputs"):
            for form_input_key, form_input_value in form_inputs.items():
                data[f"{efootprint_class_name}_{attr_name}__{form_input_key}"] = form_input_value
        else:
            magnitude = getattr(default_value, "magnitude", None)
            unit = getattr(default_value, "unit", None)

            # Only auto-fill scalar quantities. Some defaults (e.g., recurrent arrays) cannot be expressed as a single
            # `value` + `unit` pair compatible with the HTTP form parser.
            try:
                float(magnitude)
            except (TypeError, ValueError):
                continue

            data[f"{efootprint_class_name}_{attr_name}"] = str(magnitude)
            data[f"{efootprint_class_name}_{attr_name}_unit"] = str(unit)

    for key, value in overrides.items():
        if "form_data" in key:
            # Handle nested form data (e.g., for Server's storage list)
            data[key] = json.dumps(value)
        elif isinstance(value, ExplainableQuantity):
            data[f"{efootprint_class_name}_{key}"] = str(value.magnitude)
            data[f"{efootprint_class_name}_{key}_unit"] = str(value.unit)
        else:
            data[f"{efootprint_class_name}_{key}"] = value

    return data
