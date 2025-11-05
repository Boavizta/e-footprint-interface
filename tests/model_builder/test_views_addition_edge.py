import os

from efootprint.logger import logger

from model_builder.addition.views_addition import add_object
from model_builder.views_deletion import delete_object
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

    def test_add_edge_device_basic(self):
        """Test basic EdgeDevice creation with component addition and removal"""
        os.environ["RAISE_EXCEPTIONS"] = "True"

        # Step 1: Create EdgeDevice
        edge_device_data = self.create_post_data_from_class_default_values(
            name="Test Edge Device", efootprint_class_name="EdgeDevice")
        add_request = self.create_post_request("/add-object/EdgeDevice", edge_device_data)

        # Check initial state
        self.assertNotIn("EdgeDevice", add_request.session["system_data"])

        response = add_object(add_request, "EdgeDevice")

        # Verify response and data
        self.assert_response_ok(response)
        self.assertIn("EdgeDevice", add_request.session["system_data"])
        self.assertEqual(len(add_request.session["system_data"]["EdgeDevice"]), 1)

        edge_device_id = self.get_object_id_from_session(add_request, "EdgeDevice")
        edge_device_json = add_request.session["system_data"]["EdgeDevice"][edge_device_id]

        self.assertEqual(edge_device_json["name"], "Test Edge Device")
        self.assertEqual(edge_device_json["components"], [])  # Initially empty
        logger.info("EdgeDevice created successfully")

        # Step 2: Add a CPU component to the edge device
        cpu_component_data = self.create_post_data_from_class_default_values(
            name="Test CPU Component", efootprint_class_name="EdgeCPUComponent",
            efootprint_id_of_parent_to_link_to=edge_device_id)
        cpu_add_request = self.create_post_request(
            "/add-object/EdgeCPUComponent", cpu_component_data, add_request.session["system_data"])

        # Check initial component state
        self.assertNotIn("EdgeCPUComponent", cpu_add_request.session["system_data"])

        response = add_object(cpu_add_request, "EdgeCPUComponent")

        # Verify CPU component creation
        self.assert_response_ok(response)
        self.assertIn("EdgeCPUComponent", cpu_add_request.session["system_data"])
        self.assertEqual(len(cpu_add_request.session["system_data"]["EdgeCPUComponent"]), 1)

        cpu_component_id = self.get_object_id_from_session(cpu_add_request, "EdgeCPUComponent")
        cpu_component_json = cpu_add_request.session["system_data"]["EdgeCPUComponent"][cpu_component_id]

        self.assertEqual(cpu_component_json["name"], "Test CPU Component")

        # Verify the component was added to the edge device
        updated_edge_device = cpu_add_request.session["system_data"]["EdgeDevice"][edge_device_id]
        self.assertIn(cpu_component_id, updated_edge_device["components"])
        logger.info("CPU component added to EdgeDevice successfully")

        # Step 3: Remove the CPU component
        delete_request = self.create_post_request(
            f"/model_builder/delete-object/{cpu_component_id}/", {}, cpu_add_request.session["system_data"])
        response = delete_object(delete_request, cpu_component_id)

        # Verify CPU component deletion
        self.assert_response_no_content(response)
        self.assertNotIn("EdgeCPUComponent", delete_request.session["system_data"])

        # Verify the component was removed from the edge device
        final_edge_device = delete_request.session["system_data"]["EdgeDevice"][edge_device_id]
        self.assertEqual(final_edge_device["components"], [])
        logger.info("CPU component removed from EdgeDevice successfully")

    def test_add_recurrent_edge_device_need_with_component_needs(self):
        """Test RecurrentEdgeDeviceNeed creation with RecurrentEdgeComponentNeeds linked to CPU and RAM components"""
        os.environ["RAISE_EXCEPTIONS"] = "True"

        # Step 1: Create EdgeDevice
        edge_device_data = self.create_post_data_from_class_default_values(
            name="Test Edge Device", efootprint_class_name="EdgeDevice")
        edge_device_request = self.create_post_request("/add-object/EdgeDevice", edge_device_data)
        add_object(edge_device_request, "EdgeDevice")
        edge_device_id = self.get_object_id_from_session(edge_device_request, "EdgeDevice")
        logger.info("EdgeDevice created successfully")

        # Step 2: Add a CPU component to the edge device
        cpu_component_data = self.create_post_data_from_class_default_values(
            name="Test CPU Component", efootprint_class_name="EdgeCPUComponent",
            efootprint_id_of_parent_to_link_to=edge_device_id)
        cpu_request = self.create_post_request(
            "/add-object/EdgeCPUComponent", cpu_component_data, edge_device_request.session["system_data"])
        add_object(cpu_request, "EdgeCPUComponent")
        cpu_component_id = self.get_object_id_from_session(cpu_request, "EdgeCPUComponent")
        logger.info("CPU component added to EdgeDevice")

        # Step 3: Add a RAM component to the edge device
        ram_component_data = self.create_post_data_from_class_default_values(
            name="Test RAM Component", efootprint_class_name="EdgeRAMComponent",
            efootprint_id_of_parent_to_link_to=edge_device_id)
        ram_request = self.create_post_request(
            "/add-object/EdgeRAMComponent", ram_component_data, cpu_request.session["system_data"])
        add_object(ram_request, "EdgeRAMComponent")
        ram_component_id = self.get_object_id_from_session(ram_request, "EdgeRAMComponent")
        logger.info("RAM component added to EdgeDevice")

        # Step 4: Create EdgeUsageJourney
        euj_data = self.create_edge_usage_journey_data(
            name="Test Edge Usage Journey", edge_functions="", usage_span="6")
        euj_request = self.create_post_request(
            "/add-object/EdgeUsageJourney", euj_data, ram_request.session["system_data"])
        add_object(euj_request, "EdgeUsageJourney")
        edge_usage_journey_id = self.get_object_id_from_session(euj_request, "EdgeUsageJourney")
        logger.info("EdgeUsageJourney created")

        # Step 5: Create EdgeFunction linked to the edge usage journey
        ef_data = self.create_edge_function_data(
            name="Test Edge Function", parent_id=edge_usage_journey_id, recurrent_edge_device_needs="")
        ef_request = self.create_post_request(
            "/add-object/EdgeFunction", ef_data, euj_request.session["system_data"])
        add_object(ef_request, "EdgeFunction")
        edge_function_id = self.get_object_id_from_session(ef_request, "EdgeFunction")
        logger.info("EdgeFunction created")

        # Step 6: Create RecurrentEdgeDeviceNeed linked to the edge function
        redn_data = {
            "csrfmiddlewaretoken": "test_token",
            "type_object_available": "RecurrentEdgeDeviceNeed",
            "RecurrentEdgeDeviceNeed_name": "Test Recurrent Edge Device Need",
            "edge_device": edge_device_id,
            "efootprint_id_of_parent_to_link_to": edge_function_id
        }
        redn_request = self.create_post_request(
            "/add-object/RecurrentEdgeDeviceNeed", redn_data, ef_request.session["system_data"])
        add_object(redn_request, "RecurrentEdgeDeviceNeed")
        redn_id = self.get_object_id_from_session(redn_request, "RecurrentEdgeDeviceNeed")
        logger.info("RecurrentEdgeDeviceNeed created")

        # Verify RecurrentEdgeDeviceNeed was created correctly
        redn_json = redn_request.session["system_data"]["RecurrentEdgeDeviceNeed"][redn_id]
        self.assertEqual(redn_json["name"], "Test Recurrent Edge Device Need")
        self.assertEqual(redn_json["edge_device"], edge_device_id)
        self.assertEqual(redn_json["recurrent_edge_component_needs"], [])  # Initially empty

        # Step 7: Add RecurrentEdgeComponentNeed for CPU
        cpu_need_data = {
            "csrfmiddlewaretoken": "test_token",
            "type_object_available": "RecurrentEdgeComponentNeed",
            "RecurrentEdgeComponentNeed_name": "CPU Need",
            "RecurrentEdgeComponentNeed_edge_component": cpu_component_id,
            "RecurrentEdgeComponentNeed_recurrent_need__constant_value": "2.0",
            "RecurrentEdgeComponentNeed_recurrent_need__constant_unit": "cpu_core",
            "efootprint_id_of_parent_to_link_to": redn_id
        }
        cpu_need_request = self.create_post_request(
            "/add-object/RecurrentEdgeComponentNeed", cpu_need_data, redn_request.session["system_data"])
        add_object(cpu_need_request, "RecurrentEdgeComponentNeed")
        cpu_need_id = self.get_object_id_from_session(cpu_need_request, "RecurrentEdgeComponentNeed")
        logger.info("RecurrentEdgeComponentNeed for CPU added")

        # Verify CPU component need was created correctly
        cpu_need_json = cpu_need_request.session["system_data"]["RecurrentEdgeComponentNeed"][cpu_need_id]
        self.assertEqual(cpu_need_json["name"], "CPU Need")
        self.assertEqual(cpu_need_json["edge_component"], cpu_component_id)
        self.assertEqual(cpu_need_json["recurrent_need"]["form_inputs"]["constant_value"], "2.0")
        self.assertEqual(cpu_need_json["recurrent_need"]["form_inputs"]["constant_unit"], "cpu_core")

        # Step 8: Add RecurrentEdgeComponentNeed for RAM
        ram_need_data = {
            "csrfmiddlewaretoken": "test_token",
            "type_object_available": "RecurrentEdgeComponentNeed",
            "RecurrentEdgeComponentNeed_name": "RAM Need",
            "RecurrentEdgeComponentNeed_edge_component": ram_component_id,
            "RecurrentEdgeComponentNeed_recurrent_need__constant_value": "4.0",
            "RecurrentEdgeComponentNeed_recurrent_need__constant_unit": "GB_ram",
            "efootprint_id_of_parent_to_link_to": redn_id
        }
        ram_need_request = self.create_post_request(
            "/add-object/RecurrentEdgeComponentNeed", ram_need_data, cpu_need_request.session["system_data"])
        add_object(ram_need_request, "RecurrentEdgeComponentNeed")
        ram_need_id = self.get_object_id_from_name(ram_need_request, "RecurrentEdgeComponentNeed", "RAM Need")
        logger.info("RecurrentEdgeComponentNeed for RAM added")

        # Verify RAM component need was created correctly
        ram_need_json = ram_need_request.session["system_data"]["RecurrentEdgeComponentNeed"][ram_need_id]
        self.assertEqual(ram_need_json["name"], "RAM Need")
        self.assertEqual(ram_need_json["edge_component"], ram_component_id)
        self.assertEqual(ram_need_json["recurrent_need"]["form_inputs"]["constant_value"], "4.0")
        self.assertEqual(ram_need_json["recurrent_need"]["form_inputs"]["constant_unit"], "GB_ram")

        # Verify both component needs are linked to RecurrentEdgeDeviceNeed
        updated_redn = ram_need_request.session["system_data"]["RecurrentEdgeDeviceNeed"][redn_id]
        self.assertEqual(len(updated_redn["recurrent_edge_component_needs"]), 2)
        self.assertIn(cpu_need_id, updated_redn["recurrent_edge_component_needs"])
        self.assertIn(ram_need_id, updated_redn["recurrent_edge_component_needs"])

        logger.info("RecurrentEdgeDeviceNeed with 2 RecurrentEdgeComponentNeeds created successfully")
