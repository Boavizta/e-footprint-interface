import os
import gzip
import base64
import json
import zstandard as zstd

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities, \
    EmptyExplainableObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.logger import logger
from efootprint.utils.tools import time_it

from model_builder.class_structure import MODELING_OBJECT_CLASSES_DICT
from tests.test_structure import root_dir


import array
@time_it
def compress_value(value):
    arr = array.array("d", value)  # "d" is double-precision float
    cctx = zstd.ZstdCompressor(level=1)
    compressed = cctx.compress(arr.tobytes())
    return base64.b64encode(compressed).decode("utf-8")


def to_serializable_dict(explainable_object: ExplainableObject):
    explainable_object_dict = {
        "class_name": explainable_object.__class__.__name__
    }

    if isinstance(explainable_object, ExplainableQuantity):
        explainable_object_dict.update(explainable_object.to_json())
    elif isinstance(explainable_object, ExplainableHourlyQuantities):
        explainable_object_dict.update(
            {
                "label": explainable_object.label,
                "values": compress_value(explainable_object.value["value"].values._data.tolist()),
                "unit": str(explainable_object.value.dtypes.iloc[0].units),
                "start_date": explainable_object.value.index[0].strftime("%Y-%m-%d %H:%M:%S")
            }
        )
    elif isinstance(explainable_object, EmptyExplainableObject):
        explainable_object_dict.update(explainable_object.to_json())
    elif isinstance(explainable_object, ExplainableObjectDict):
        output = {}
        for value in explainable_object.values():
            output.update(to_serializable_dict(value))
        return output
    elif isinstance(explainable_object, ExplainableObject):
        explainable_object_dict.update(explainable_object.to_json())
    else:
        raise ValueError(f"Unsupported type: {explainable_object.__class__.__name__}. object {explainable_object}.")

    # Include modeling object relationship
    if explainable_object.modeling_obj_container is not None:
        explainable_object_dict["modeling_obj_container_id"] = explainable_object.modeling_obj_container.id
        explainable_object_dict["attr_name_in_mod_obj_container"] = explainable_object.attr_name_in_mod_obj_container

    explainable_object_dict["direct_ancestors"] = [
        str((ancestor.modeling_obj_container.id, ancestor.attr_name_in_mod_obj_container, ancestor.key_in_dict.id if ancestor.dict_container is not None else None))
        for ancestor in explainable_object.direct_ancestors_with_id]
    explainable_object_dict["direct_children"] = [
        str((child.modeling_obj_container.id, child.attr_name_in_mod_obj_container, child.key_in_dict.id if child.dict_container is not None else None))
        for child in explainable_object.direct_children_with_id]

    return {str((explainable_object.modeling_obj_container.id, explainable_object.attr_name_in_mod_obj_container, explainable_object.key_in_dict.id if explainable_object.dict_container is not None else None)): explainable_object_dict}


@time_it
def serialize_efootprint_object_attributes(efootprint_object):
    """
    Serializes the attributes of an EFootprint object into a dictionary format.
    This function is used to create a JSON representation of the object's attributes.
    """
    efootprint_obj_attributes_dict = {}
    for calculated_attribute_name in efootprint_object.calculated_attributes:
        explainable_object = getattr(efootprint_object, calculated_attribute_name)
        efootprint_obj_attributes_dict.update(to_serializable_dict(explainable_object))

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
from time import time
start = time()
with gzip.open(
    os.path.join(root_dir, "model_builder", "calculated_attributes_serialization.zip"), "wt", encoding="utf-8") as f:
    json.dump(calculated_attributes_dict, f)
end = time()
logger.info(f"zip dumping took {end - start} seconds.")

start = time()
with open(
    os.path.join(root_dir, "model_builder", "calculated_attributes_serialization.json"), "w") as f:
    json.dump(calculated_attributes_dict, f, indent=4)
end = time()
logger.info(f"json dumping took {end - start} seconds.")

# test time it takes to load the json file
start = time()
with open(
    os.path.join(root_dir, "model_builder", "calculated_attributes_serialization.json"), "r") as f:
    loaded_dict = json.load(f)

end = time()
logger.info(f"json loading took {end - start} seconds.")

# test time it takes to load the zip file
start = time()
with gzip.open(
    os.path.join(root_dir, "model_builder", "calculated_attributes_serialization.zip"), "rt", encoding="utf-8") as f:
    loaded_dict = json.load(f)
end = time()
logger.info(f"zip loading took {end - start} seconds.")
