import json
from copy import copy, deepcopy
from decimal import Decimal
from inspect import _empty as empty_annotation
from typing import get_origin, List, get_args, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params
from efootprint.builders.timeseries.explainable_hourly_quantities_from_form_inputs import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import ExplainableRecurrentQuantitiesFromConstant

from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.efootprint_to_web_mapping import get_corresponding_web_class
from model_builder.domain.type_annotation_utils import resolve_optional_annotation

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


def _format_decimal_for_number_input(value: Decimal) -> str:
    """Format a Decimal for an HTML number input without losing precision."""
    if value == value.to_integral():
        return str(int(value))
    return format(value.normalize(), "f")


def _stringify_form_value(value):
    """Convert numeric default values to strings for template rendering."""
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return _format_decimal_for_number_input(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return {key: _stringify_form_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_stringify_form_value(val) for val in value]
    if isinstance(value, tuple):
        return tuple(_stringify_form_value(val) for val in value)
    return value


def _get_compatible_step(value: Decimal, configured_step: int | float | None) -> str:
    """Return the configured step unless it rejects the rendered value."""
    step_decimal = Decimal(str(configured_step if configured_step is not None else 0.1))
    if step_decimal > 0 and value % step_decimal == 0:
        return _stringify_form_value(configured_step if configured_step is not None else 0.1)

    decimal_places = max(0, -value.as_tuple().exponent)
    return _format_decimal_for_number_input(Decimal("1").scaleb(-decimal_places))


def format_magnitude_for_number_input(magnitude) -> str:
    """Format a numeric magnitude as a canonical dot-decimal string for <input type=number>."""
    return _format_decimal_for_number_input(Decimal(str(magnitude)))


def compatible_step_for_magnitude(magnitude, default_step: float = 0.1) -> str:
    """Return a step value compatible with the given magnitude (falling back to default_step)."""
    return _get_compatible_step(Decimal(str(magnitude)), default_step)


def _build_dict_count_field_from_annotation(
    attr_name: str, id_prefix: str, type_arg_str: str,
    default_values: dict, model_web: "ModelWeb", obj_to_edit: "ModelingObjectWeb" = None) -> dict:
    """Build a dict_count field payload for an `ExplainableObjectDict[X]` attribute."""
    available_web_objects = model_web.get_web_objects_from_efootprint_type(type_arg_str)
    if obj_to_edit is not None:
        available_web_objects = obj_to_edit.filter_dict_count_options(attr_name, available_web_objects)
    options = sorted(
        [{"value": obj.efootprint_id, "label": obj.name} for obj in available_web_objects],
        key=lambda option: option["label"].lower(),
    )
    selected_raw = default_values.get(attr_name) or {}
    selected_counts = {key.id: count.value.magnitude for key, count in selected_raw.items()}
    return {
        "input_type": "dict_count",
        "web_id": f"{id_prefix}_{attr_name}",
        "options": options,
        "options_json": json.dumps(options),
        "selected_json": json.dumps(selected_counts),
    }


def generate_object_creation_structure(
    efootprint_class_str: str, available_efootprint_classes: list, model_web: "ModelWeb"):
    dynamic_form_dict = {
        "switch_item": "type_object_available",
        "switch_values": [available_class.__name__ for available_class in available_efootprint_classes],
        "dynamic_lists": []}

    type_efootprint_classes_available = {
        "category": "efootprint_classes_available",
        "header": f"{ClassUIConfigProvider.get_label(efootprint_class_str)} selection",
        "fields": [{
            "input_type": "select_object",
            "web_id": "type_object_available",
            "label": ClassUIConfigProvider.get_type_object_available_label(efootprint_class_str),
            "options": [
                {"label": ClassUIConfigProvider.get_more_descriptive_label(available_class.__name__),
                    "value": available_class.__name__}
                for available_class in available_efootprint_classes]
        }
        ]
    }

    form_sections = [type_efootprint_classes_available]

    for index, efootprint_class in enumerate(available_efootprint_classes):
        default_values = deepcopy(efootprint_class.default_values)
        available_efootprint_class_str = efootprint_class.__name__
        available_efootprint_class_label = ClassUIConfigProvider.get_label(available_efootprint_class_str)
        default_values["name"] = (
            f"{available_efootprint_class_label} "
            f"{len(model_web.get_web_objects_from_efootprint_type(available_efootprint_class_str)) + 1}")
        corresponding_web_class = get_corresponding_web_class(efootprint_class)
        for default_web_attr in corresponding_web_class.default_values:
            default_values[default_web_attr] = copy(corresponding_web_class.default_values[default_web_attr])

        class_fields, class_fields_advanced, dynamic_lists = generate_dynamic_form(
            available_efootprint_class_str, default_values, model_web)

        dynamic_form_dict["dynamic_lists"] += dynamic_lists

        form_sections.append({
            "category": available_efootprint_class_str,
            "header": f"{available_efootprint_class_label} creation",
            "fields": class_fields,
            "advanced_fields": class_fields_advanced,
        })

    return form_sections, dynamic_form_dict


def generate_select_multiple_field(
    attr_name: str, id_prefix: str, selected_objects: list, child_type_str: str, model_web: "ModelWeb"
) -> dict:
    """Build a select_multiple field dict for a list attribute.

    Args:
        attr_name: The list attribute name (e.g. 'jobs')
        id_prefix: The class name prefix used for web_id (e.g. 'UsageJourneyStep')
        selected_objects: Raw ModelingObject instances currently linked
        child_type_str: Class name of child objects (e.g. 'Job')
        model_web: ModelWeb instance for querying available objects
    """
    field_config = FieldUIConfigProvider.get_config(attr_name)
    unselected = [
        {"value": option.id, "label": option.name}
        for option in model_web.get_efootprint_objects_from_efootprint_type(child_type_str)
        if option not in selected_objects
    ]
    selected = [{"value": elt.id, "label": elt.name} for elt in selected_objects]
    return {
        "web_id": f"{id_prefix}_{attr_name}",
        "attr_name": attr_name,
        "label": field_config.get("label", attr_name),
        "tooltip": field_config.get("tooltip", False),
        "input_type": "select_multiple",
        "selected": selected,
        "unselected": unselected,
        "selected_json": json.dumps(selected),
        "unselected_json": json.dumps(unselected),
    }


def generate_dynamic_form(
    efootprint_class_str: str, default_values: dict, model_web: "ModelWeb",
    obj_to_edit: "ModelingObjectWeb" = None):
    structure_fields = []
    structure_fields_advanced = []
    dynamic_lists = []
    efootprint_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_str]

    list_values = efootprint_class.list_values
    conditional_list_values = efootprint_class.conditional_list_values
    id_prefix = efootprint_class_str
    init_sig_params = get_init_signature_params(efootprint_class)

    attributes_that_can_have_negative_values = efootprint_class.attributes_that_can_have_negative_values()
    corresponding_web_class = get_corresponding_web_class(efootprint_class)
    available_sources = [{"id": s.id, "name": s.name, "link": s.link} for s in model_web.available_sources]
    for attr_name in init_sig_params.keys():
        if attr_name in corresponding_web_class.attributes_to_skip_in_forms + ["self"]:
            continue
        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {efootprint_class_str} has no annotation so it has been set up to str by default.")
            annotation = str
        annotation = resolve_optional_annotation(annotation)
        field_config = FieldUIConfigProvider.get_config(attr_name)
        structure_field = {
            "web_id": id_prefix + "_" + attr_name,
            "attr_name": attr_name,
            "label": field_config.get("label", attr_name),
            "tooltip": field_config.get("tooltip", False)
        }
        annotation_origin = get_origin(annotation)
        if annotation_origin and annotation_origin in (list, List):
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            selected_objects = default_values.get(attr_name, [])
            structure_field.update(
                generate_select_multiple_field(attr_name, id_prefix, selected_objects, list_attribute_object_type_str, model_web)
            )
        elif (annotation_origin is not None
              and isinstance(annotation_origin, type)
              and issubclass(annotation_origin, ExplainableObjectDict)):
            type_arg = get_args(annotation)[0]
            type_arg_str = type_arg if isinstance(type_arg, str) else type_arg.__name__
            structure_field.update(
                _build_dict_count_field_from_annotation(
                    attr_name, id_prefix, type_arg_str, default_values, model_web, obj_to_edit)
            )
        elif issubclass(annotation, str):
            structure_field.update({
                "input_type": "str",
                "default": _stringify_form_value(default_values[attr_name])
            })
        elif issubclass(annotation, ModelingObject):
            mod_obj_attribute_object_type_str = annotation.__name__
            selection_options = model_web.get_efootprint_objects_from_efootprint_type(mod_obj_attribute_object_type_str)
            if attr_name in default_values.keys():
                selected = default_values[attr_name]
            else:
                if selection_options:
                    selected = selection_options[0]
                else:
                    raise ValueError(
                        f"No default value for {attr_name} in {efootprint_class_str}. This attribute should maybe "
                        f"be ignored through the attributes_to_skip_in_forms class attribute ?")
            structure_field.update({
                "input_type": "select_object",
                "selected": selected.id,
                "options": [
                    {"label": attr_value.name, "value": attr_value.id} for attr_value in selection_options]
            })
        else:
            default = default_values[attr_name]
            source_json = {"name":default.source.name, "link":default.source.link} if default.source else None
            metadata = {
                "confidence": default.confidence,
                "comment": default.comment,
                "source": {
                    "id": default.source.id,
                    "name": default.source.name,
                    "link": default.source.link,
                } if default.source else None,
                "available_sources": available_sources,
            }
            structure_field.update({"source": source_json, "metadata": metadata})
            if issubclass(annotation, ExplainableQuantity):
                default_value_decimal = Decimal(str(default.magnitude))
                default_value = _format_decimal_for_number_input(default_value_decimal)
                step = _get_compatible_step(default_value_decimal, field_config.get("step", 0.1))
                structure_field.update({
                    "input_type": "explainable_quantity",
                    "unit": "dimensionless" if default.value.units == u.dimensionless else f"{default.value.units:~P}",
                    "default": default_value,
                    "can_be_negative": attr_name in attributes_that_can_have_negative_values,
                    "step": step
                })
            elif issubclass(annotation, ExplainableHourlyQuantities):
                # Check if this is a form-editable timeseries or a read-only one
                if isinstance(default, ExplainableHourlyQuantitiesFromFormInputs):
                    # Editable: extract form inputs
                    structure_field.update({
                        "input_type": "hourly_quantities_from_growth",
                        "default": _stringify_form_value(default.form_inputs),
                        "subfields_ui_config": corresponding_web_class.hourly_quantities_from_growth_ui_config,
                    })
                else:
                    # Read-only: base efootprint class
                    structure_field.update({"input_type": "timeseries_input", "default": default})
            elif issubclass(annotation, ExplainableRecurrentQuantities):
                # Check if this is a form-editable timeseries or a read-only one
                if isinstance(default, ExplainableRecurrentQuantitiesFromConstant):
                    # Editable: extract constant value
                    structure_field.update({
                        "input_type": "recurrent_quantities_from_constant",
                        "default": _stringify_form_value(default.form_inputs)
                    })
                else:
                    # Read-only: base efootprint class
                    structure_field.update({"input_type": "recurrent_timeseries_input", "default": default})
            elif issubclass(annotation, ExplainableObject):
                structure_field.update({"default": _stringify_form_value(default.value)})
                if attr_name in list_values.keys():
                    structure_field.update({
                        "input_type": "select_str_input",
                        "selected": default_values[attr_name].value,
                        "options": [
                            {"label": str(attr_value), "value": str(attr_value)}
                            for attr_value in list_values[attr_name]]
                    })
                elif attr_name in conditional_list_values.keys():
                    structure_field.update({
                        "input_type": "datalist",
                        "selected": default_values[attr_name].value,
                        "options": None
                    })
                    dynamic_lists.append(
                        {
                            "input_id": id_prefix + "_" + attr_name,
                            "filter_by": id_prefix + "_" + conditional_list_values[attr_name]["depends_on"],
                            "list_value": {
                                str(conditional_value): [str(possible_value) for possible_value in possible_values]
                                for conditional_value, possible_values in
                                conditional_list_values[attr_name]["conditional_list_values"].items()
                            }
                        })
                else:
                    structure_field.update({"input_type": "str"})

        if field_config.get("is_advanced_parameter", False):
            structure_fields_advanced.append(structure_field)
        else:
            structure_fields.append(structure_field)

    # Reorder fields so timeseries fields appear last (preserving order within each group)
    timeseries_input_types = ["hourly_quantities_from_growth", "recurrent_quantities_from_constant",
                               "timeseries_input", "recurrent_timeseries_input"]

    non_timeseries_fields = [f for f in structure_fields if f["input_type"] not in timeseries_input_types]
    timeseries_fields = [f for f in structure_fields if f["input_type"] in timeseries_input_types]
    structure_fields = non_timeseries_fields + timeseries_fields

    non_timeseries_fields_advanced = [f for f in structure_fields_advanced if f["input_type"] not in timeseries_input_types]
    timeseries_fields_advanced = [f for f in structure_fields_advanced if f["input_type"] in timeseries_input_types]
    structure_fields_advanced = non_timeseries_fields_advanced + timeseries_fields_advanced

    return structure_fields, structure_fields_advanced, dynamic_lists
