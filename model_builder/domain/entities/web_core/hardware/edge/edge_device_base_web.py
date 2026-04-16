from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_storage import EdgeStorage

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.domain.entities.web_core.hardware.edge.edge_group_member_mixin import EdgeGroupMemberMixin


class EdgeDeviceBaseWeb(EdgeGroupMemberMixin, ModelingObjectWeb):
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
    def _parent_group_membership_dict(self) -> str:
        return "edge_device_counts"

    def create_side_effects(self):
        from model_builder.domain.oob_region import OobRegion
        side_effects = super().create_side_effects()
        if self.modeling_obj._find_parent_groups():
            side_effects.oob_regions.append(OobRegion("edge_device_lists"))
            side_effects.replaces_primary_render = True
        return side_effects
