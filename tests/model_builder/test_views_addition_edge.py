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
        """Test basic EdgeUsageJourney creation with EdgeFunction structure"""
        os.environ["RAISE_EXCEPTIONS"] = "True"

        # EdgeUsageJourney in efootprint 12.0.0 now takes edge_functions, not edge_device directly
        # Create empty EdgeUsageJourney first
        euj_data = self.create_edge_usage_journey_data(
            name="Test Edge Usage Journey", usage_span="6", edge_functions="")
        add_request = self.create_post_request("/add-object/EdgeUsageJourney", euj_data)

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
        self.assertEqual(edge_usage_journey_json["usage_span"]["value"], 6)
        self.assertEqual(edge_usage_journey_json["edge_functions"], [])  # Empty list initially

        logger.info("EdgeUsageJourney created successfully")

    def test_add_recurrent_edge_process_via_edge_function(self):
        """Test adding a RecurrentEdgeProcess via EdgeFunction to an EdgeUsageJourney"""
        os.environ["RAISE_EXCEPTIONS"] = "True"

        # Step 1: Create edge usage journey
        euj_data = self.create_edge_usage_journey_data(
            name="Test Edge Usage Journey", edge_functions="", usage_span="6")
        euj_request = self.create_post_request(
            "/add-object/EdgeUsageJourney", euj_data)
        add_object(euj_request, "EdgeUsageJourney")
        edge_usage_journey_id = self.get_object_id_from_session(euj_request, "EdgeUsageJourney")

        # Step 2: Create edge function linked to the edge usage journey
        ef_data = self.create_edge_function_data(
            name="Test Edge Function", parent_id=edge_usage_journey_id, recurrent_edge_device_needs="")
        ef_request = self.create_post_request(
            "/add-object/EdgeFunction", ef_data, euj_request.session["system_data"])
        add_object(ef_request, "EdgeFunction")
        edge_function_id = self.get_object_id_from_session(ef_request, "EdgeFunction")

        # Step 3: Create an edge device
        edge_device_data = self.create_edge_device_data("Test Edge Device")
        edge_device_request = self.create_post_request("/add-object/EdgeComputer", edge_device_data, ef_request.session["system_data"])
        add_object(edge_device_request, "EdgeComputer")
        edge_device_id = self.get_object_id_from_session(edge_device_request, "EdgeComputer")

        # Step 4: Create recurrent edge process linked to the edge function
        rep_data = self.create_recurrent_edge_process_data(
            name="Test Process", parent_id=edge_function_id, edge_device_id=edge_device_id,
            constant_compute_needed="2", constant_ram_needed="1.5", constant_storage_needed="200")
        rep_request = self.create_post_request(
            "/add-object/RecurrentEdgeProcess", rep_data, edge_device_request.session["system_data"])
        add_object(rep_request, "RecurrentEdgeProcess")
        rep_id = self.get_object_id_from_session(rep_request, "RecurrentEdgeProcess")

        # Verify the structure
        recurrent_process = rep_request.session["system_data"]["RecurrentEdgeProcess"][rep_id]
        self.assertEqual(recurrent_process["name"], "Test Process")
        self.assertEqual(recurrent_process["edge_device"], edge_device_id)
        self.assertEqual(recurrent_process["recurrent_compute_needed"]["form_inputs"]["constant_value"], "2")

        edge_function = rep_request.session["system_data"]["EdgeFunction"][edge_function_id]
        self.assertEqual(edge_function["name"], "Test Edge Function")
        self.assertIn(rep_id, edge_function["recurrent_edge_device_needs"])

        edge_usage_journey = rep_request.session["system_data"]["EdgeUsageJourney"][edge_usage_journey_id]
        self.assertEqual(edge_usage_journey["name"], "Test Edge Usage Journey")
        self.assertIn(edge_function_id, edge_usage_journey["edge_functions"])

        logger.info("RecurrentEdgeProcess added via EdgeFunction to EdgeUsageJourney successfully")

    def test_model_web_edge_usage_journeys_property(self):
        """Test that ModelWeb.edge_usage_journeys property works correctly"""
        from model_builder.web_core.model_web import ModelWeb

        # Create edge usage journey
        euj_data = self.create_edge_usage_journey_data(name="Test Edge Usage Journey", edge_functions="")
        euj_request = self.create_post_request("/add-object/EdgeUsageJourney", euj_data)
        add_object(euj_request, "EdgeUsageJourney")

        # Test ModelWeb property
        model_web = ModelWeb(euj_request.session)
        edge_usage_journeys = model_web.edge_usage_journeys

        self.assertEqual(len(edge_usage_journeys), 1)
        self.assertEqual(edge_usage_journeys[0].name, "Test Edge Usage Journey")

        logger.info("ModelWeb.edge_usage_journeys property working correctly")

    def test_edge_usage_journey_with_empty_edge_functions(self):
        """Test EdgeUsageJourney creation with empty edge_functions list"""
        if "RAISE_EXCEPTIONS" in os.environ:
            os.environ.pop("RAISE_EXCEPTIONS")

        # EdgeUsageJourney can now be created with empty edge_functions - this is valid
        euj_data = self.create_edge_usage_journey_data(name="Test Edge Usage Journey", edge_functions="")
        add_request = self.create_post_request("/add-object/EdgeUsageJourney", euj_data)

        response = add_object(add_request, "EdgeUsageJourney")

        # Should succeed - empty edge_functions is valid in efootprint 12.0.0
        self.assert_response_ok(response)
        edge_usage_journey_id = self.get_object_id_from_session(add_request, "EdgeUsageJourney")
        edge_usage_journey = add_request.session["system_data"]["EdgeUsageJourney"][edge_usage_journey_id]
        self.assertEqual(edge_usage_journey["edge_functions"], [])

        logger.info("EdgeUsageJourney creation with empty edge_functions successful")
