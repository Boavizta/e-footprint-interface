import os
from unittest.mock import patch

import numpy as np
from django.http import QueryDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.logger import logger

from model_builder.addition.views_addition import add_object
from model_builder.edition.views_edition import edit_object
from model_builder.views import result_chart
from model_builder.web_core.model_web import ModelWeb
from model_builder.views_deletion import delete_object
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class IntegrationTest(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(
            root_test_dir, "..", "model_builder", "reference_data", "default_system_data.json")

    def test_integration(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        logger.info(f"Creating server")
        post_data = self.create_post_data_from_class_default_values(
            "Server", "Server", server_type="autoscaling", fixed_nb_of_instances=None)
        post_data["storage_form_data"] = str(self.create_post_data_from_class_default_values(
            "Storage", "Storage", fixed_nb_of_instances=None)).replace("'", '"')
        server_request = self.create_post_request("/add-object/ServerBase", post_data)
        response = add_object(server_request, "Server")
        server_id = self.get_object_id_from_session(server_request, "Server")
        self.assertEqual(response.status_code, 200)

        logger.info(f"Creating job")
        post_data = self.create_post_data_from_class_default_values(
            "Job", "Job", efootprint_id_of_parent_to_link_to="uid-my-first-usage-journey-step-1",
            server=server_id, data_transferred=SourceValue(10 * u.MB))
        job_request = self.create_post_request(
            "/model_builder/Job/", post_data, system_data=server_request.session["system_data"])
        response = add_object(job_request, "Job")
        self.assertEqual(response.status_code, 200)
        new_job_id = self.get_object_id_from_session(job_request, "Job")

        logger.info(f"Creating usage pattern")
        post_data = self.create_usage_pattern_data(
            "New usage pattern", usage_journey_id="uid-my-first-usage-journey-1")
        up_request = self.create_post_request(
            "/add-object/UsagePattern", post_data, system_data=job_request.session["system_data"])
        initial_model_web = ModelWeb(up_request.session)
        initial_total_footprint = initial_model_web.system.total_footprint
        response = add_object(up_request, "UsagePattern")
        new_up_id = self.get_object_id_from_session(up_request, "UsagePattern")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(up_request.session["system_data"]["UsagePattern"]), 1)

        computed_model_web = ModelWeb(up_request.session)
        logger.info("Updating job data transferred to 20 MB")
        previous_network_energy_footprint = computed_model_web.system.usage_patterns[0].network.energy_footprint.sum()
        logger.info(f"Previous network energy footprint: {previous_network_energy_footprint}")
        job = computed_model_web.get_efootprint_object_from_efootprint_id(new_job_id, "Job")
        edit_data = self.create_edit_object_post_data(job, "data_transferred", SourceValue(20 * u.MB))
        edit_request = self.create_post_request(
            f"/edit-object/{job.id}", edit_data, up_request.session["system_data"])
        response = edit_object(edit_request, job.id)
        self.assertEqual(response.status_code, 200)
        updated_model_web = ModelWeb(edit_request.session)
        updated_network_energy_footprint = updated_model_web.system.usage_patterns[0].network.energy_footprint.sum()
        logger.info(f"Updated network energy footprint: {updated_network_energy_footprint}")
        self.assertGreater(updated_network_energy_footprint, previous_network_energy_footprint,
                           "Network energy footprint did not increase after increasing job data transferred")

        logger.info(f"Creating edge device")
        edge_device_data = self.create_edge_device_data("Test Edge Device")
        edge_device_request = self.create_post_request(
            "/add-object/EdgeComputer", edge_device_data, edit_request.session["system_data"])
        add_object(edge_device_request, "EdgeComputer")
        edge_device_id = self.get_object_id_from_session(edge_device_request, "EdgeComputer")
        print(f"Edge device ID: {edge_device_id}")

        logger.info(f"Creating edge usage journey")
        euj_data = self.create_edge_usage_journey_data(
            name="Test Edge Usage Journey", edge_functions="", usage_span="6")
        euj_request = self.create_post_request(
            "/add-object/EdgeUsageJourney", euj_data, edge_device_request.session["system_data"])
        add_object(euj_request, "EdgeUsageJourney")
        edge_usage_journey_id = self.get_object_id_from_session(euj_request, "EdgeUsageJourney")

        logger.info(f"Creating edge function")
        ef_data = self.create_edge_function_data(
            name="Test Edge Function", parent_id=edge_usage_journey_id, recurrent_edge_device_needs="")
        ef_request = self.create_post_request(
            "/add-object/EdgeFunction", ef_data, euj_request.session["system_data"])
        add_object(ef_request, "EdgeFunction")
        edge_function_id = self.get_object_id_from_session(ef_request, "EdgeFunction")

        logger.info(f"Creating recurrent edge process")
        rep_data = self.create_recurrent_edge_process_data(
            name="Test Process", parent_id=edge_function_id, edge_device_id=edge_device_id)
        rep_request = self.create_post_request(
            "/add-object/RecurrentEdgeProcess", rep_data, ef_request.session["system_data"])
        add_object(rep_request, "RecurrentEdgeProcess")

        logger.info(f"Creating edge usage pattern")
        eup_data = self.create_edge_usage_pattern_data(
            name="Test Edge Usage Pattern", edge_usage_journey_id=edge_usage_journey_id)
        eup_request = self.create_post_request(
            "/add-object/EdgeUsagePattern", eup_data, rep_request.session["system_data"])
        response = add_object(eup_request, "EdgeUsagePattern")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(eup_request.session["system_data"]["EdgeUsagePattern"]), 1)

        computed_model_web = ModelWeb(eup_request.session)
        for footprint_key, footprint_value in computed_model_web.system_emissions["values"].items():
            self.assertGreater(len(footprint_value), 0, f"No footprint values computed for {footprint_key}")
            self.assertGreater(np.max(np.abs(footprint_value)), 0, f"Footprint values are all zero for {footprint_key}")

        logger.info(f"Manually deleting usage pattern")
        delete_object(up_request, new_up_id)
        self.assertIsNone(up_request.session["system_data"].get("UsagePattern", None))
        logger.info(f"Manually deleting job")
        delete_object(up_request, new_job_id)
        logger.info(f"Manually deleting server")
        delete_object(up_request, server_id)

        self.maxDiff = None
        self.assertEqual(set(up_request.session["system_data"].keys()), set(self.system_data.keys()))
        for efootprint_class in self.system_data:
            if efootprint_class == "efootprint_version":
                continue
            self.assertEqual(
                set(up_request.session["system_data"][efootprint_class].keys()),
                set(self.system_data[efootprint_class].keys()),
                f"Mismatch in {efootprint_class} data")
        self.assertEqual(initial_total_footprint.efootprint_object,
                         ModelWeb(up_request.session).system.total_footprint.efootprint_object)

    @patch("model_builder.object_creation_and_edition_utils.render_exception_modal")
    def test_raise_error_if_users_tries_to_see_results_with_incomplete_modeling(self, mock_exception_modal):
        logger.info("Creating user journey")
        post_data = QueryDict(mutable=True)
        post_data.update({"name": "First user journey", "uj_steps": []})

        result_request = self.factory.post("/result-chart/", data=post_data)
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
