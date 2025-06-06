import os
from unittest.mock import patch

from efootprint.logger import logger
from django.http import QueryDict

from model_builder.addition.views_addition import add_object
from model_builder.views import model_builder_main, result_chart
from model_builder.model_web import default_networks, default_devices, default_countries
from model_builder.views_deletion import delete_object
from model_builder.edition.views_edition import edit_object, open_edit_object_panel
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsAddition(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")

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
        self.assertNotIn("UsagePatternFromForm", add_request.session["system_data"])
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

    def test_add_usage_journey_step(self):
        post_data = QueryDict(mutable=True)
        post_data.update({
            "csrfmiddlewaretoken": ["ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv"],
            "UsageJourneyStep_name": ["New usage journey step"],
            "efootprint_id_of_parent_to_link_to": ["uuid-Daily-video-usage"],
            "UsageJourneyStep_user_time_spent": ["1"],
            "UsageJourneyStep_user_time_spent_unit": ["min"],
            "UsageJourneyStep_jobs": [""],
        })

        add_request = self.factory.post("/add-object/UsageJourneyStep", data=post_data)
        self._add_session_to_request(add_request, self.system_data)
        nb_uj_steps_before = len(add_request.session["system_data"]["UsageJourneyStep"])
        response = add_object(add_request, "UsageJourneyStep")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(nb_uj_steps_before + 1, len(add_request.session["system_data"]["UsageJourneyStep"]))

    @patch("model_builder.object_creation_and_edition_utils.render_exception_modal")
    def test_add_usage_journey_step_to_usage_journey_unlinked_to_system_in_existing_computed_system(
        self, mock_render_exception_modal):
        self.system_data_path = os.path.join(root_test_dir, "model_builder", "system_with_mirrored_cards.json")
        self.setUp()
        post_data = QueryDict(mutable=True)
        post_data.update({
            "csrfmiddlewaretoken": ["ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv"],
            "UsageJourney_name": ["New usage journey"],
            "UsageJourney_uj_steps": [""]
        })
        add_request = self.factory.post("/add-object/UsageJourney", data=post_data)
        self._add_session_to_request(add_request, self.system_data)
        nb_uj = len(add_request.session["system_data"]["UsageJourney"])
        response = add_object(add_request, "UsageJourney")
        self.assertEqual(nb_uj + 1, len(add_request.session["system_data"]["UsageJourney"]))
        new_uj_id = list(add_request.session["system_data"]["UsageJourney"].keys())[-1]

        # Add a new usage journey step to the newly created usage journey
        post_data = QueryDict(mutable=True)
        post_data.update({
            "csrfmiddlewaretoken": ["ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv"],
            "UsageJourneyStep_name": ["New usage journey step"],
            "efootprint_id_of_parent_to_link_to": [new_uj_id],
            "UsageJourneyStep_user_time_spent": ["1"],
            "UsageJourneyStep_user_time_spent_unit": ["min"],
            "UsageJourneyStep_jobs": [""],
        })
        add_request = self.factory.post("/add-object/UsageJourneyStep", data=post_data)
        self._add_session_to_request(add_request, self.system_data)
        nb_uj_steps_before = len(add_request.session["system_data"]["UsageJourneyStep"])
        response = add_object(add_request, "UsageJourneyStep")
        mock_render_exception_modal.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(nb_uj_steps_before + 1, len(add_request.session["system_data"]["UsageJourneyStep"]))

        self.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")

    def test_delete_uj_step_from_default_uj_then_link_usage_pattern_to_it(self):
        self.system_data_path = os.path.join(root_test_dir, "..", "model_builder", "default_system_data.json")
        self.setUp()
        # delete system data file
        system_data_with_calculated_attributes_path = self.system_data_path.replace(
            ".json", "_with_calculated_attributes.json")
        if os.path.exists(system_data_with_calculated_attributes_path):
            os.remove(system_data_with_calculated_attributes_path)
        uj_step_id = next(iter(self.system_data["UsageJourneyStep"].keys()))
        delete_request = self.factory.post(f"/delete-object/{uj_step_id}")
        self._add_session_to_request(delete_request, self.system_data)
        nb_uj_steps = len(delete_request.session["system_data"]["UsageJourneyStep"])
        self.assertEqual(1, nb_uj_steps)
        logger.info("Deleting usage journey step")
        response = delete_object(delete_request, uj_step_id)
        self.assertNotIn("UsageJourneyStep", delete_request.session["system_data"])
        uj_id = next(iter(delete_request.session["system_data"]["UsageJourney"].keys()))
        logger.info("Linking usage pattern to usage journey without uj step")
        post_data = QueryDict(mutable=True)
        post_data.update({
            "csrfmiddlewaretoken": ["ruwwTrYareoTugkh9MF7b5lhY3DF70xEwgHKAE6gHAYDvYZFDyr1YiXsV5VDJHKv"],
            "UsagePatternFromForm_devices": [list(default_devices().keys())[0]],
            "UsagePatternFromForm_network": [list(default_networks().keys())[0]],
            "UsagePatternFromForm_country": [list(default_countries().keys())[0]],
            "UsagePatternFromForm_usage_journey": [uj_id],
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
        self._add_session_to_request(add_request, self.system_data)

        response = add_object(add_request, "UsagePatternFromForm")
        self.assertEqual(response.status_code, 200)

        result_request = self.factory.get("/model_builder/result-chart/")
        self._add_session_to_request(result_request, add_request.session["system_data"])
        logger.info("Requesting result chart after adding usage pattern to usage journey without uj step")
        os.environ["RAISE_EXCEPTIONS"] = "True"
        with self.assertRaises(ValueError) as context:
            response = result_chart(result_request)
        self.assertIn("No impact could be computed because the modeling is incomplete", str(context.exception))

        self.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")
