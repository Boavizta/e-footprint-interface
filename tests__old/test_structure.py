import os
import json
from dataclasses import dataclass
from unittest import TestCase
import sys
from unittest.mock import MagicMock
from copy import deepcopy

from efootprint.constants.countries import Countries
from efootprint.all_classes_in_order import SERVICE_CLASSES
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params

from model_builder.adapters.forms.form_context_builder import FormContextBuilder
from model_builder.adapters.views.views_addition import _should_use_form_context_builder
from model_builder.domain.entities.web_builders.services.external_api_web import ExternalApiWeb
from model_builder.domain.entities.web_builders.services.service_web import ServiceWeb
from model_builder.domain.entities.web_core.hardware.edge.edge_component_base_web import EdgeComponentWeb
from model_builder.domain.entities.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb
from model_builder.domain.entities.web_core.hardware.server_web import ServerWeb
from model_builder.domain.entities.web_core.usage.edge.edge_function_web import EdgeFunctionWeb
from model_builder.domain.entities.web_core.usage.edge.edge_usage_pattern_web import EdgeUsagePatternWeb
from model_builder.domain.entities.web_core.usage.edge.recurrent_edge_component_need_web import RecurrentEdgeComponentNeedWeb
from model_builder.domain.entities.web_core.usage.edge.recurrent_edge_device_need_base_web import RecurrentEdgeDeviceNeedBaseWeb
from model_builder.domain.entities.web_core.usage.job_web import JobWeb
from model_builder.domain.entities.web_core.usage.journey_base_web import JourneyBaseWeb
from model_builder.domain.entities.web_core.usage.journey_step_base_web import JourneyStepBaseWeb
from model_builder.domain.entities.web_core.usage.usage_pattern_web import UsagePatternWeb

