import os
import re
import json
from dataclasses import dataclass
from unittest import TestCase
import sys
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.modeling_object import css_escape
from efootprint.constants.countries import Countries
from efootprint.core.hardware.edge_device import EdgeComputer
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.all_classes_in_order import SERVICE_CLASSES, SERVER_CLASSES, SERVICE_JOB_CLASSES, \
    SERVER_BUILDER_CLASSES
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.usage.job import Job
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.efootprint_extensions.edge_usage_pattern_from_form import EdgeUsagePatternFromForm

# Add project root to sys.path manually
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model_builder.class_structure import generate_object_creation_structure, \
    FORM_FIELD_REFERENCES, FORM_TYPE_OBJECT
from model_builder.web_core.model_web import model_builder_root
from model_builder.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ATTRIBUTES_TO_SKIP_IN_FORMS
from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.efootprint_extensions.recurrent_edge_process_from_form import RecurrentEdgeProcessFromForm


obj_creation_structure_dict = {
    "Service": SERVICE_CLASSES, "ServerBase": SERVER_CLASSES + SERVER_BUILDER_CLASSES,
    "Job": [Job] + SERVICE_JOB_CLASSES, "UsagePattern": [UsagePatternFromForm], "UsageJourney": [UsageJourney],
    "UsageJourneyStep": [UsageJourneyStep], "EdgeUsageJourney": [EdgeUsageJourney],
    "RecurrentEdgeProcess": [RecurrentEdgeProcessFromForm], "EdgeComputer": [EdgeComputer],
    "EdgeUsagePattern": [EdgeUsagePatternFromForm]}
root_dir = os.path.dirname(os.path.abspath(__file__))


def assert_json_equal(json1, json2, path=""):
    """
    Recursively asserts that two JSON-like Python structures are equal,
    ignoring dictionary key order and list element order.

    Raises an AssertionError if a mismatch is found.
    """
    if type(json1) != type(json2):
        raise AssertionError(f"Type mismatch at {path or 'root'}: {type(json1).__name__} != {type(json2).__name__}")

    if isinstance(json1, dict):
        keys1 = set(json1.keys())
        keys2 = set(json2.keys())
        if keys1 != keys2:
            raise AssertionError(f"Key mismatch at {path or 'root'}: {keys1} != {keys2}")
        for key in keys1:
            assert_json_equal(json1[key], json2[key], path + f".{key}")
    elif isinstance(json1, list):
        unmatched = list(json2)
        for i, item1 in enumerate(json1):
            for j, item2 in enumerate(unmatched):
                try:
                    assert_json_equal(item1, item2, path + f"[{i}]")
                    unmatched.pop(j)
                    break
                except AssertionError:
                    continue
            else:
                raise AssertionError(f"No match found for list element at {path}[{i}]: {item1}")
        if unmatched:
            raise AssertionError(f"Extra elements in second list at {path}: {unmatched}")
    else:
        if json1 != json2:
            raise AssertionError(f"Value mismatch at {path or 'root'}: {json1} != {json2}")


