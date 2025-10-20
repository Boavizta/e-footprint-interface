import os
from unittest.mock import patch

from efootprint.logger import logger

from model_builder.addition.views_addition import add_object
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsAdditionEdge(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")

    def test_add_edge_usage_journey_basic(self):
        """Test basic EdgeUsageJourney creation"""
        os.environ["RAISE_EXCEPTIONS"] = "True"

        # Create an edge device first to link to
        edge_device_data = self.create_edge_device_data("Test Edge Device")
        edge_device_request = self.create_post_request("/add-object/EdgeComputer", edge_device_data)
        add_object(edge_device_request, "EdgeComputer")
        edge_device_id = self.get_object_id_from_session(edge_device_request, "EdgeComputer")

        # Now create edge usage journey
        euj_data = self.create_edge_usage_journey_data(
            name="Test Edge Usage Journey", edge_device=edge_device_id, usage_span="6")
        add_request = self.create_post_request(
            "/add-object/EdgeUsageJourney", euj_data, edge_device_request.session["system_data"])

        # Check initial state
        self.assertNotIn("EdgeUsageJourney", add_request.session["system_data"])

        response = add_object(add_request, "EdgeUsageJourney")

        # Verify response and data
        self.assert_response_ok(response)
        self.assertIn("EdgeUsageJourney", add_request.session["system_data"])
        self.assertEqual(len(add_request.session["system_data"]["EdgeUsageJourney"]), 1)

        edge_usage_journey_id = self.get_object_id_from_session(add_request, "EdgeUsageJourney")
        edge_usage_journey_json = add_request.session["system_data"]["EdgeUsageJourney"][edge_usage_journey_id]

        self.assertEqual(edge_usage_journey_json["name"], "Test Edge Usage Journey")
        self.assertEqual(edge_usage_journey_json["edge_device"], edge_device_id)
        self.assertEqual(edge_usage_journey_json["usage_span"]["value"], 6)

        logger.info("EdgeUsageJourney created successfully")

    def test_add_recurrent_edge_process_to_edge_usage_journey(self):
        """Test adding a RecurrentEdgeProcessFromForm to an EdgeUsageJourney"""
        os.environ["RAISE_EXCEPTIONS"] = "True"

        # Create an edge device first
        edge_device_data = self.create_edge_device_data("Test Edge Device")
        edge_device_request = self.create_post_request("/add-object/EdgeComputer", edge_device_data)
        add_object(edge_device_request, "EdgeComputer")
        edge_device_id = self.get_object_id_from_session(edge_device_request, "EdgeComputer")

        # Create edge usage journey
        euj_data = self.create_edge_usage_journey_data(name="Test Edge Usage Journey", edge_device=edge_device_id)
        euj_request = self.create_post_request(
            "/add-object/EdgeUsageJourney", euj_data, edge_device_request.session["system_data"])
        add_object(euj_request, "EdgeUsageJourney")
        edge_usage_journey_id = self.get_object_id_from_session(euj_request, "EdgeUsageJourney")

        # Create recurrent edge process and link to edge usage journey
        rep_data = self.create_recurrent_edge_process_data(
            name="Test Process", parent_id=edge_usage_journey_id, constant_compute_needed="2",
            constant_ram_needed="1.5", constant_storage_needed="200")
        rep_request = self.create_post_request(
            "/add-object/RecurrentEdgeProcessFromForm", rep_data, euj_request.session["system_data"])

        # Check initial state
        initial_rep_count = len(rep_request.session["system_data"].get("RecurrentEdgeProcessFromForm", {}))

        response = add_object(rep_request, "RecurrentEdgeProcessFromForm")

        # Verify response and data
        self.assert_response_ok(response)
        self.assertIn("RecurrentEdgeProcessFromForm", rep_request.session["system_data"])
        self.assertEqual(len(rep_request.session["system_data"]["RecurrentEdgeProcessFromForm"]), initial_rep_count + 1)

        # Get the process ID and verify it's linked to the edge usage journey
        rep_id = self.get_object_id_from_session(rep_request, "RecurrentEdgeProcessFromForm")
        recurrent_process = rep_request.session["system_data"]["RecurrentEdgeProcessFromForm"][rep_id]

        self.assertEqual(recurrent_process["name"], "Test Process")
        self.assertEqual(recurrent_process["constant_compute_needed"]["value"], 2.0)
        self.assertEqual(recurrent_process["constant_ram_needed"]["value"], 1.5)
        self.assertEqual(recurrent_process["constant_storage_needed"]["value"], 200.0)

        # Verify the edge usage journey contains the process
        updated_edge_usage_journey = rep_request.session["system_data"]["EdgeUsageJourney"][edge_usage_journey_id]
        self.assertIn(rep_id, updated_edge_usage_journey["edge_processes"])

        logger.info("RecurrentEdgeProcessFromForm added to EdgeUsageJourney successfully")

    def test_model_web_edge_usage_journeys_property(self):
        """Test that ModelWeb.edge_usage_journeys property works correctly"""
        from model_builder.web_core.model_web import ModelWeb

        edge_device_data = self.create_edge_device_data("Test Edge Device")
        edge_device_request = self.create_post_request("/add-object/EdgeComputer", edge_device_data)
        add_object(edge_device_request, "EdgeComputer")
        edge_device_id = self.get_object_id_from_session(edge_device_request, "EdgeComputer")

        # Create edge usage journey
        euj_data = self.create_edge_usage_journey_data(name="Test Edge Usage Journey", edge_device=edge_device_id)
        euj_request = self.create_post_request(
            "/add-object/EdgeUsageJourney", euj_data, edge_device_request.session["system_data"])
        add_object(euj_request, "EdgeUsageJourney")

        # Test ModelWeb property
        model_web = ModelWeb(euj_request.session)
        edge_usage_journeys = model_web.edge_usage_journeys

        self.assertEqual(len(edge_usage_journeys), 1)
        self.assertEqual(edge_usage_journeys[0].name, "Test Edge Usage Journey")

        logger.info("ModelWeb.edge_usage_journeys property working correctly")

    def test_edge_usage_journey_without_edge_device(self):
        """Test EdgeUsageJourney creation fails gracefully without edge device"""
        if "RAISE_EXCEPTIONS" in os.environ:
            os.environ.pop("RAISE_EXCEPTIONS")

        euj_data = self.create_edge_usage_journey_data(name="Test Edge Usage Journey", edge_device="")
        add_request = self.create_post_request("/add-object/EdgeUsageJourney", euj_data)

        # This should handle the case where no edge device is selected
        with patch('model_builder.object_creation_and_edition_utils.render_exception_modal') as mock_error:
            response = add_object(add_request, "EdgeUsageJourney")
            mock_error.assert_called_once()

        logger.info("EdgeUsageJourney creation handled gracefully without edge device")
