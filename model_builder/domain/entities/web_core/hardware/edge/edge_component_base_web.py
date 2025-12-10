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
        'object_type': 'EdgeComponent',
        'available_classes': [EdgeCPUComponent, EdgeRAMComponent, EdgeStorage, EdgeWorkloadComponent],
        'parent_context_key': 'edge_device',
    }

    @property
    def template_name(self):
        return "edge_component"

    @property
    def class_title_style(self):
        return "h8"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for component creation forms - link to parent edge device."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
        }
