import json
import os
from contextlib import contextmanager
from copy import deepcopy
from typing import Dict, Any, Optional

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import QueryDict
from django.test import TestCase, RequestFactory
from django import setup
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json

from model_builder.version_upgrade_handlers import upgrade_interface_version_pre_14
from model_builder.domain.entities.web_core.model_web import default_networks, default_devices, default_countries
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from tests__old.test_constants import (
    USAGE_PATTERN_FORM_DATA, WEB_APPLICATION_FORM_DATA, WEB_APPLICATION_JOB_FORM_DATA,
    GPU_SERVER_FORM_DATA, HTTP_OK, HTTP_NO_CONTENT, EDGE_DEVICE_FORM_DATA, EDGE_USAGE_PATTERN_FORM_DATA
)

setup()


class TestModelingBase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = None

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.factory = RequestFactory()

        # Load system data
        with open(self.system_data_path, "r") as f:
            system_data_without_calculated_attributes = json.load(f)
        upgraded_system_data = upgrade_interface_version_pre_14(system_data_without_calculated_attributes)
        class_obj_dict, flat_obj_dict = json_to_system(
            upgraded_system_data, launch_system_computations=True,
            efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
        system = class_obj_dict["System"]["uuid-system-1"]
        system_data_with_calculated_attributes = system_to_json(system, save_calculated_attributes=True)
        # Save system data with calculated attributes
        self.system_data_with_calculated_attributes_path = self.system_data_path.replace(".json", "_with_calculated_attributes.json")
        with open(self.system_data_with_calculated_attributes_path, "w") as f:
            json.dump(system_data_with_calculated_attributes, f, indent=4)
        # include objects that are not linked to the system
        for efootprint_class in class_obj_dict:
            for obj_id in class_obj_dict[efootprint_class]:
                if efootprint_class not in system_data_with_calculated_attributes:
                    system_data_with_calculated_attributes[efootprint_class] = {}
                if obj_id not in system_data_with_calculated_attributes[efootprint_class]:
                    system_data_with_calculated_attributes[efootprint_class][obj_id] = \
                        class_obj_dict[efootprint_class][obj_id].to_json(save_calculated_attributes=True)
        self.system_data = system_data_with_calculated_attributes

    @staticmethod
    def _add_session_to_request(request, system_data):
        """Attach a session to the request object using Django's session middleware."""
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session["system_data"] = system_data
        request.session.save()

    def change_system_data(self, new_system_data_path):
        old_system_data_path = self.system_data_path
        self.system_data_path = new_system_data_path
        self.setUp()
        # delete system data file
        system_data_with_calculated_attributes_path = new_system_data_path.replace(
            ".json", "_with_calculated_attributes.json")
        if os.path.exists(system_data_with_calculated_attributes_path):
            os.remove(system_data_with_calculated_attributes_path)
        self.system_data_path = old_system_data_path

    # Helper methods for common test operations
    def create_post_request(self, url: str, data: Dict[str, Any], system_data: Optional[Dict] = None) -> Any:
        """Create a POST request with session data attached."""
        post_data = QueryDict(mutable=True)
        post_data.update(data)
        request = self.factory.post(url, data=post_data)
        self._add_session_to_request(request, system_data or self.system_data)
        return request

    def create_get_request(self, url: str, system_data: Optional[Dict] = None) -> Any:
        """Create a GET request with session data attached."""
        request = self.factory.get(url)
        self._add_session_to_request(request, system_data or self.system_data)
        return request

    @staticmethod
    def create_post_data_from_class_default_values(
        name: str, efootprint_class_name: str, **overrides) -> Dict[str, Any]:
        """Create form data based on the default values of the specified efootprint class."""
        if efootprint_class_name not in MODELING_OBJECT_CLASSES_DICT:
            raise ValueError(f"Class {efootprint_class_name} not found in MODELING_OBJECT_CLASSES_DICT")

        efootprint_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_name]
        data = {"csrfmiddlewaretoken": "ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv",
                "type_object_available": efootprint_class_name,
                f"{efootprint_class_name}_name": name}

        for attr_name, default_value in efootprint_class.default_values.items():
            if attr_name in overrides:
                continue
            data[f"{efootprint_class_name}_{attr_name}"] = str(default_value.magnitude)
            data[f"{efootprint_class_name}_{attr_name}_unit"] = str(default_value.unit)

        for key, value in overrides.items():
            if value is None:
                continue
            if isinstance(value, ExplainableQuantity):
                data[f"{efootprint_class_name}_{key}"] = str(value.magnitude)
                data[f"{efootprint_class_name}_{key}_unit"] = str(value.unit)
            else:
                data[key] = value

        return data

    @staticmethod
    def create_edit_object_post_data(
        obj_to_edit: ModelingObject, attr_name: str, new_value: ExplainableQuantity) -> Dict[str, Any]:
        """Create form data for editing an object's attribute."""
        efootprint_class_name = obj_to_edit.class_as_simple_str
        output_data = {
            "csrfmiddlewaretoken": "ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv",
            f"{efootprint_class_name}_{attr_name}": str(new_value.magnitude),
            f"{efootprint_class_name}_{attr_name}_unit": str(new_value.unit)
        }
        return output_data


    @staticmethod
    def create_usage_pattern_data(name: str = "Test Usage Pattern",
                                usage_journey_id: str = None, **overrides) -> Dict[str, Any]:
        """Create usage pattern form data with sensible defaults."""
        data = deepcopy(USAGE_PATTERN_FORM_DATA)
        data["UsagePattern_name"] = name

        # Set default device, network, country if available
        if not overrides.get("UsagePattern_devices"):
            devices = list(default_devices().keys())
            if devices:
                data["UsagePattern_devices"] = devices[0]

        if not overrides.get("UsagePattern_network"):
            networks = list(default_networks().keys())
            if networks:
                data["UsagePattern_network"] = networks[0]

        if not overrides.get("UsagePattern_country"):
            countries = list(default_countries().keys())
            if countries:
                data["UsagePattern_country"] = countries[0]

        data["UsagePattern_usage_journey"] = usage_journey_id

        data.update(overrides)
        return data

    @staticmethod
    def create_edge_usage_pattern_data(
        name: str = "Test Edge Usage Pattern", edge_usage_journey_id: str = None, **overrides) -> Dict[str, Any]:
        """Create edge usage pattern form data with sensible defaults."""
        data = deepcopy(EDGE_USAGE_PATTERN_FORM_DATA)
        data["EdgeUsagePattern_name"] = name
        data["EdgeUsagePattern_edge_usage_journey"] = edge_usage_journey_id

        if not overrides.get("EdgeUsagePattern_country"):
            countries = list(default_countries().keys())
            if countries:
                data["EdgeUsagePattern_country"] = countries[0]

        data.update(overrides)
        return data

    @staticmethod
    def create_web_application_data(name: str = "Test Service",
                                   parent_id: Optional[str] = None, **overrides) -> Dict[str, Any]:
        """Create web application form data with sensible defaults."""
        data = deepcopy(WEB_APPLICATION_FORM_DATA)
        data["WebApplication_name"] = name
        if parent_id:
            data["efootprint_id_of_parent_to_link_to"] = parent_id
        data.update(overrides)
        return data

    @staticmethod
    def create_web_application_job_data(name: str = "Test Job",
                                       parent_id: Optional[str] = None,
                                       service_id: Optional[str] = None,
                                       server: Optional[str] = None, **overrides) -> Dict[str, Any]:
        """Create web application job form data with sensible defaults."""
        data = deepcopy(WEB_APPLICATION_JOB_FORM_DATA)
        data["WebApplicationJob_name"] = name
        if parent_id:
            data["efootprint_id_of_parent_to_link_to"] = parent_id
        if service_id:
            data["WebApplicationJob_service"] = service_id
        if server:
            data["WebApplicationJob_server"] = server
        data.update(overrides)
        return data

    @staticmethod
    def create_gpu_server_data(name: str = "Test GPU Server", **overrides) -> Dict[str, Any]:
        """Create GPU server form data with sensible defaults."""
        data = deepcopy(GPU_SERVER_FORM_DATA)
        data["GPUServer_name"] = name
        data.update(overrides)
        return data

    @staticmethod
    def create_edge_device_data(name: str = "Test Edge Device", **overrides) -> Dict[str, Any]:
        """Create edge device form data with sensible defaults."""
        data = deepcopy(EDGE_DEVICE_FORM_DATA)
        data["EdgeComputer_name"] = name
        data.update(overrides)
        return data

    @staticmethod
    def create_usage_journey_data(name: str = "Test Usage Journey",
                                 uj_steps: str = "", **overrides) -> Dict[str, Any]:
        """Create usage journey form data with sensible defaults."""
        data = {
            "csrfmiddlewaretoken": "ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv",
            "UsageJourney_name": name,
            "UsageJourney_uj_steps": uj_steps
        }
        data.update(overrides)
        return data

    @staticmethod
    def create_usage_journey_step_data(name: str = "Test Usage Journey Step",
                                      parent_id: Optional[str] = None,
                                      user_time_spent: str = "1",
                                      user_time_spent_unit: str = "min",
                                      jobs: str = "", **overrides) -> Dict[str, Any]:
        """Create usage journey step form data with sensible defaults."""
        data = {
            "csrfmiddlewaretoken": "ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv",
            "UsageJourneyStep_name": name,
            "UsageJourneyStep_user_time_spent": user_time_spent,
            "UsageJourneyStep_user_time_spent_unit": user_time_spent_unit,
            "UsageJourneyStep_jobs": jobs
        }
        if parent_id:
            data["efootprint_id_of_parent_to_link_to"] = parent_id
        data.update(overrides)
        return data

    @staticmethod
    def create_genai_model_data(name: str = "Test GenAI Model",
                               parent_id: Optional[str] = None,
                               provider: str = "mistralai",
                               model_name: str = "open-mistral-7b",
                               bits_per_token: str = "24",
                               llm_memory_factor: str = "1.2",
                               nb_of_bits_per_parameter: str = "16", **overrides) -> Dict[str, Any]:
        """Create GenAI model form data with sensible defaults."""
        data = {
            "GenAIModel_bits_per_token": bits_per_token,
            "GenAIModel_llm_memory_factor": llm_memory_factor,
            "GenAIModel_model_name": model_name,
            "GenAIModel_name": name,
            "GenAIModel_nb_of_bits_per_parameter": nb_of_bits_per_parameter,
            "GenAIModel_provider": provider,
            "type_object_available": "GenAIModel"
        }
        if parent_id:
            data["efootprint_id_of_parent_to_link_to"] = parent_id
        data.update(overrides)
        return data

    @staticmethod
    def create_genai_job_data(name: str = "Test GenAI Job",
                             parent_id: Optional[str] = None,
                             service_id: Optional[str] = None,
                             server_id: Optional[str] = None,
                             output_token_count: str = "1000", **overrides) -> Dict[str, Any]:
        """Create GenAI job form data with sensible defaults."""
        data = {
            "GenAIJob_name": name,
            "GenAIJob_output_token_count": output_token_count,
            "type_object_available": "GenAIJob"
        }
        if parent_id:
            data["efootprint_id_of_parent_to_link_to"] = parent_id
        if service_id:
            data["service"] = service_id
        if server_id:
            data["server"] = server_id
        data.update(overrides)
        return data

    @staticmethod
    def create_external_api_data(name: str = "Test External API",
                                provider: str = "openai",
                                model_name: str = "gpt-4",
                                bits_per_token: str = "24",
                                llm_memory_factor: str = "1.2",
                                nb_of_bits_per_parameter: str = "16", **overrides) -> Dict[str, Any]:
        """Create external API form data with sensible defaults."""
        data = {
            "type_object_available": "GenAIModel",
            "GenAIModel_name": name,
            "GenAIModel_provider": provider,
            "GenAIModel_model_name": model_name,
            "GenAIModel_nb_of_bits_per_parameter": nb_of_bits_per_parameter,
            "GenAIModel_llm_memory_factor": llm_memory_factor,
            "GenAIModel_bits_per_token": bits_per_token
        }
        data.update(overrides)
        return data

    @staticmethod
    def create_edge_usage_journey_data(name: str = "Test Edge Usage Journey",
                                      usage_span: str = "6",
                                      edge_functions: str = "", **overrides):
        """Create edge usage journey form data with sensible defaults."""
        data = {
            "csrfmiddlewaretoken": "ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv",
            "EdgeUsageJourney_name": name,
            "EdgeUsageJourney_usage_span": usage_span,
            "EdgeUsageJourney_usage_span_unit": "yr",
            "EdgeUsageJourney_edge_functions": edge_functions,
        }
        data.update(overrides)
        return data

    @staticmethod
    def create_edge_function_data(name: str = "Test Edge Function",
                                 parent_id: str = "",
                                 recurrent_edge_device_needs: str = "", **overrides):
        """Create edge function form data with sensible defaults."""
        data = {
            "csrfmiddlewaretoken": "ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv",
            "EdgeFunction_name": name,
            "EdgeFunction_recurrent_edge_device_needs": recurrent_edge_device_needs,
        }
        if parent_id:
            data["efootprint_id_of_parent_to_link_to"] = parent_id
        data.update(overrides)
        return data

    @staticmethod
    def create_recurrent_edge_process_data(name: str = "Test Recurrent Edge Process",
                                          parent_id: str = "",
                                          edge_device_id: str = "",
                                          constant_compute_needed: str = "1",
                                          constant_ram_needed: str = "1",
                                          constant_storage_needed: str = "0", **overrides):
        """Create recurrent edge process form data with sensible defaults."""
        data = {
            "csrfmiddlewaretoken": "ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv",
            "RecurrentEdgeProcess_name": name,
            "RecurrentEdgeProcess_edge_device": edge_device_id,
            "RecurrentEdgeProcess_recurrent_compute_needed__constant_value": constant_compute_needed,
            "RecurrentEdgeProcess_recurrent_compute_needed__constant_unit": "cpu_core",
            "RecurrentEdgeProcess_recurrent_ram_needed__constant_value": constant_ram_needed,
            "RecurrentEdgeProcess_recurrent_ram_needed__constant_unit": "GB_ram",
            "RecurrentEdgeProcess_recurrent_storage_needed__constant_value": constant_storage_needed,
            "RecurrentEdgeProcess_recurrent_storage_needed__constant_unit": "GB",
        }
        if parent_id:
            data["efootprint_id_of_parent_to_link_to"] = parent_id
        data.update(overrides)
        return data

    def assert_response_ok(self, response):
        """Assert that response status is 200 OK."""
        self.assertEqual(response.status_code, HTTP_OK,
                        f"Expected HTTP 200, got {response.status_code}")

    def assert_response_no_content(self, response):
        """Assert that response status is 204 No Content."""
        self.assertEqual(response.status_code, HTTP_NO_CONTENT,
                        f"Expected HTTP 204, got {response.status_code}")

    def get_object_id_from_session(self, request, object_type: str, index: int = -1) -> str:
        """Get an object ID from the session data by type and index."""
        objects = request.session["system_data"].get(object_type, {})
        if not objects:
            raise ValueError(f"No objects of type {object_type} found in session")
        return list(objects.keys())[index]

    def get_object_id_from_name(self, system_data: dict, object_type: str, name) -> str:
        """Get an object ID from the session data by type and index."""
        objects = system_data.get(object_type, {})
        for id, value in objects.items():
            if objects[id]["name"] == name:
                return id
        raise ValueError(f"No objects of type {object_type} with name {name} found in session")

    @contextmanager
    def temp_environ(**env_vars):
        """Context manager for temporarily setting environment variables."""
        original_values = {}
        for key, value in env_vars.items():
            original_values[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            yield
        finally:
            for key, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