class TestsClassStructure(TestCase):
    @staticmethod
    def _test_dict_equal_to_ref(dict_to_test, tmp_filepath):
        with open(tmp_filepath, "w") as f:
            json.dump(dict_to_test, f, indent=4)

        with open(tmp_filepath, "r") as tmp_file, open(tmp_filepath.replace("_tmp", ""), "r") as ref_file:
            assert_json_equal(json.load(tmp_file), json.load(ref_file))
            os.remove(tmp_filepath)

    def test_class_creation_structures(self):
        for class_category_name, class_list in obj_creation_structure_dict.items():
            logger.info(f"Testing {class_category_name} creation structure")
            tmp_structure_filepath = os.path.join(
                root_dir, "class_structures", f"{class_category_name}_creation_structure_tmp.json")
            model_web = MagicMock()
            @dataclass
            class MockModelingObjectWeb:
                id: str
                name: str

            option1 = MockModelingObjectWeb(id="efootprint_id1", name="option1")
            option2 = MockModelingObjectWeb(id="efootprint_id2", name="option2")
            model_web.get_efootprint_objects_from_efootprint_type.side_effect = lambda x: [option1, option2]
            structure, dynamic_data = generate_object_creation_structure(
                class_category_name, class_list, attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS, model_web=model_web)
            self._test_dict_equal_to_ref(structure, tmp_structure_filepath)
            tmp_dynamic_data_filepath = os.path.join(
                root_dir, "class_structures", f"{class_category_name}_creation_dynamic_data_tmp.json")
            self._test_dict_equal_to_ref(dynamic_data, tmp_dynamic_data_filepath)

    def test_default_objects(self):
        default_efootprint_networks = [network_archetype() for network_archetype in Network.archetypes()]
        default_efootprint_hardwares = [Device.laptop(), Device.smartphone()]
        efootprint_countries = []
        for attr_value in vars(Countries).values():
            if callable(attr_value):
                efootprint_countries.append(attr_value())

        def create_object_dict_while_normalizing_ids(object_list: list):
            output_dict = {}
            for elt in object_list:
                elt.id = "id-XXXXXX-" + css_escape(elt.name)
                output_dict[elt.id] = elt.to_json()

            return output_dict

        network_archetypes = create_object_dict_while_normalizing_ids(default_efootprint_networks)
        hardware_archetypes = create_object_dict_while_normalizing_ids(default_efootprint_hardwares)
        countries = create_object_dict_while_normalizing_ids(efootprint_countries)

        with open(os.path.join(model_builder_root, "reference_data", "default_networks.json"), "r") as f:
            default_networks = json.load(f)
        with open(os.path.join(model_builder_root, "reference_data", "default_devices.json"), "r") as f:
            default_devices = json.load(f)
        with open(os.path.join(model_builder_root, "reference_data", "default_countries.json"), "r") as f:
            default_countries = json.load(f)

        def remove_ids_from_str(json_str):
            return re.sub(r"\"id-[a-zA-Z0-9]{6}-", "\"id-XXXXXX-", json_str)

        self.assertEqual(
            remove_ids_from_str(json.dumps(network_archetypes)), remove_ids_from_str(json.dumps(default_networks)))
        self.assertEqual(
            remove_ids_from_str(json.dumps(hardware_archetypes)), remove_ids_from_str(json.dumps(default_devices)))
        self.assertEqual(
            remove_ids_from_str(json.dumps(countries)), remove_ids_from_str(json.dumps(default_countries)))

    def test_objects_attributes_have_correspondences(self):
        objects_extra_fields_to_check = ['Server','Service']

        for efootprint_class_str in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.keys():
            if efootprint_class_str in ["ServerBase", "Service", "ExternalApi"]:
                continue
            efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_str]
            init_sig_params = get_init_signature_params(efootprint_obj_class)
            for attr_name in init_sig_params.keys():
                if attr_name == 'self':
                    continue
                assert FORM_FIELD_REFERENCES[attr_name]["label"] is not None

        for object_extra_fields_to_check in objects_extra_fields_to_check:
                assert FORM_TYPE_OBJECT[object_extra_fields_to_check]["label"] is not None


if __name__ == "__main__":
    from copy import deepcopy
    from typing import get_origin

    from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity

    reformatted_form_fields = deepcopy(FORM_FIELD_REFERENCES)
    for efootprint_class in MODELING_OBJECT_CLASSES_DICT.values():
        init_sig_params = get_init_signature_params(efootprint_class)
        for attr_name in init_sig_params.keys():
            annotation = init_sig_params[attr_name].annotation
            if attr_name == "self":
                continue
            if attr_name not in reformatted_form_fields:
                reformatted_form_fields[attr_name] = {
                    "modeling_obj_containers": [efootprint_class.__name__],
                    "label": attr_name.replace("_", " "),
                }
                if not get_origin(annotation) and issubclass(annotation, ExplainableQuantity):
                    reformatted_form_fields[attr_name].update({"is_advanced_parameter": True, "step": 1})
            if efootprint_class.__name__ not in reformatted_form_fields[attr_name]["modeling_obj_containers"]:
                reformatted_form_fields[attr_name]["modeling_obj_containers"].append(efootprint_class.__name__)

    with open(os.path.join(model_builder_root, "form_fields_reference.json"), "w") as f:
        json.dump(reformatted_form_fields, f, indent=4)
