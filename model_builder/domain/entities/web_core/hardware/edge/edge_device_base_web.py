from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_storage import EdgeStorage

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class EdgeDeviceBaseWeb(ModelingObjectWeb):
    """Base web wrapper for EdgeDevice and its subclasses (EdgeComputer, EdgeAppliance)."""
    add_template = "add_edge_device.html"
    attributes_to_skip_in_forms = ["storage"]
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'with_storage',
        'available_classes': [EdgeComputer, EdgeAppliance, EdgeDevice],
        'storage_type': 'EdgeStorage',
        'storage_classes': [EdgeStorage],
    }

    @property
    def template_name(self):
        return "edge_device"

    @property
    def class_title_style(self):
        return "h6"
