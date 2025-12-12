import json
import os

from efootprint import __version__ as efootprint_version

from model_builder.adapters.views.views import model_builder_main
from tests__old import root_test_dir
from tests__old.model_builder.base_modeling_integration_test_class import TestModelingBase


class TestViews(TestModelingBase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = os.path.join(root_test_dir, "model_builder", "default_system_data.json")

    def test_default_system_data_has_right_efootprint_version(self):
        with open(os.path.join(root_test_dir, "..", "model_builder", "domain", "reference_data", "default_system_data.json"),
                  "r") as file:
            system_data = json.load(file)
            self.assertEqual(system_data["efootprint_version"], efootprint_version)

    def test_conversion_of_system_data_version_9_to_latest_version(self):
        with open(self.system_data_path, "r") as file:
            json_system_data = json.load(file)
        self.assertEqual(json_system_data["efootprint_version"], "9.1.4")
        self.assertEqual(self.system_data["efootprint_version"], efootprint_version)
        model_builder_main_request = self.factory.post('/model_builder/')
        self._add_session_to_request(model_builder_main_request, self.system_data)

        response = model_builder_main(model_builder_main_request)

        self.assertEqual(model_builder_main_request.session["system_data"]["efootprint_version"], efootprint_version)
        self.assertTrue("Device" in model_builder_main_request.session["system_data"].keys())
