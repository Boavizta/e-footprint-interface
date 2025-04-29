import os
from unittest.mock import patch

from efootprint.logger import logger

from model_builder.views_deletion import delete_object
from tests.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViewsDeletion(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join("tests", "model_builder", "system_with_mirrored_cards.json")

    @patch("model_builder.object_creation_and_edition_utils.render_exception_modal")
    def test_deletion(self, mock_render_exception_modal):
        job_id = "id-e01f58-Video-streaming-job-1"
        logger.info(f"Delete mirrored cards jobs ")
        delete_request = self.factory.get(f'/model_builder/delete_object/{job_id}/')
        self._add_session_to_request(delete_request, system_data=self.system_data)
        response =  delete_object(delete_request,  job_id)

        self.assertEqual(response.status_code, 200)
        mock_render_exception_modal.assert_not_called()
