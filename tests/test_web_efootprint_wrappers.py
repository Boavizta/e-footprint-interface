from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.core.hardware.storage import Storage

from model_builder.efootprint_to_web_mapping import ModelingObjectWeb


class StorageWeb(ModelingObjectWeb):
    @property
    def id(self):
        return f"{self._modeling_obj.id}_modeling_obj"


class TestWebEfootprintWrappers(TestCase):
    def test_storage_web_id(self):
        mock_model_web = MagicMock()
        storage = Storage.ssd()
        storage_web = StorageWeb(storage, mock_model_web)

        self.assertEqual(f"{storage.id}_modeling_obj", storage_web.id)
