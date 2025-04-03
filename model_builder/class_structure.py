from inspect import signature
from typing import get_origin, List, get_args

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.job import JobBase

from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm

_extension_classes = [UsagePatternFromForm]
MODELING_OBJECT_CLASSES_DICT = {modeling_object_class.__name__: modeling_object_class
                                for modeling_object_class in ALL_EFOOTPRINT_CLASSES + _extension_classes}
ABSTRACT_EFOOTPRINT_MODELING_CLASSES = {"JobBase": JobBase, "ServerBase": ServerBase}


def efootprint_class_structure(efootprint_class_str: str, model_web=None):
    efootprint_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_str]
    conditional_list_values = efootprint_class.conditional_list_values()
    structure = {
        "numerical_attributes": [],
        "hourly_quantities_attributes": [],
        "modeling_obj_attributes": [],
        "list_attributes": [],
        "str_attributes": [],
        "conditional_str_attributes": [
            {
                "attr_name": key,
                "depends_on": value["depends_on"],
                "conditional_list_values": {
                    str(conditional_value): [str(possible_value) for possible_value in possible_values]
                    for conditional_value, possible_values in value["conditional_list_values"].items()
                }
            }
            for key, value in conditional_list_values.items()]
    }
    efootprint_class_default_values = efootprint_class.default_values()
    efootprint_class_list_values = efootprint_class.list_values()
    init_sig_params = signature(efootprint_class.__init__).parameters
    for attr_name in init_sig_params.keys():
        annotation = init_sig_params[attr_name].annotation
        if get_origin(annotation):
            if get_origin(annotation) in (list, List):
                object_type = get_args(annotation)[0]
                structure["list_attributes"].append({"attr_name": attr_name, "object_type": object_type.__name__})
        elif issubclass(annotation, ExplainableQuantity):
            default_value = efootprint_class_default_values[attr_name].value
            structure["numerical_attributes"].append(
                {"attr_name": attr_name, "unit": f"{default_value.units:~P}",
                 "long_unit": str(default_value.units),
                 "default_value": round(default_value.magnitude, 2)})
        elif issubclass(annotation, ExplainableHourlyQuantities):
            structure["hourly_quantities_attributes"].append({"attr_name": attr_name})
        elif issubclass(annotation, ExplainableObject):
            if attr_name in efootprint_class_list_values.keys():
                structure["str_attributes"].append(
                    {"attr_name": attr_name,
                     "list_values": [str(value) for value in efootprint_class.list_values()[attr_name]]}
                    )
            elif attr_name not in conditional_list_values.keys():
                structure["str_attributes"].append(
                    {"attr_name": attr_name, "default_value": str(efootprint_class_default_values[attr_name].value)})
        elif issubclass(annotation, ModelingObject):
            structure["modeling_obj_attributes"].append({"attr_name": attr_name, "object_type": annotation.__name__})

        if model_web is not None:
            for attribute_type in structure.keys():
                for attribute in structure[attribute_type]:
                    if "object_type" in attribute.keys():
                        attribute["existing_objects"] = model_web.get_web_objects_from_efootprint_type(
                            attribute["object_type"])

    return structure


def generate_object_creation_structure(available_efootprint_classes: list, header: str, attributes_to_skip = None):
    if attributes_to_skip is None:
        attributes_to_skip = []

    dynamic_form_dict = {
        "switch_item": "type_object_available",
        "switch_values": [available_class.__name__ for available_class in available_efootprint_classes],
        "dynamic_lists": []}

    type_efootprint_classes_available = {
        "category": "efootprint_classes_available",
        "header": header,
        "class": "",
        "fields": [{
            "input_type": "select",
            "id": "type_object_available",
            "name": "type_object_available",
            "options": [{"label": available_class.__name__, "value": available_class.__name__}
                        for available_class in available_efootprint_classes]
        }
        ]
    }

    form_sections = [type_efootprint_classes_available]

    for index, efootprint_class in enumerate(available_efootprint_classes):
        class_structure = efootprint_class_structure(efootprint_class.__name__)
        class_fields, dynamic_lists = format_structure_for_dynamic_form(class_structure, attributes_to_skip)

        if dynamic_lists:
            dynamic_form_dict["dynamic_lists"].extend(
                [elt for elt in dynamic_lists
                 if elt["input"] not in [elt["input"] for elt in dynamic_form_dict["dynamic_lists"]]])


        form_sections.append({
            "category": efootprint_class.__name__,
            "header": f"{efootprint_class.__name__} creation",
            "fields": class_fields})

    return form_sections, dynamic_form_dict


def generate_object_edition_structure(web_object, attributes_to_skip=None):
    if attributes_to_skip is None:
        attributes_to_skip = []

    web_object_structure = web_object.generate_structure()
    object_fields, dynamic_lists = format_structure_for_dynamic_form(
        web_object_structure, attributes_to_skip)

    return {"fields": object_fields, "modeling_obj_attributes": web_object_structure["modeling_obj_attributes"],
            "list_attributes": web_object_structure["list_attributes"]}, {"dynamic_lists": dynamic_lists}


def format_structure_for_dynamic_form(input_structure, attributes_to_skip):
    structure_fields = []
    dynamic_lists = []

    for str_attribute_dict in input_structure["str_attributes"]:
        if str_attribute_dict["attr_name"] in attributes_to_skip:
            continue
        if "list_values" in str_attribute_dict.keys():
            selected = None
            if "attr_value" in str_attribute_dict.keys():
                selected = str_attribute_dict["attr_value"].value
            structure_fields.append({
                "input_type": "select",
                "id": str_attribute_dict["attr_name"],
                "name": str_attribute_dict["attr_name"],
                "selected": selected,
                "options": [
                    {"label": attr_value, "value": attr_value} for attr_value in str_attribute_dict["list_values"]]
            })
        else:
            structure_fields.append(
                {
                    "input_type": "str",
                    "id": str_attribute_dict["attr_name"],
                    "name": str_attribute_dict["attr_name"],
                    "default": str_attribute_dict["default_value"]
                }
            )
    for conditional_str_attribute_dict in input_structure["conditional_str_attributes"]:
        if conditional_str_attribute_dict["attr_name"] in attributes_to_skip:
            continue
        selected = None
        if "attr_value" in conditional_str_attribute_dict.keys():
            selected = conditional_str_attribute_dict["attr_value"].value
        structure_fields.append({
            "input_type": "datalist",
            "id": conditional_str_attribute_dict["attr_name"],
            "name": conditional_str_attribute_dict["attr_name"],
            "selected": selected,
            "options": None
        })
        dynamic_lists.append(
                {
                    "input": conditional_str_attribute_dict["attr_name"],
                    "filter_by": conditional_str_attribute_dict["depends_on"],
                    "list_value": conditional_str_attribute_dict["conditional_list_values"]
                })
    for numerical_attribute in input_structure["numerical_attributes"]:
        if numerical_attribute["attr_name"] in attributes_to_skip:
            continue
        default_value = numerical_attribute["default_value"]
        if "attr_value" in numerical_attribute.keys():
            default_value = numerical_attribute["attr_value"].rounded_magnitude
        structure_fields.append({
            "input_type": "input",
            "id": numerical_attribute["attr_name"],
            "name": numerical_attribute["attr_name"],
            "unit": numerical_attribute["unit"],
            "default": default_value
        })

    return structure_fields, dynamic_lists
