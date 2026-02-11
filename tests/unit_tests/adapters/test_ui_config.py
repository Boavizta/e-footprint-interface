import os
import json
from unittest import TestCase

from efootprint.utils.tools import get_init_signature_params
from model_builder.adapters.ui_config import CLASS_UI_CONFIG, FIELD_UI_CONFIG
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING

root_dir = os.path.dirname(os.path.abspath(__file__))


class TestsUIConfig(TestCase):
    def test_objects_attributes_have_correspondences(self):
        objects_extra_fields_to_check = ['Server','Service']

        for efootprint_class_str in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.keys():
            if efootprint_class_str in ["ServerBase", "Service", "ExternalAPI", "EdgeDeviceBase", "JobBase",
                                        "RecurrentEdgeDeviceNeedBase", "EdgeComponent"]:
                continue
            efootprint_obj_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_str]
            init_sig_params = get_init_signature_params(efootprint_obj_class)
            for attr_name in init_sig_params.keys():
                if attr_name == 'self':
                    continue
                assert FIELD_UI_CONFIG[attr_name]["label"] is not None

        for object_extra_fields_to_check in objects_extra_fields_to_check:
                assert CLASS_UI_CONFIG[object_extra_fields_to_check]["label"] is not None


if __name__ == "__main__":
    import os as script_os
    from copy import deepcopy
    from typing import get_origin

    from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity

    # Path to the ui_config and reference_data directories
    ui_config_dir = script_os.path.join(
        script_os.path.dirname(__file__), "..", "..", "..", "model_builder", "adapters", "ui_config")

    def recompute_field_ui_config():
        reformatted_form_fields = deepcopy(FIELD_UI_CONFIG)
        # Reinitialize modeling_obj_containers key for all init sig param
        for efootprint_class in MODELING_OBJECT_CLASSES_DICT.values():
            init_sig_params = get_init_signature_params(efootprint_class)
            for attr_name in init_sig_params.keys():
                if attr_name in reformatted_form_fields:
                    reformatted_form_fields[attr_name]["modeling_obj_containers"] = []

        for efootprint_class in MODELING_OBJECT_CLASSES_DICT.values():
            init_sig_params = get_init_signature_params(efootprint_class)
            for attr_name in init_sig_params.keys():
                annotation = init_sig_params[attr_name].annotation
                if attr_name == "self":
                    continue
                if attr_name not in reformatted_form_fields:
                    reformatted_form_fields[attr_name] = {
                        "modeling_obj_containers": [efootprint_class.__name__],
                        "label": attr_name.replace("_", " "),
                    }
                    if not get_origin(annotation) and issubclass(annotation, ExplainableQuantity):
                        reformatted_form_fields[attr_name].update({"is_advanced_parameter": True, "step": 1})
                if efootprint_class.__name__ not in reformatted_form_fields[attr_name]["modeling_obj_containers"]:
                    reformatted_form_fields[attr_name]["modeling_obj_containers"].append(efootprint_class.__name__)

        with open(script_os.path.join(ui_config_dir, "field_ui_config.json"), "w") as f:
            json.dump(reformatted_form_fields, f, indent=4)

    recompute_field_ui_config()
