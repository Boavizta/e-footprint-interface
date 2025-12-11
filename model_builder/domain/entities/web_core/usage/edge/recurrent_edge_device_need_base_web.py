from typing import TYPE_CHECKING

from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed

from model_builder.domain.entities.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class RecurrentEdgeDeviceNeedBaseWeb(ResourceNeedBaseWeb):
    """Web wrapper for RecurrentEdgeDeviceNeed and its subclasses (RecurrentEdgeProcess, RecurrentEdgeWorkload)."""
    attributes_to_skip_in_forms = ["edge_device"]

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    # Type depends directly on parent's class (no intermediate selection)
    form_creation_config = {
        'strategy': 'parent_selection',
        'parent_attribute': 'edge_device',
        # Maps parent class name → compatible child classes
        'type_classes_by_parent_class': {
            'EdgeComputer': [RecurrentEdgeProcess],
            'EdgeAppliance': [RecurrentEdgeWorkload],
            'EdgeDevice': [RecurrentEdgeDeviceNeed],
        },
    }

    @classmethod
    def get_creation_prerequisites(cls, model_web: "ModelWeb") -> dict:
        """Return raw domain data needed for form building.

        The adapter will transform this into form structures.
        No form field dictionaries here - just domain objects and relationships.
        """
        edge_devices = model_web.edge_devices
        if not edge_devices:
            raise ValueError("Please create an edge device before adding a recurrent edge resource need")

        available_classes = [RecurrentEdgeProcess, RecurrentEdgeWorkload, RecurrentEdgeDeviceNeed]

        return {
            'parents': edge_devices,
            'available_classes': available_classes,
        }
