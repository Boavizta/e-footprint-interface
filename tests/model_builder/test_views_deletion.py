import os

from efootprint.logger import logger

from model_builder.adapters.views.views_deletion import delete_object
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsDeletion(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "system_with_mirrored_cards.json")

    def test_deletion(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        job_id = "id-e01f58-Video-streaming-job-1"
        logger.info(f"Delete mirrored cards jobs ")
        delete_request = self.factory.get(f'/model_builder/delete_object/{job_id}/')
        self._add_session_to_request(delete_request, system_data=self.system_data)
        self.assertIn("VideoStreamingJob", delete_request.session["system_data"])
        response =  delete_object(delete_request, job_id)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("VideoStreamingJob", delete_request.session["system_data"])

    def test_delete_job_linked_to_service_then_service(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        self.change_system_data(os.path.join(root_test_dir, "model_builder", "job_linked_to_genai_service.json"))
        job_id = next(iter(self.system_data["GenAIJob"]))
        logger.info(f"Delete job linked to GenAI service {job_id}")
        delete_job_request = self.factory.get(f'/model_builder/delete_object/{job_id}/')
        self._add_session_to_request(delete_job_request, system_data=self.system_data)
        response = delete_object(delete_job_request, job_id)
        self.assertEqual(response.status_code, 200)

        logger.info(f"Delete GenAI service")
        service_id = next(iter(self.system_data["GenAIModel"]))
        delete_service_request = self.factory.get(f'/model_builder/delete_object/{service_id}/')
        self._add_session_to_request(delete_service_request, system_data=delete_job_request.session["system_data"])
        response = delete_object(delete_service_request, service_id)
        self.assertEqual(response.status_code, 204)

    def test_delete_edge_computer(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
        from efootprint.core.hardware.edge.edge_storage import EdgeStorage

        edge_computer = EdgeComputer.from_defaults(
            "temporary edge computer for deletion test",
            storage=EdgeStorage.from_defaults("temporary edge storage for deletion test"))

        for component in edge_computer.components:
            component.compute_calculated_attributes()

        edge_computer.compute_calculated_attributes()

        system_data = {
            "System": {"system_id": {"name": "My system", "id": "uuid-system-1",
                                     "usage_patterns": [], "edge_usage_patterns": []}},
            "EdgeComputer": {edge_computer.id: edge_computer.to_json(save_calculated_attributes=True)},
            "EdgeComputerCPUComponent": {
                edge_computer.cpu_component.id: edge_computer.cpu_component.to_json(
                    save_calculated_attributes=True)},
            "EdgeComputerRAMComponent": {
                edge_computer.ram_component.id: edge_computer.ram_component.to_json(
                    save_calculated_attributes=True)},
            "EdgeStorage": {edge_computer.storage.id: edge_computer.storage.to_json(save_calculated_attributes=True)}
        }
        logger.info(f"Delete Edge computer {edge_computer.id}")
        delete_request = self.factory.get(f'/model_builder/delete_object/{edge_computer.id}/')
        self._add_session_to_request(delete_request, system_data=system_data)
        response = delete_object(delete_request, edge_computer.id)
        self.assertNotIn("EdgeComputer", delete_request.session["system_data"])
        self.assertNotIn("EdgeComputerCPUComponent", delete_request.session["system_data"])
        self.assertNotIn("EdgeComputerRAMComponent", delete_request.session["system_data"])
        self.assertNotIn("EdgeStorage", delete_request.session["system_data"])
        self.assertEqual(response.status_code, 204)


    def test_delete_edge_appliance(self):
        os.environ["RAISE_EXCEPTIONS"] = "True"
        from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance

        edge_appliance = EdgeAppliance.from_defaults("temporary edge appliance for deletion test")
        for component in edge_appliance.components:
            component.compute_calculated_attributes()

        edge_appliance.compute_calculated_attributes()

        system_data = {
            "System": {"system_id": {"name": "My system", "id": "uuid-system-1",
                                     "usage_patterns": [], "edge_usage_patterns": []}},
            "EdgeAppliance": {edge_appliance.id: edge_appliance.to_json(save_calculated_attributes=True)},
            "EdgeApplianceComponent": {
                edge_appliance.appliance_component.id: edge_appliance.appliance_component.to_json(
                    save_calculated_attributes=True)},
        }
        logger.info(f"Delete Edge appliance {edge_appliance.id}")
        delete_request = self.factory.get(f'/model_builder/delete_object/{edge_appliance.id}/')
        self._add_session_to_request(delete_request, system_data=system_data)
        response = delete_object(delete_request, edge_appliance.id)
        self.assertNotIn("EdgeAppliance", delete_request.session["system_data"])
        self.assertNotIn("EdgeApplianceComponent", delete_request.session["system_data"])
        self.assertEqual(response.status_code, 204)
