from typing import TYPE_CHECKING

from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_storage import EdgeStorage

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.domain.entities.web_core.hardware.hardware_utils import generate_object_with_storage_creation_context

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class EdgeDeviceBaseWeb(ModelingObjectWeb):
    """Base web wrapper for EdgeDevice and its subclasses (EdgeComputer, EdgeAppliance)."""
    add_template = "add_edge_device.html"
    attributes_to_skip_in_forms = ["storage"]
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def template_name(self):
        return "edge_device"

    @property
    def class_title_style(self):
        return "h6"

    @classmethod
    def generate_object_creation_context(
    cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None, object_type: str=None):
        return generate_object_with_storage_creation_context(
            model_web, "EdgeDeviceBase", [EdgeComputer, EdgeAppliance, EdgeDevice],
            "EdgeStorage", [EdgeStorage])
