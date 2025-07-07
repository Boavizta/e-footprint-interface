import os

from model_builder.views import get_explainable_hourly_quantity_chart_and_explanation
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