# Add project root to sys.path manually
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model_builder.adapters.forms.class_structure import FORM_FIELD_REFERENCES, FORM_TYPE_OBJECT
from model_builder.domain.entities.web_core.model_web import model_builder_root
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING

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

    def test_class_creation_structures_from_context(self):
        web_classes = [
            UsagePatternWeb, EdgeUsagePatternWeb,
            JourneyBaseWeb,
            JourneyStepBaseWeb, EdgeFunctionWeb,
            JobWeb, RecurrentEdgeDeviceNeedBaseWeb, RecurrentEdgeComponentNeedWeb,
            EdgeDeviceBaseWeb, EdgeComponentWeb, ServerWeb,
            ExternalApiWeb, ServiceWeb
        ]
        object_type_dict = {
            UsagePatternWeb: "UsagePattern", EdgeUsagePatternWeb: "EdgeUsagePattern", JourneyBaseWeb: "UsageJourney",
            JourneyStepBaseWeb: "UsageJourneyStep", EdgeFunctionWeb: "EdgeFunction", JobWeb: "JobBase",
            RecurrentEdgeDeviceNeedBaseWeb: "RecurrentEdgeDeviceNeedBase",
            RecurrentEdgeComponentNeedWeb: "RecurrentEdgeComponentNeedBase", EdgeDeviceBaseWeb: "EdgeDeviceBase",
            EdgeComponentWeb: "EdgeComponent", ServerWeb: "ServerBase", ExternalApiWeb: "ExternalApi",
            ServiceWeb: "Service"}
        basic_model_web = MagicMock()
        mock_obj = MagicMock()
        mock_obj.name = "option1"
        mock_obj.id = "efootprint_id1"
        mock_obj_2 = MagicMock()
        mock_obj_2.name = "option2"
        mock_obj_2.id = "efootprint_id2"
        basic_model_web.get_efootprint_objects_from_efootprint_type.return_value = [mock_obj, mock_obj_2]

        service_model_web = deepcopy(basic_model_web)
        service_mock_server = MagicMock()
        service_mock_server.installable_services.return_value = SERVICE_CLASSES
        service_model_web.get_web_object_from_efootprint_id.return_value = service_mock_server

        job_model_web = deepcopy(basic_model_web)
        job_mock_server = MagicMock()
        job_mock_server.name = "server"
        job_mock_server.efootprint_id = "server_efootprint_id"
        service_mock = MagicMock()
        service_mock.name = "service"
        service_mock.efootprint_id = "service_efootprint_id"
        job_mock_server.installed_services = [service_mock]
        job_model_web.servers = [job_mock_server]
        job_model_web.response_objs = {service.__name__: service for service in SERVICE_CLASSES}

        usage_pattern_model_web = deepcopy(basic_model_web)
        mock_journey = MagicMock()
        mock_journey.name = "mock_journey"
        mock_journey.id = "mock_journey_efootprint_id"
        usage_pattern_model_web.usage_journeys = [mock_journey]
        usage_pattern_model_web.edge_usage_journeys = [mock_journey]

        recurrent_edge_device_need_model_web = deepcopy(basic_model_web)
        mock_edge_device = MagicMock()
        mock_edge_device.configure_mock(
            name="mock_edge_device", efootprint_id="mock_edge_device_efootprint_id", class_as_simple_str="EdgeComputer")
        mock_edge_device2 = MagicMock()
        mock_edge_device2.configure_mock(
            name="mock_edge_device2", efootprint_id="mock_edge_device2_efootprint_id",
            class_as_simple_str="EdgeAppliance")
        mock_edge_device3 = MagicMock()
        mock_edge_device3.configure_mock(
            name="mock_edge_device3", efootprint_id="mock_edge_device3_efootprint_id", class_as_simple_str="EdgeDevice")
        recurrent_edge_device_need_model_web.edge_devices = [mock_edge_device, mock_edge_device2, mock_edge_device3]

        recurrent_edge_component_need_model_web = deepcopy(basic_model_web)
        mock_edge_component = MagicMock()
        mock_edge_component.configure_mock(
            name="mock_edge_component", efootprint_id="mock_edge_component_efootprint_id")
        mock_edge_component.get_efootprint_value.return_value = [u.cpu_core]
        mock_recurrent_edge_device_need = MagicMock()
        mock_edge_device = MagicMock()
        mock_edge_device.configure_mock(
            name="mock_edge_device", efootprint_id="mock_edge_device_efootprint_id")
        mock_recurrent_edge_device_need.edge_device = mock_edge_device
        mock_edge_device.components = [mock_edge_component]
        recurrent_edge_component_need_model_web.get_web_object_from_efootprint_id.return_value = (
            mock_recurrent_edge_device_need)

        model_web_dict = {
            ServiceWeb: service_model_web, JobWeb: job_model_web, UsagePatternWeb: usage_pattern_model_web,
            EdgeUsagePatternWeb: usage_pattern_model_web,
            RecurrentEdgeDeviceNeedBaseWeb: recurrent_edge_device_need_model_web,
            RecurrentEdgeComponentNeedWeb: recurrent_edge_component_need_model_web,}

        for web_class in web_classes:
            web_class_name = web_class.__name__
            logger.info(f"Testing {web_class_name} creation structure")
            tmp_structure_filepath = os.path.join(
                root_dir, "class_structures", f"{web_class_name}_creation_structure_tmp.json")
            model_web = MagicMock()
            @dataclass
            class MockModelingObjectWeb:
                id: str
                name: str

            option1 = MockModelingObjectWeb(id="efootprint_id1", name="option1")
            option2 = MockModelingObjectWeb(id="efootprint_id2", name="option2")
            model_web.get_efootprint_objects_from_efootprint_type.side_effect = lambda x: [option1, option2]
            model_web.servers = ["mock_server"]

            if web_class in model_web_dict:
                model_web = model_web_dict[web_class]
            else:
                model_web = basic_model_web

            if _should_use_form_context_builder(web_class):
                form_builder = FormContextBuilder(model_web)
                creation_context = form_builder.build_creation_context(
                    web_class, object_type=object_type_dict.get(web_class, None),
                    efootprint_id_of_parent_to_link_to=None)
            else:
                # Fall back to custom implementation for complex cases (to be migrated later)
                creation_context = web_class.generate_object_creation_context(
                    model_web, efootprint_id_of_parent_to_link_to=None,
                    object_type=object_type_dict[web_class])

            form_sections = creation_context["form_sections"]
            dynamic_data = creation_context.get("dynamic_form_data", None)
            self._test_dict_equal_to_ref(form_sections, tmp_structure_filepath)
            if dynamic_data is not None:
                tmp_dynamic_data_filepath = os.path.join(
                    root_dir, "class_structures", f"{web_class_name}_creation_dynamic_data_tmp.json")
                self._test_dict_equal_to_ref(dynamic_data, tmp_dynamic_data_filepath)

    def test_default_objects(self):
        default_efootprint_networks = [network_archetype() for network_archetype in Network.archetypes()]
        default_efootprint_hardwares = [Device.laptop(), Device.smartphone()]
        efootprint_countries = []
        for attr_value in vars(Countries).values():
            if callable(attr_value):
                efootprint_countries.append(attr_value())

        def create_object_dict(object_list: list):
            output_dict = {}
            for elt in object_list:
                output_dict[elt.id] = elt.to_json()

            return output_dict

        network_archetypes = create_object_dict(default_efootprint_networks)
        hardware_archetypes = create_object_dict(default_efootprint_hardwares)
        countries = create_object_dict(efootprint_countries)

        with open(os.path.join(model_builder_root, "reference_data", "default_networks.json"), "r") as f:
            default_networks = json.load(f)
        with open(os.path.join(model_builder_root, "reference_data", "default_devices.json"), "r") as f:
            default_devices = json.load(f)
        with open(os.path.join(model_builder_root, "reference_data", "default_countries.json"), "r") as f:
            default_countries = json.load(f)

        def check_dict_equality_ignoring_ids(dict1, dict2):
            for subdict1, subdict2 in zip(list(dict1.values()), list(dict2.values())):
                subdict1.pop("id", None)
                subdict2.pop("id", None)
                self.assertDictEqual(subdict1, subdict2)

        check_dict_equality_ignoring_ids(network_archetypes, default_networks)
        check_dict_equality_ignoring_ids(hardware_archetypes, default_devices)
        check_dict_equality_ignoring_ids(countries, default_countries)

    def test_objects_attributes_have_correspondences(self):
        objects_extra_fields_to_check = ['Server','Service']

        for efootprint_class_str in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.keys():
            if efootprint_class_str in ["ServerBase", "Service", "ExternalApi", "EdgeDeviceBase", "JobBase",
                                        "RecurrentEdgeDeviceNeedBase", "EdgeComponent"]:
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

    def recompute_form_field_references():
        reformatted_form_fields = deepcopy(FORM_FIELD_REFERENCES)
        # Reinitialize modeling_obj_containers key for all init sig param
        for efootprint_class in MODELING_OBJECT_CLASSES_DICT.values():
            init_sig_params = get_init_signature_params(efootprint_class)
            for attr_name in init_sig_params.keys():
                if attr_name in reformatted_form_fields:
                    reformatted_form_fields[attr_name]["modeling_obj_containers"] = []

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

        with open(os.path.join(model_builder_root, "reference_data", "form_fields_reference.json"), "w") as f:
            json.dump(reformatted_form_fields, f, indent=4)

    def recompute_default_countries():
        efootprint_countries = []
        for attr_value in vars(Countries).values():
            if callable(attr_value):
                efootprint_countries.append(attr_value())

        json_dump = {}
        for elt in efootprint_countries:
            json_dump[elt.id] = elt.to_json()

        with open(os.path.join(model_builder_root, "reference_data", "default_countries.json"), "w") as f:
            json.dump(json_dump, f, indent=4)

    # recompute_form_field_references()
    recompute_default_countries()
