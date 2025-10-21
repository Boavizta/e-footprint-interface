from typing import TYPE_CHECKING

from efootprint.core.hardware.edge_appliance import EdgeAppliance
from efootprint.core.hardware.edge_computer import EdgeComputer
from efootprint.core.hardware.edge_storage import EdgeStorage

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.hardware.hardware_utils import generate_object_with_storage_creation_context

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeDeviceBaseWeb(ModelingObjectWeb):
    """Base web wrapper for EdgeDeviceBase and its subclasses (EdgeComputer, EdgeAppliance)."""
    add_template = "add_edge_device.html"
    attributes_to_skip_in_forms = ["storage"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def template_name(self):
        return "edge_device"

    @property
    def class_title_style(self):
        return "h6"

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        return generate_object_with_storage_creation_context(
            model_web, "EdgeDeviceBase", [EdgeComputer, EdgeAppliance],
            "EdgeStorage", [EdgeStorage])

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING

        object_creation_type = request.POST.get("type_object_available", object_type)
        child_object_web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[object_creation_type]
        http_response = child_object_web_class.add_new_object_and_return_html_response(
            request, model_web, object_creation_type)

        return http_response
