from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.all_classes_in_order import CANONICAL_COMPUTATION_ORDER
from efootprint.core.hardware.storage import Storage

from model_builder.domain.efootprint_to_web_mapping import ModelingObjectWeb, EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING


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

    def test_make_sure_that_all_canonical_classes_are_mapped(self):
        excluded_classes = ["Device", "Country", "Network", "System"]
        unmapped_classes = []
        for canonical_class in CANONICAL_COMPUTATION_ORDER:
            if (canonical_class.__name__ not in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
                and canonical_class.__name__ not in excluded_classes):
                unmapped_classes.append(canonical_class.__name__)

        self.assertEqual([], unmapped_classes,
                         f"The following efootprint classes are not mapped to web classes: {unmapped_classes}")
