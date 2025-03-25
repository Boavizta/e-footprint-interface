import os
from unittest.mock import patch

from django.http import QueryDict
from efootprint.logger import logger

from model_builder.views import result_chart
from model_builder.views_addition import add_new_usage_pattern, add_new_service, add_new_job
from model_builder.model_web import default_networks, default_devices, default_countries
from model_builder.views_deletion import delete_object
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class IntegrationTest(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join("tests", "model_builder", "default_system_data.json")

    def test_partial_integration(self):
        logger.info(f"Creating usage pattern")
        post_data = QueryDict(mutable=True)
        post_data.update({
            'csrfmiddlewaretoken': ['ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv'],
            'devices': [list(default_devices().keys())[0]],
            'network': [list(default_networks().keys())[0]],
            'country': [list(default_countries().keys())[0]],
            'usage_journey': ['uuid-Daily-video-usage'],
            'start_date': ['2025-02-01'],
            'modeling_duration_value': ["5"],
            "modeling_duration_unit": ["month"],
            "net_growth_rate_in_percentage": ["10"],
            "net_growth_rate_timespan": ["year"],
            "initial_usage_journey_volume": ["1000"],
            "initial_usage_journey_volume_timespan": ["year"],
            'name': ['2New usage pattern'],
        })

        up_request = self.factory.post('/add_new_usage_pattern/', data=post_data)
        self._add_session_to_request(up_request, self.system_data)  # Attach a valid session
        len_system_up = len(up_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"])
        new_up_id = up_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"][-1]

        response = add_new_usage_pattern(up_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(up_request.session["system_data"]["UsagePatternFromForm"]), 1)

        logger.info(f"Creating service")
        post_data = QueryDict(mutable=True)
        post_data.update({'name': ['New service'],
                          'type_object_available': ['WebApplication'],
                          'technology': ['php-symfony'], 'base_ram_consumption': ['2'],
                          'bits_per_pixel': ['0.1'], 'static_delivery_cpu_cost': ['4.0'],
                          'ram_buffer_per_user': ['50']}
        )

        service_request = self.factory.post('/add_new_service/uuid-Server-1', data=post_data)
        self._add_session_to_request(service_request, up_request.session["system_data"])
        response = add_new_service(service_request, 'uuid-Server-1')
        service_id = next(iter(service_request.session["system_data"]["WebApplication"].keys()))
        self.assertEqual(response.status_code, 200)

        logger.info(f"Creating job")
        post_data = QueryDict(mutable=True)
        post_data.update(
        {'name': ['New job'], 'server': ['uuid-Server-1'],
         'service': [service_id],
         'type_object_available': ['WebApplicationJob'],
         'implementation_details': ['aggregation-code-side'],
         'data_transferred': ['150'], 'data_stored': ['100']}
        )

        job_request = self.factory.post('/model_builder/add-new-job/uuid-20-min-streaming-on-Youtube/', data=post_data)
        self._add_session_to_request(job_request, service_request.session["system_data"])
        response = add_new_job(job_request, "uuid-20-min-streaming-on-Youtube")
        self.assertEqual(response.status_code, 200)
        new_job_id = next(iter(job_request.session["system_data"]["WebApplicationJob"].keys()))

        logger.info(f"Manually deleting usage pattern")
        delete_object(job_request, new_up_id)
        logger.info(f"Manually deleting job")
        delete_object(job_request, new_job_id)
        logger.info(f"Manually deleting service")
        delete_object(job_request, service_id)

        self.assertEqual(job_request.session["system_data"], self.system_data)

    @patch("model_builder.views.render_exception_modal")
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
