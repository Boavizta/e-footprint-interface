import json
import os

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory
from django import setup
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json

from model_builder.model_web import MODELING_OBJECT_CLASSES_DICT

setup()


class TestModelingBase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.system_data_path = None

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.factory = RequestFactory()

        # Load system data
        with open(self.system_data_path, "r") as f:
            system_data_without_calculated_attributes = json.load(f)
        class_obj_dict, flat_obj_dict = json_to_system(
            system_data_without_calculated_attributes, launch_system_computations=True,
            efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
        system = class_obj_dict["System"]["uuid-system-1"]
        system_data_with_calculated_attributes = system_to_json(system, save_calculated_attributes=True)
        # Save system data with calculated attributes
        self.system_data_with_calculated_attributes_path = self.system_data_path.replace(".json", "_with_calculated_attributes.json")
        with open(self.system_data_with_calculated_attributes_path, "w") as f:
            json.dump(system_data_with_calculated_attributes, f, indent=4)
        # include objects that are not linked to the system
        for efootprint_class in class_obj_dict:
            for obj_id in class_obj_dict[efootprint_class]:
                if efootprint_class not in system_data_with_calculated_attributes:
                    system_data_with_calculated_attributes[efootprint_class] = {}
                if obj_id not in system_data_with_calculated_attributes[efootprint_class]:
                    system_data_with_calculated_attributes[efootprint_class][obj_id] = \
                        class_obj_dict[efootprint_class][obj_id].to_json(save_calculated_attributes=True)
        self.system_data = system_data_with_calculated_attributes

    @staticmethod
    def _add_session_to_request(request, system_data):
        """Attach a session to the request object using Django's session middleware."""
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session["system_data"] = system_data
        request.session.save()

    def change_system_data(self, new_system_data_path):
        old_system_data_path = self.system_data_path
        self.system_data_path = new_system_data_path
        self.setUp()
        # delete system data file
        system_data_with_calculated_attributes_path = new_system_data_path.replace(
            ".json", "_with_calculated_attributes.json")
        if os.path.exists(system_data_with_calculated_attributes_path):
            os.remove(system_data_with_calculated_attributes_path)
        self.system_data_path = old_system_data_path
