from inspect import signature, _empty as empty_annotation
from typing import get_origin, List, get_args

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.job import JobBase
from efootprint.logger import logger

from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm

_extension_classes = [UsagePatternFromForm]
MODELING_OBJECT_CLASSES_DICT = {modeling_object_class.__name__: modeling_object_class
                                for modeling_object_class in ALL_EFOOTPRINT_CLASSES + _extension_classes}
ABSTRACT_EFOOTPRINT_MODELING_CLASSES = {"JobBase": JobBase, "ServerBase": ServerBase}


def generate_object_creation_structure(
    available_efootprint_classes: list, header: str, attributes_to_skip = None, model_web=None):
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
        default_values = efootprint_class.default_values()
        efootprint_class_str = efootprint_class.__name__
        default_values["name"] = efootprint_class_str
        class_fields, dynamic_lists = generate_dynamic_form(
            efootprint_class_str, default_values, attributes_to_skip, model_web)

        dynamic_form_dict["dynamic_lists"] += dynamic_lists

        form_sections.append({
            "category": efootprint_class_str,
            "header": f"{efootprint_class_str} creation",
            "fields": class_fields})

    return form_sections, dynamic_form_dict


def generate_object_edition_structure(web_object, attributes_to_skip=None):
    if attributes_to_skip is None:
        attributes_to_skip = []

    object_fields, dynamic_lists = generate_dynamic_form(
        web_object.class_as_simple_str, web_object.modeling_obj.__dict__, attributes_to_skip, web_object.model_web)

    return {"fields": object_fields}, {"dynamic_lists": dynamic_lists}


def generate_dynamic_form(
    efootprint_class_str: str, default_values: dict, attributes_to_skip: list, model_web):
    structure_fields = []
    dynamic_lists = []

    efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_str]
    list_values = efootprint_obj_class.list_values()
    conditional_list_values = efootprint_obj_class.conditional_list_values()
    id_prefix = efootprint_class_str
    init_sig_params = signature(efootprint_obj_class.__init__).parameters

    for attr_name in init_sig_params.keys():
        if attr_name in attributes_to_skip + ["self", "name"]:
            continue
        annotation = init_sig_params[attr_name].annotation
        if annotation is empty_annotation:
            logger.warning(
                f"Attribute {attr_name} in {efootprint_class_str} has no annotation so it has been set up to str by default.")
            annotation = str
        if get_origin(annotation) and get_origin(annotation) in (list, List):
            list_attribute_object_type_str = get_args(annotation)[0].__name__
            if attr_name in default_values.keys():
                selected = [elt.id for elt in default_values[attr_name]]
            else:
                selected = []
            structure_fields.append({
                "input_type": "select-multiple",
                "id": id_prefix + "_" + attr_name,
                "name": attr_name,
                "selected": selected,
                "options": [
                    {"label": attr_value.name, "value": attr_value.id}
                    for attr_value in model_web.get_efootprint_objects_from_efootprint_type(
                        list_attribute_object_type_str)]
            })
        elif issubclass(annotation, str):
            structure_fields.append({
                "input_type": "str",
                "id": id_prefix + "_" + attr_name,
                "name": attr_name,
                "default": default_values[attr_name]
            })
        elif issubclass(annotation, ExplainableQuantity):
            default = default_values[attr_name]
            structure_fields.append({
                "input_type": "input",
                "id": id_prefix + "_" + attr_name,
                "name": attr_name,
                "unit": f"{default.value.units:~P}",
                "default": round(default.magnitude, 2)
            })
        elif issubclass(annotation, ExplainableObject):
            if attr_name in list_values.keys():
                structure_fields.append({
                    "input_type": "select",
                    "id": id_prefix + "_" + attr_name,
                    "name": attr_name,
                    "selected": default_values[attr_name].value,
                    "options": [
                        {"label": str(attr_value), "value": str(attr_value)} for attr_value in list_values[attr_name]]
                })
            elif attr_name in conditional_list_values.keys():
                structure_fields.append({
                    "input_type": "datalist",
                    "id": id_prefix + "_" + attr_name,
                    "name": attr_name,
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
                structure_fields.append(
                    {
                        "input_type": "str",
                        "id": id_prefix + "_" + attr_name,
                        "name": attr_name,
                        "default": default_values[attr_name].value
                    }
                )
        elif issubclass(annotation, ModelingObject):
            mod_obj_attribute_object_type_str = annotation.__name__
            selection_options = model_web.get_efootprint_objects_from_efootprint_type(mod_obj_attribute_object_type_str)
            if attr_name in default_values.keys():
                selected = default_values[attr_name]
            else:
                selected = selection_options[0]
            structure_fields.append({
                "input_type": "select",
                "id": id_prefix + "_" + attr_name,
                "name": attr_name,
                "selected": selected.id,
                "options": [
                    {"label": attr_value.name, "value": attr_value.id} for attr_value in selection_options]
            })

    return structure_fields, dynamic_lists
