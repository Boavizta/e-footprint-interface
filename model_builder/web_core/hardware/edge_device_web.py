from typing import TYPE_CHECKING

from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_storage import EdgeStorage

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.hardware.hardware_utils import generate_object_with_storage_creation_context

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeDeviceWeb(ModelingObjectWeb):
    add_template = "add_object_with_storage.html"

    @property
    def class_title_style(self):
        return "h6"

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        return generate_object_with_storage_creation_context(
            model_web, "EdgeDevice", [EdgeDevice],
            "EdgeStorage", [EdgeStorage])
