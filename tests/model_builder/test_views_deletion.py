import os
from unittest.mock import patch

from efootprint.logger import logger

from model_builder.views_deletion import delete_object
from tests import root_test_dir
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsDeletion(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "system_with_mirrored_cards.json")

    @patch("model_builder.object_creation_and_edition_utils.render_exception_modal")
    def test_deletion(self, mock_render_exception_modal):
        job_id = "id-e01f58-Video-streaming-job-1"
        logger.info(f"Delete mirrored cards jobs ")
        delete_request = self.factory.get(f'/model_builder/delete_object/{job_id}/')
        self._add_session_to_request(delete_request, system_data=self.system_data)
        self.assertIn("VideoStreamingJob", delete_request.session["system_data"])
        response =  delete_object(delete_request, job_id)

        self.assertEqual(response.status_code, 200)
        mock_render_exception_modal.assert_not_called()
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
