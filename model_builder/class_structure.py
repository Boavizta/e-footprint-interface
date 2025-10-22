from copy import deepcopy
from inspect import _empty as empty_annotation
from typing import get_origin, List, get_args, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.all_classes_in_order import CANONICAL_COMPUTATION_ORDER
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.form_references import FORM_TYPE_OBJECT, FORM_FIELD_REFERENCES

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


def generate_object_creation_structure(
    efootprint_class_str: str, available_efootprint_classes: list, model_web: "ModelWeb"):
    dynamic_form_dict = {
        "switch_item": "type_object_available",
        "switch_values": [available_class.__name__ for available_class in available_efootprint_classes],
        "dynamic_lists": []}

    type_efootprint_classes_available = {
        "category": "efootprint_classes_available",
        "header": f"{FORM_TYPE_OBJECT[efootprint_class_str]["label"]} selection",
        "fields": [{
            "input_type": "select_object",
            "web_id": "type_object_available",
            "label": FORM_TYPE_OBJECT[efootprint_class_str]["type_object_available"],
            "options": [
                {"label": FORM_TYPE_OBJECT[available_class.__name__].get(
                    "more_descriptive_label_for_select_inputs", FORM_TYPE_OBJECT[available_class.__name__]["label"]),
                    "value": available_class.__name__}
                for available_class in available_efootprint_classes]
        }
        ]
    }

    form_sections = [type_efootprint_classes_available]

    for index, efootprint_class in enumerate(available_efootprint_classes):
        default_values = deepcopy(efootprint_class.default_values)
        available_efootprint_class_str = efootprint_class.__name__
        available_efootprint_class_label = FORM_TYPE_OBJECT[available_efootprint_class_str]["label"]
        default_values["name"] = (
            f"{available_efootprint_class_label} "
            f"{len(model_web.get_web_objects_from_efootprint_type(available_efootprint_class_str)) + 1}")
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


def generate_object_creation_context(
    efootprint_class_str: str, available_efootprint_classes: list, model_web: "ModelWeb"):
    form_sections, dynamic_form_data = generate_object_creation_structure(
        efootprint_class_str, available_efootprint_classes, model_web)

    context_data = {"form_sections": form_sections,
                    "header_name": "Add new " + FORM_TYPE_OBJECT[efootprint_class_str]["label"].lower(),
                    "object_type": efootprint_class_str,
                    "obj_formatting_data": FORM_TYPE_OBJECT[efootprint_class_str]}

    return context_data


def generate_dynamic_form(
    efootprint_class_str: str, default_values: dict, model_web: "ModelWeb"):
    from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
    structure_fields = []
    structure_fields_advanced = []
    dynamic_lists = []
    efootprint_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_str]
    if efootprint_class.__name__ in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING:
        corresponding_web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[efootprint_class.__name__]
    else:
        corresponding_canonical_class = None
        for canonical_class in CANONICAL_COMPUTATION_ORDER:
            if issubclass(efootprint_class, canonical_class):
                corresponding_canonical_class = canonical_class
                break
        if corresponding_canonical_class is None:
            raise ValueError(f"No corresponding canonical class found for {efootprint_class_str}.")
        corresponding_web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[corresponding_canonical_class.__name__]


    list_values = efootprint_class.list_values
    conditional_list_values = efootprint_class.conditional_list_values
    id_prefix = efootprint_class_str
    init_sig_params = get_init_signature_params(efootprint_class)

    attributes_that_can_have_negative_values = efootprint_class.attributes_that_can_have_negative_values()

    for attr_name in init_sig_params.keys():
        if attr_name in corresponding_web_class.attributes_to_skip_in_forms + ["self"]:
            continue
        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {efootprint_class_str} has no annotation so it has been set up to str by default.")
            annotation = str
        structure_field = {
            "web_id": id_prefix + "_" + attr_name,
            "attr_name": attr_name,
            "label": FORM_FIELD_REFERENCES[attr_name]["label"],
            "tooltip": FORM_FIELD_REFERENCES[attr_name].get("tooltip", False)
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
            if attr_name == "devices":
                # Special case for UsagePatternFromForm’s devices, to remove possibility for user to select multiple
                # devices for now.
                structure_field.update({
                    "input_type": "select_object",
                    "options": selected + unselected,
                    "selected": selected[0]["value"] if len(selected) > 0 else unselected[0]["value"]
                })
            else:
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
            structure_field.update({"default": default.value, "source": source_json})
            if issubclass(annotation, ExplainableQuantity):
                default_value = float(round(default.magnitude, 2))
                step = FORM_FIELD_REFERENCES[attr_name].get("step", 0.1)
                if default_value == int(default_value):
                    default_value = int(default_value)
                else:
                    step = 0.1
                structure_field.update({
                    "input_type": "input",
                    "unit": f"{default.value.units:~P}",
                    "default": default_value,
                    "can_be_negative": attr_name in attributes_that_can_have_negative_values,
                    "step": step
                })
            elif issubclass(annotation, ExplainableHourlyQuantities):
                structure_field.update({"input_type": "timeseries_input", "default": str(default)})
            elif issubclass(annotation, ExplainableRecurrentQuantities):
                structure_field.update({"input_type": "recurrent_timeseries_input", "default": str(default)})
            elif issubclass(annotation, ExplainableObject):
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

        if FORM_FIELD_REFERENCES[attr_name].get("is_advanced_parameter", False):
            structure_fields_advanced.append(structure_field)
        else:
            structure_fields.append(structure_field)

    return structure_fields, structure_fields_advanced, dynamic_lists
