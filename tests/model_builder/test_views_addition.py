import os

from efootprint.logger import logger
from django.http import QueryDict

from model_builder.addition.views_addition import add_object
from model_builder.views import model_builder_main
from model_builder.model_web import default_networks, default_devices, default_countries
from model_builder.views_deletion import delete_object
from model_builder.edition.views_edition import edit_object, open_edit_object_panel
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsAddition(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join("tests", "model_builder", "default_system_data.json")

    def test_add_new_usage_pattern_from_form(self):
        post_data = QueryDict(mutable=True)
        post_data.update({
            "csrfmiddlewaretoken": ["ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv"],
            "UsagePatternFromForm_devices": [list(default_devices().keys())[0]],
            "UsagePatternFromForm_network": [list(default_networks().keys())[0]],
            "UsagePatternFromForm_country": [list(default_countries().keys())[0]],
            "UsagePatternFromForm_usage_journey": ["uuid-Daily-video-usage"],
            "UsagePatternFromForm_start_date": ["2025-02-01"],
            "UsagePatternFromForm_modeling_duration_value": ["5"],
            "UsagePatternFromForm_modeling_duration_unit": ["month"],
            "UsagePatternFromForm_net_growth_rate_in_percentage": ["10"],
            "UsagePatternFromForm_net_growth_rate_timespan": ["year"],
            "UsagePatternFromForm_initial_usage_journey_volume": ["1000"],
            "UsagePatternFromForm_initial_usage_journey_volume_timespan": ["year"],
            "UsagePatternFromForm_name": ["2New usage pattern"],
        })
        add_request = self.factory.post("/add-object/UsagePatternFromForm", data=post_data)
        self._add_session_to_request(add_request, self.system_data)  # Attach a valid session
        len_system_up = len(add_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"])

        response = add_object(add_request, "UsagePatternFromForm")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(add_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"]),
                         len_system_up + 1)
        self.assertEqual(len(add_request.session["system_data"]["UsagePatternFromForm"]),1)
        up_id = list(add_request.session["system_data"]["UsagePatternFromForm"].keys())[-1]

        logger.info("Open edit usage pattern panel")
        open_edit_panel_request = self.factory.get(f"/model_builder/open-edit-object-panel/{up_id}/")
        self._add_session_to_request(open_edit_panel_request, add_request.session["system_data"])
        response = open_edit_object_panel(open_edit_panel_request, up_id)
        self.assertEqual(response.status_code, 200)

        logger.info("Edit usage pattern")
        post_data = QueryDict(mutable=True)
        post_data.update({"UsagePatternFromForm_name": ["New up name"],
                          "UsagePatternFromForm_network": [list(default_networks().keys())[1]],
                          "UsagePatternFromForm_modeling_duration_unit": ["year"],
                          "UsagePatternFromForm_start_date": ["2025-02-02"]})
        edit_request = self.factory.post(f"/model_builder/edit-usage-pattern/{up_id}/", data=post_data)
        self._add_session_to_request(edit_request, add_request.session["system_data"])

        response = edit_object(edit_request, up_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            add_request.session["system_data"]["UsagePatternFromForm"][up_id]["start_date"]["value"][:10], "2025-02-02")

        logger.info("Reloading page")
        results_request = self.factory.get("/model_builder/")
        self._add_session_to_request(results_request, add_request.session["system_data"])

        response = model_builder_main(results_request)
        self.assertEqual(response.status_code, 200)

        logger.info("Deleting usage pattern")
        delete_request = self.factory.post(f"/model_builder/delete-object/{up_id}/")
        self._add_session_to_request(delete_request, add_request.session["system_data"])

        response = delete_object(delete_request, up_id)

        self.assertEqual(response.status_code, 204)
        self.assertNotIn(up_id, add_request.session["system_data"]["UsagePatternFromForm"])
        self.assertEqual(
            len(delete_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"]), len_system_up)

    def test_add_web_service_then_web_job(self):
        post_data = QueryDict(mutable=True)
        post_data.update({"WebApplication_name": ["New service"],
                            "efootprint_id_of_parent_to_link_to": ["uuid-Server-1"],
                          "type_object_available": ["WebApplication"],
                          "WebApplication_technology": ["php-symfony"], "WebApplication_base_ram_consumption": ["2"],
                          "WebApplication_bits_per_pixel": ["0.1"], "WebApplication_static_delivery_cpu_cost": ["4.0"],
                          "WebApplication_ram_buffer_per_user": ["50"]}
        )

        request = self.factory.post("/add-object/Service", data=post_data)
        self._add_session_to_request(request, self.system_data)

        response = add_object(request, "Service")
        service_id = next(iter(request.session["system_data"]["WebApplication"].keys()))
        self.assertEqual(response.status_code, 200)

        post_data = QueryDict(mutable=True)
        post_data.update(
        {"WebApplicationJob_name": ["New job"], "server": ["uuid-Server-1"],
         "efootprint_id_of_parent_to_link_to": ["uuid-20-min-streaming-on-Youtube"],
         "WebApplicationJob_service": [service_id],
         "type_object_available": ["WebApplicationJob"],
         "WebApplicationJob_implementation_details": ["aggregation-code-side"],
         "WebApplicationJob_data_transferred": ["2.2", "150"], "WebApplicationJob_data_stored": ["100", "100"],
         "WebApplicationJob_request_duration": ["1"], "WebApplicationJob_compute_needed": ["0.1"],
         "WebApplicationJob_ram_needed": ["50"]}
        )

        request = self.factory.post("/model_builder/add-object/Job", data=post_data)
        self._add_session_to_request(request, self.system_data)

        response = add_object(request, "Job")
        self.assertEqual(response.status_code, 200)


    def test_add_usage_journey_with_no_uj_step(self):
        post_data = QueryDict(mutable=True)
        post_data.update({
            "csrfmiddlewaretoken": ["ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv"],
            "UsageJourney_name": ["New usage journey"],
            "UsageJourney_uj_steps": [""]
        })
        add_request = self.factory.post("/add-object/UsageJourney", data=post_data)
        system_data = {
            "efootprint_version": "9.1.4",
            "System": {
                "uuid-system-1": {
                    "name": "system 1",
                    "id": "uuid-system-1",
                    "usage_patterns": []
                }
            }
        }
        self._add_session_to_request(add_request, system_data)

        response = add_object(add_request, "UsageJourney")

        self.assertTrue("UsageJourney" in add_request.session["system_data"].keys())
