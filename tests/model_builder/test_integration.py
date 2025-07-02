import os
from unittest.mock import patch

from django.http import QueryDict
from efootprint.logger import logger

from model_builder.addition.views_addition import add_object
from model_builder.views import result_chart
from model_builder.model_web import default_networks, default_devices, default_countries, ModelWeb
from model_builder.views_deletion import delete_object
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class IntegrationTest(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")

    def test_partial_integration(self):
        logger.info(f"Creating usage pattern")
        post_data = QueryDict(mutable=True)
        post_data.update({
            'csrfmiddlewaretoken': ['ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv'],
            'UsagePatternFromForm_devices': [list(default_devices().keys())[0]],
            'UsagePatternFromForm_network': [list(default_networks().keys())[0]],
            'UsagePatternFromForm_country': [list(default_countries().keys())[0]],
            'UsagePatternFromForm_usage_journey': ['uuid-Daily-video-usage'],
            'UsagePatternFromForm_start_date': ['2025-02-01'],
            'UsagePatternFromForm_modeling_duration_value': ["5"],
            "UsagePatternFromForm_modeling_duration_unit": ["month"],
            "UsagePatternFromForm_net_growth_rate_in_percentage": ["10"],
            "UsagePatternFromForm_net_growth_rate_timespan": ["year"],
            "UsagePatternFromForm_initial_usage_journey_volume": ["1000"],
            "UsagePatternFromForm_initial_usage_journey_volume_timespan": ["year"],
            'UsagePatternFromForm_name': ['2New usage pattern'],
        })

        up_request = self.factory.post('/add-object/UsagePatternFromForm', data=post_data)
        self._add_session_to_request(up_request, self.system_data)  # Attach a valid session
        len_system_up = len(up_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"])
        initial_model_web = ModelWeb(up_request.session)
        initial_total_footprint = initial_model_web.system.total_footprint

        response = add_object(up_request, "UsagePatternFromForm")
        new_up_id = up_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"][-1]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(up_request.session["system_data"]["UsagePatternFromForm"]), 3)

        logger.info(f"Creating service")
        post_data = QueryDict(mutable=True)
        post_data.update({'WebApplication_name': ['New service'],
                          'efootprint_id_of_parent_to_link_to': ['uuid-Server-1'],
                          'type_object_available': ['WebApplication'],
                          'WebApplication_technology': ['php-symfony'], 'WebApplication_base_ram_consumption': ['2'],
                          'WebApplication_bits_per_pixel': ['0.1'], 'WebApplication_static_delivery_cpu_cost': ['4.0'],
                          'WebApplication_ram_buffer_per_user': ['50']}
        )

        service_request = self.factory.post('/add-object/Service', data=post_data)
        self._add_session_to_request(service_request, up_request.session["system_data"])
        response = add_object(service_request, "Service")
        service_id = next(iter(service_request.session["system_data"]["WebApplication"].keys()))
        self.assertEqual(response.status_code, 200)

        logger.info(f"Creating job")
        post_data = QueryDict(mutable=True)
        post_data.update(
        {'WebApplicationJob_name': ['New job'], 'WebApplicationJob_server': ['uuid-Server-1'],
         'efootprint_id_of_parent_to_link_to': ['uuid-20-min-streaming-on-Youtube'],
         'WebApplicationJob_service': [service_id],
         'type_object_available': ['WebApplicationJob'],
         'WebApplicationJob_implementation_details': ['aggregation-code-side'],
         'WebApplicationJob_data_transferred': ['150'], 'WebApplicationJob_data_stored': ['100']}
        )

        job_request = self.factory.post('/model_builder/Job/', data=post_data)
        self._add_session_to_request(job_request, service_request.session["system_data"])
        response = add_object(job_request, "Job")
        self.assertEqual(response.status_code, 200)
        new_job_id = next(iter(job_request.session["system_data"]["WebApplicationJob"].keys()))

        logger.info(f"Manually deleting usage pattern")
        delete_object(job_request, new_up_id)
        self.assertEqual(2, len(job_request.session["system_data"]["UsagePatternFromForm"]))
        logger.info(f"Manually deleting job")
        delete_object(job_request, new_job_id)
        logger.info(f"Manually deleting service")
        delete_object(job_request, service_id)

        self.maxDiff = None
        self.assertEqual(set(job_request.session["system_data"].keys()), set(self.system_data.keys()))
        for efootprint_class in self.system_data:
            if efootprint_class == "efootprint_version":
                continue
            self.assertEqual(
                set(job_request.session["system_data"][efootprint_class].keys()),
                set(self.system_data[efootprint_class].keys()),
                f"Mismatch in {efootprint_class} data")
        self.assertEqual(initial_total_footprint.efootprint_object,
                         ModelWeb(job_request.session).system.total_footprint.efootprint_object)

    @patch("model_builder.object_creation_and_edition_utils.render_exception_modal")
    def test_raise_error_if_users_tries_to_see_results_with_incomplete_modeling(self, mock_exception_modal):
        logger.info("Creating user journey")
        post_data = QueryDict(mutable=True)
        post_data.update({"name": "First user journey", "uj_steps": []})

        result_request = self.factory.post('/result-chart/', data=post_data)
        self._add_session_to_request(result_request, {
            "efootprint_version": "9.1.4",
            "System": {
                "uuid-system-1": {
                    "name": "system 1",
                    "id": "uuid-system-1",
                    "usage_patterns": []
                }
            }
        })

        response = result_chart(result_request)
        mock_exception_modal.assert_called_once()
