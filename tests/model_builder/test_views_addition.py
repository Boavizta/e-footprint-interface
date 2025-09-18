import os
from unittest.mock import patch

from efootprint.logger import logger

from model_builder.addition.views_addition import add_object
from model_builder.views import model_builder_main, result_chart
from model_builder.views_deletion import delete_object
from model_builder.edition.views_edition import edit_object, open_edit_object_panel
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase
from tests.test_constants import TEST_SERVER_ID, TEST_UJ_STEP_ID


class TestViewsAddition(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")

    def test_add_new_usage_pattern_from_form(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"

        up_data = self.create_usage_pattern_data(name="2New usage pattern", usage_journey_id="uuid-Daily-video-usage")
        add_request = self.create_post_request("/add-object/UsagePatternFromForm", up_data)
        len_system_up = len(add_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"])

        response = add_object(add_request, "UsagePatternFromForm")

        self.assert_response_ok(response)
        self.assertEqual(len(add_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"]),
                         len_system_up + 1)
        self.assertEqual(3, len(add_request.session["system_data"]["UsagePatternFromForm"]))
        up_id = self.get_object_id_from_session(add_request, "UsagePatternFromForm")

        # Open edit panel
        logger.info("Open edit usage pattern panel")
        open_edit_panel_request = self.create_get_request(
            f"/model_builder/open-edit-object-panel/{up_id}/", add_request.session["system_data"])
        response = open_edit_object_panel(open_edit_panel_request, up_id)
        self.assert_response_ok(response)

        # Edit usage pattern
        logger.info("Edit usage pattern")
        edit_data = {
            "UsagePatternFromForm_name": "New up name",
            "UsagePatternFromForm_modeling_duration_unit": "year",
            "UsagePatternFromForm_start_date": "2025-02-02"
        }
        edit_request = self.create_post_request(
            f"/model_builder/edit-usage-pattern/{up_id}/", edit_data, open_edit_panel_request.session["system_data"])
        response = edit_object(edit_request, up_id)

        self.assert_response_ok(response)
        self.assertEqual(
            edit_request.session["system_data"]["UsagePatternFromForm"][up_id]["start_date"]["value"][:10],
            "2025-02-02")

        # Reload page
        logger.info("Reloading page")
        results_request = self.create_get_request("/model_builder/", edit_request.session["system_data"])
        response = model_builder_main(results_request)
        self.assert_response_ok(response)

        # Delete usage pattern
        logger.info("Deleting usage pattern")
        delete_request = self.create_post_request(
            f"/model_builder/delete-object/{up_id}/", {}, results_request.session["system_data"])
        response = delete_object(delete_request, up_id)

        self.assert_response_no_content(response)
        self.assertEqual(2, len(delete_request.session["system_data"]["UsagePatternFromForm"]))
        self.assertEqual(
            len(delete_request.session["system_data"]["System"]["uuid-system-1"]["usage_patterns"]), len_system_up)

    def test_add_web_service_then_web_job(self):
        service_data = self.create_web_application_data(name="New service",parent_id=TEST_SERVER_ID)
        add_service_request = self.create_post_request("/add-object/Service", service_data)
        response = add_object(add_service_request, "Service")

        self.assert_response_ok(response)
        service_id = self.get_object_id_from_session(add_service_request, "WebApplication")

        # Create web application job
        job_data = self.create_web_application_job_data(
            name="New job",
            parent_id=TEST_UJ_STEP_ID,
            service_id=service_id,
            server=TEST_SERVER_ID,
            WebApplicationJob_data_transferred=["2.2", "150"],
            WebApplicationJob_data_stored=["100", "100"],
            WebApplicationJob_request_duration="1",
            WebApplicationJob_compute_needed="0.1",
            WebApplicationJob_ram_needed="50"
        )
        add_job_request = self.create_post_request(
            "/model_builder/add-object/Job", job_data, add_service_request.session["system_data"])
        response = add_object(add_job_request, "Job")

        self.assert_response_ok(response)

    def test_add_usage_journey_with_no_uj_step(self):
        uj_data = self.create_usage_journey_data(name="New usage journey")
        from tests.test_constants import MINIMAL_SYSTEM_DATA
        add_request = self.create_post_request("/add-object/UsageJourney", uj_data, MINIMAL_SYSTEM_DATA)

        response = add_object(add_request, "UsageJourney")

        self.assertIn("UsageJourney", add_request.session["system_data"])

    def test_add_usage_journey_step(self):
        ujs_data = self.create_usage_journey_step_data(
            name="New usage journey step", parent_id="uuid-Daily-video-usage")
        add_request = self.create_post_request("/add-object/UsageJourneyStep", ujs_data)
        nb_uj_steps_before = len(add_request.session["system_data"]["UsageJourneyStep"])

        response = add_object(add_request, "UsageJourneyStep")

        self.assert_response_ok(response)
        self.assertEqual(nb_uj_steps_before + 1, len(add_request.session["system_data"]["UsageJourneyStep"]))

    @patch("model_builder.object_creation_and_edition_utils.render_exception_modal")
    def test_add_usage_journey_step_to_usage_journey_unlinked_to_system_in_existing_computed_system(
        self, mock_render_exception_modal):
        self.change_system_data(os.path.join(root_test_dir, "model_builder", "system_with_mirrored_cards.json"))

        # Create usage journey
        uj_data = self.create_usage_journey_data(name="New usage journey")
        add_request = self.create_post_request("/add-object/UsageJourney", uj_data)
        nb_uj = len(add_request.session["system_data"]["UsageJourney"])
        response = add_object(add_request, "UsageJourney")
        self.assertEqual(nb_uj + 1, len(add_request.session["system_data"]["UsageJourney"]))
        new_uj_id = self.get_object_id_from_session(add_request, "UsageJourney")

        # Add usage journey step to the newly created usage journey
        ujs_data = self.create_usage_journey_step_data(name="New usage journey step", parent_id=new_uj_id)
        add_ujs_request = self.create_post_request("/add-object/UsageJourneyStep", ujs_data, self.system_data)
        nb_uj_steps_before = len(add_ujs_request.session["system_data"]["UsageJourneyStep"])
        response = add_object(add_ujs_request, "UsageJourneyStep")

        mock_render_exception_modal.assert_not_called()
        self.assert_response_ok(response)
        self.assertEqual(nb_uj_steps_before + 1, len(add_ujs_request.session["system_data"]["UsageJourneyStep"]))

    def test_delete_uj_step_from_default_uj_then_link_usage_pattern_to_it(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        self.change_system_data(os.path.join(root_test_dir, "..", "model_builder", "default_system_data.json"))

        # Delete usage journey step
        uj_step_id = next(iter(self.system_data["UsageJourneyStep"].keys()))
        delete_request = self.create_post_request(f"/delete-object/{uj_step_id}", {})
        nb_uj_steps = len(delete_request.session["system_data"]["UsageJourneyStep"])
        self.assertEqual(1, nb_uj_steps)

        logger.info("Deleting usage journey step")
        response = delete_object(delete_request, uj_step_id)
        self.assert_response_ok(response)
        self.assertNotIn("UsageJourneyStep", delete_request.session["system_data"])

        # Link usage pattern to usage journey without step
        uj_id = next(iter(delete_request.session["system_data"]["UsageJourney"].keys()))
        logger.info("Linking usage pattern to usage journey without uj step")
        up_data = self.create_usage_pattern_data(name="2New usage pattern", usage_journey_id=uj_id)
        add_request = self.create_post_request("/add-object/UsagePatternFromForm", up_data, self.system_data)
        response = add_object(add_request, "UsagePatternFromForm")
        self.assert_response_ok(response)

        # Test result chart fails with incomplete modeling
        result_request = self.create_get_request("/model_builder/result-chart/", add_request.session["system_data"])
        logger.info("Requesting result chart after adding usage pattern to usage journey without uj step")
        with self.assertRaises(ValueError) as context:
            response = result_chart(result_request)
        self.assertIn("No impact could be computed because the modeling is incomplete", str(context.exception))

    def test_add_server_then_ai_model_then_job(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        self.change_system_data(os.path.join(root_test_dir, "..", "model_builder", "default_system_data.json"))

        # Create GPU server
        logger.info("Adding a new server")
        server_data = self.create_gpu_server_data(name="AI server 1")
        server_add_request = self.create_post_request("/add-object/ServerBase", server_data)
        response = add_object(server_add_request, "ServerBase")
        server_id = self.get_object_id_from_session(server_add_request, "GPUServer")

        # Create GenAI service
        logger.info("Installing genAI service on server")
        genai_service_data = self.create_genai_model_data(name='Generative AI model 1', parent_id=server_id)
        service_add_request = self.create_post_request(
            "/add-object/Service", genai_service_data, server_add_request.session["system_data"])
        response = add_object(service_add_request, "Service")
        gen_ai_model_id = self.get_object_id_from_session(service_add_request, "GenAIModel")

        # Create GenAI job
        logger.info("Adding a new job for the genAI model")
        uj_step_id = next(iter(service_add_request.session["system_data"]["UsageJourneyStep"].keys()))
        genai_job_data = self.create_genai_job_data(
            name='Generative AI job 1', parent_id=uj_step_id, service_id=gen_ai_model_id, server_id=server_id)
        job_request = self.create_post_request(
            "/model_builder/add-object/Job", genai_job_data, service_add_request.session["system_data"])
        response = add_object(job_request, "Job")
        self.assert_response_ok(response)

    def test_add_up_to_default_system_then_delete_it_then_add_server(self):
        self.change_system_data(os.path.join(root_test_dir, "..", "model_builder", "default_system_data.json"))
        uj_id = next(iter(self.system_data["UsageJourney"].keys()))
        os.environ["RAISE_EXCEPTIONS"] = "True"

        # Create usage pattern
        logger.info("Linking usage pattern to usage journey without uj step")
        up_data = self.create_usage_pattern_data(name="New usage pattern", usage_journey_id=uj_id)
        add_request = self.create_post_request("/add-object/UsagePatternFromForm", up_data)
        response = add_object(add_request, "UsagePatternFromForm")
        self.assert_response_ok(response)

        # Delete usage pattern
        logger.info("Delete usage pattern")
        up_id = self.get_object_id_from_session(add_request, "UsagePatternFromForm")
        delete_request = self.create_post_request(f"/model_builder/delete-object/{up_id}/", {}, add_request.session["system_data"])
        response = delete_object(delete_request, up_id)
        self.assert_response_no_content(response)

        # Add server
        logger.info("Add server")
        server_data = self.create_gpu_server_data(name="AI server 1")
        request = self.create_post_request("/add-object/ServerBase", server_data)
        response = add_object(request, "ServerBase")
        self.assert_response_ok(response)

    def test_add_external_api_with_large_model_that_needs_gpu_server_sizing_adaptation(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"

        external_api_data = self.create_external_api_data(
            name="Generative AI model 3", provider="openai", model_name="gpt-4")
        system_data = {
            "efootprint_version": "10.1.14",
            "System": {"uuid-system-1": {"name": "system 1", "id": "uuid-system-1", "usage_patterns": []}}
        }
        add_request = self.create_post_request("/add-object/ExternalApi", external_api_data, system_data)

        response = add_object(add_request, "ExternalApi")

        self.assert_response_ok(response)
