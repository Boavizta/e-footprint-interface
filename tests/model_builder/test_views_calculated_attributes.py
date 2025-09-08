import os

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.logger import logger
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.api_utils.json_to_system import json_to_system

from model_builder.efootprint_extensions.explainable_start_date import ExplainableStartDate
from model_builder.web_core.model_web import MODELING_OBJECT_CLASSES_DICT
from model_builder.views import get_explainable_hourly_quantity_chart_and_explanation, \
    get_calculated_attribute_explanation
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsEdition(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(
            root_test_dir, "model_builder", "complete_simple_modeling_with_2_usage_patterns.json")

    def test_get_explainable_hourly_quantity_chart_and_explanation_for_value_in_dict(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        request = self.factory.get(
            "get_explainable_hourly_quantity_chart_and_explanation_from_dict/id-62f62c-Generative-AI-job-1"
            "/hourly_occurrences_per_usage_pattern/id-f6d2c8-Usage-pattern-1")
        self._add_session_to_request(request, self.system_data)
        response = get_explainable_hourly_quantity_chart_and_explanation(
            request, "id-62f62c-Generative-AI-job-1", "hourly_occurrences_per_usage_pattern",
            "id-f6d2c8-Usage-pattern-1")

        self.assertEqual(response.status_code, 200)

    def test_fetch_all_calculated_attributes_endpoints_in_system(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        class_obj_dict, flat_obj_dict = json_to_system(
            self.system_data, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
        for efootprint_object in flat_obj_dict.values():
            container_id = efootprint_object.id
            for calculated_attribute_name in efootprint_object.calculated_attributes:
                calc_attr_value = getattr(efootprint_object, calculated_attribute_name)
                if isinstance(calc_attr_value, ExplainableHourlyQuantities):
                    logger.info(f"Getting chart for {calculated_attribute_name} in {container_id}.")
                    request = self.factory.get(
                        f"get_explainable_hourly_quantity_chart_and_explanation_from_dict/{container_id}"
                        f"/{calculated_attribute_name}")
                    self._add_session_to_request(request, self.system_data)
                    response = get_explainable_hourly_quantity_chart_and_explanation(
                        request, container_id, calculated_attribute_name, None)
                elif (isinstance(calc_attr_value, ExplainableQuantity)
                      or isinstance(calc_attr_value, ExplainableStartDate)):
                    logger.info(f"Getting formula for {calculated_attribute_name} in {container_id}.")
                    request = self.factory.get(
                        f"get_calculated_attribute_explanation/{container_id}/{calculated_attribute_name}")
                    self._add_session_to_request(request, self.system_data)
                    response = get_calculated_attribute_explanation(request, container_id, calculated_attribute_name)
                elif isinstance(calc_attr_value, ExplainableObjectDict):
                    for key, ehq in calc_attr_value.items():
                        logger.info(f"Getting chart for {calculated_attribute_name}, key {key.id} in {container_id}.")
                        request = self.factory.get(
                            f"get_explainable_hourly_quantity_chart_and_explanation_from_dict/{container_id}"
                            f"/{calculated_attribute_name}/{key.id}")
                        self._add_session_to_request(request, self.system_data)
                        response = get_explainable_hourly_quantity_chart_and_explanation(
                            request, container_id, calculated_attribute_name, key.id)
                self.assertEqual(response.status_code, 200)
