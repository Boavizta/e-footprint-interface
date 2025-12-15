from copy import copy, deepcopy
from inspect import _empty as empty_annotation
from typing import get_origin, List, get_args, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.efootprint_to_web_mapping import get_corresponding_web_class
from model_builder.domain.entities.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import ExplainableHourlyQuantitiesFromFormInputs
from model_builder.domain.entities.efootprint_extensions.explainable_recurrent_quantities_from_constant import ExplainableRecurrentQuantitiesFromConstant

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


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


def generate_dynamic_form(
    efootprint_class_str: str, default_values: dict, model_web: "ModelWeb"):
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
    for attr_name in init_sig_params.keys():
        if attr_name in corresponding_web_class.attributes_to_skip_in_forms + ["self"]:
            continue
        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {efootprint_class_str} has no annotation so it has been set up to str by default.")
            annotation = str
        field_config = FieldUIConfigProvider.get_config(attr_name)
        structure_field = {
            "web_id": id_prefix + "_" + attr_name,
            "attr_name": attr_name,
            "label": field_config.get("label", attr_name),
            "tooltip": field_config.get("tooltip", False)
        }
        if get_origin(annotation) and get_origin(annotation) in (list, List):
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            if attr_name in default_values:
                selected = default_values[attr_name]
            else:
                selected = []
            unselected = [
                {"value":option.id,"label":option.name}
                for option in model_web.get_efootprint_objects_from_efootprint_type(list_attribute_object_type_str)
                if option not in selected]
            selected = [{"value": elt.id, "label": elt.name} for elt in selected]
            structure_field.update({
                "input_type": "select_multiple",
                "selected": selected,
                "unselected": unselected
            })
        elif issubclass(annotation, str):
            structure_field.update({
                "input_type": "str",
                "default": default_values[attr_name]
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
            structure_field.update({"source": source_json})
            if issubclass(annotation, ExplainableQuantity):
                default_value = float(round(default.magnitude, 2))
                step = field_config.get("step", 0.1)
                if default_value == int(default_value):
                    default_value = int(default_value)
                else:
                    step = 0.1
                structure_field.update({
                    "input_type": "input",
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
                        "default": default.form_inputs
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
                        "default": default.form_inputs
                    })
                else:
                    # Read-only: base efootprint class
                    structure_field.update({"input_type": "recurrent_timeseries_input", "default": default})
            elif issubclass(annotation, ExplainableObject):
                structure_field.update({"default": default.value})
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
