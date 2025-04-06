import os
import re
import json
from dataclasses import dataclass
from unittest import TestCase
import sys
from unittest.mock import MagicMock

from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep

# Add project root to sys.path manually
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from efootprint.core.all_classes_in_order import SERVICE_CLASSES, SERVER_CLASSES, SERVICE_JOB_CLASSES, \
    SERVER_BUILDER_CLASSES
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.usage.job import Job
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from efootprint.logger import logger

from model_builder.class_structure import generate_object_creation_structure, MODELING_OBJECT_CLASSES_DICT
from model_builder.model_web import model_web_root, ATTRIBUTES_TO_SKIP_IN_FORMS
from utils import EFOOTPRINT_COUNTRIES


obj_creation_structure_dict = {
        "Service": SERVICE_CLASSES, "Server": SERVER_CLASSES + SERVER_BUILDER_CLASSES,
        "Job": [Job] + SERVICE_JOB_CLASSES, "UsagePattern": [UsagePatternFromForm], "UsageJourney": [UsageJourney],
        "UsageJourneyStep": [UsageJourneyStep]}
root_dir = os.path.dirname(os.path.abspath(__file__))


class TestsClassStructure(TestCase):
    def _test_dict_equal_to_ref(self, dict_to_test, tmp_filepath):
        with open(tmp_filepath, "w") as f:
            json.dump(dict_to_test, f, indent=4)

        with open(tmp_filepath, "r") as tmp_file, open(tmp_filepath.replace("_tmp", ""), "r") as ref_file:
            # the trailing \n is added because Pycharm adds it when saving reference files
            self.assertEqual(tmp_file.read() + "\n", ref_file.read())
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
                class_list, class_category_name, attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS, model_web=model_web)
            self._test_dict_equal_to_ref(structure, tmp_structure_filepath)
            tmp_dynamic_data_filepath = os.path.join(
                root_dir, "class_structures", f"{class_category_name}_creation_dynamic_data_tmp.json")
            self._test_dict_equal_to_ref(dynamic_data, tmp_dynamic_data_filepath)

    def test_default_objects(self):
        default_efootprint_networks = [network_archetype() for network_archetype in Network.archetypes()]
        default_efootprint_hardwares = [Device.laptop(), Device.smartphone()]

        network_archetypes = {network.id: network.to_json() for network in default_efootprint_networks}
        hardware_archetypes = {hardware.id: hardware.to_json() for hardware in default_efootprint_hardwares}
        countries = {country.id: country.to_json() for country in EFOOTPRINT_COUNTRIES}

        with open(os.path.join(model_web_root, "default_networks.json"), "r") as f:
            default_networks = json.load(f)
        with open(os.path.join(model_web_root, "default_devices.json"), "r") as f:
            default_devices = json.load(f)
        with open(os.path.join(model_web_root, "default_countries.json"), "r") as f:
            default_countries = json.load(f)

        def remove_ids_from_str(json_str):
            return re.sub(r"\"id-[a-zA-Z0-9]{6}-", "\"id-XXXXXX-", json_str)

        self.assertEqual(
            remove_ids_from_str(json.dumps(network_archetypes)), remove_ids_from_str(json.dumps(default_networks)))
        self.assertEqual(
            remove_ids_from_str(json.dumps(hardware_archetypes)), remove_ids_from_str(json.dumps(default_devices)))
        self.assertEqual(
            remove_ids_from_str(json.dumps(countries)), remove_ids_from_str(json.dumps(default_countries)))
