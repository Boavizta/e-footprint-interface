from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class EdgeComponentWeb(ModelingObjectWeb):
    """Base web wrapper for EdgeComponent and its subclasses."""

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'child_of_parent',
        'available_classes': [EdgeCPUComponent, EdgeRAMComponent, EdgeStorage, EdgeWorkloadComponent],
        'parent_context_key': 'edge_device',
    }

    @property
    def template_name(self):
        return "edge_component"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for component creation forms - link to parent edge device."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
        }

    @classmethod
    def create_side_effects(cls, added_obj, model_web):
        from model_builder.domain.oob_region import CreateSideEffects, OobRegion
        del model_web
        parent_device = added_obj.modeling_obj.modeling_obj_containers[0]
        if parent_device._find_parent_groups():
            return CreateSideEffects(oob_regions=[OobRegion("edge_device_lists")], replaces_primary_render=True)
        return CreateSideEffects()
