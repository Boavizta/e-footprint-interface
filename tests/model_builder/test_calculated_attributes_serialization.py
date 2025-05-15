import os
import json

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.logger import logger
from efootprint.utils.tools import time_it

from model_builder.class_structure import MODELING_OBJECT_CLASSES_DICT
from tests.test_structure import root_dir


def to_serializable_dict(explainable_object: ExplainableObject):
    explainable_object_dict = {
        "value_type": type(explainable_object.value).__name__,
        "label": explainable_object.label,
        "class_name": explainable_object.__class__.__name__
    }

    # Handle different value types appropriately
    if hasattr(explainable_object, "to_json"):
        explainable_object_dict["value"] = explainable_object.to_json()
    elif hasattr(explainable_object, "__dict__"):
        raise NotImplementedError(f"Serialization for {explainable_object.value.__class__.__name__} is not implemented.")
        # explainable_object_dict["value"] = explainable_object.value.__dict__
    else:
        # Handle primitive types or convert to string if needed
        explainable_object_dict["value"] = str(explainable_object.value)

    # Include modeling object relationship
    if explainable_object.modeling_obj_container is not None:
        explainable_object_dict["modeling_obj_container_id"] = explainable_object.modeling_obj_container.id
        explainable_object_dict["attr_name_in_mod_obj_container"] = explainable_object.attr_name_in_mod_obj_container

    # Include relationship information
    if explainable_object.left_parent is not None:
        explainable_object_dict["left_parent_id"] = id(explainable_object.left_parent) \
            if explainable_object.left_parent is not None else None
    if explainable_object.right_parent is not None:
        explainable_object_dict["right_parent_id"] = id(explainable_object.right_parent) \
            if explainable_object.right_parent is not None else None
    explainable_object_dict["direct_ancestors"] = [id(ancestor) for ancestor in explainable_object.direct_ancestors_with_id]
    explainable_object_dict["direct_children"] = [id(child) for child in explainable_object.direct_children_with_id]

    return explainable_object_dict


@time_it
def serialize_efootprint_object_attributes(efootprint_object):
    """
    Serializes the attributes of an EFootprint object into a dictionary format.
    This function is used to create a JSON representation of the object's attributes.
    """
    efootprint_obj_attributes_dict = {}
    for explainable_object in get_instance_attributes(efootprint_object, ExplainableObject).values():
        if explainable_object.attr_name_in_mod_obj_container in efootprint_object.calculated_attributes:
            efootprint_obj_attributes_dict[id(explainable_object)] = to_serializable_dict(explainable_object)
        else:
            efootprint_obj_attributes_dict[id(explainable_object)] = {
                "modeling_obj_container_id": explainable_object.modeling_obj_container.id,
                "attr_name_in_mod_obj_container": explainable_object.attr_name_in_mod_obj_container,
            }

    return efootprint_obj_attributes_dict

# Load the system data
with open(os.path.join(root_dir, "model_builder", "system_with_multiple_servers_and_ups.json"), "r") as file:
    system_data = json.load(file)

class_obj_dict, flat_obj_dict = json_to_system(
    system_data, launch_system_computations=True, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)

@time_it
def serialize_system(input_flat_obj_dict):
    calc_attr_dict = {}

    for efootprint_object in input_flat_obj_dict.values():
        efootprint_object_attributes_dict = serialize_efootprint_object_attributes(efootprint_object)
        calc_attr_dict.update(efootprint_object_attributes_dict)

    return calc_attr_dict

# Serialize the system and get the calculated attributes dictionary
calculated_attributes_dict = serialize_system(flat_obj_dict)

# Save the calculated attributes dictionary to a JSON file
with open(os.path.join(root_dir, "model_builder", "calculated_attributes_serialization.json"), "w") as f:
    json.dump(calculated_attributes_dict, f, indent=4)
