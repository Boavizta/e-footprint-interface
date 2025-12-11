from typing import TYPE_CHECKING

from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed

from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.domain.entities.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class RecurrentEdgeDeviceNeedBaseWeb(ResourceNeedBaseWeb):
    """Web wrapper for RecurrentEdgeDeviceNeed and its subclasses (RecurrentEdgeProcess, RecurrentEdgeWorkload)."""
    attributes_to_skip_in_forms = ["edge_device"]

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'parent_selection',
        'object_type': 'RecurrentEdgeDeviceNeedBase',
    }

    @classmethod
    def get_form_creation_data(cls, model_web: "ModelWeb") -> dict:
        """Provide form data for parent_selection strategy.

        Returns data for FormContextBuilder to build the form structure.
        Domain logic stays here; form generation happens in adapter.
        """
        edge_devices = model_web.edge_devices
        if len(edge_devices) == 0:
            raise ValueError("Please create an edge device before adding a recurrent edge resource need")

        # RecurrentEdgeProcess works with EdgeComputer, RecurrentEdgeWorkload works with EdgeAppliance,
        # RecurrentEdgeDeviceNeed works with EdgeDevice.
        available_resource_need_classes = [RecurrentEdgeProcess, RecurrentEdgeWorkload, RecurrentEdgeDeviceNeed]

        # Build helper field for edge device selection
        helper_fields = [
            {
                "input_type": "select_object",
                "web_id": "edge_device",
                "name": "Edge Device",
                "options": [
                    {"label": edge_device.name, "value": edge_device.efootprint_id}
                    for edge_device in edge_devices],
                "label": "Choose an edge device",
            },
        ]

        # Define which resource need types are compatible with which edge device types
        possible_resource_need_types_per_device = {}
        for edge_device in edge_devices:
            device_class = edge_device.class_as_simple_str
            if device_class == "EdgeComputer":
                possible_resource_need_types_per_device[edge_device.efootprint_id] = [
                    {"label": FORM_TYPE_OBJECT["RecurrentEdgeProcess"]["label"], "value": "RecurrentEdgeProcess"}
                ]
            elif device_class == "EdgeAppliance":
                possible_resource_need_types_per_device[edge_device.efootprint_id] = [
                    {"label": FORM_TYPE_OBJECT["RecurrentEdgeWorkload"]["label"], "value": "RecurrentEdgeWorkload"}
                ]
            elif device_class == "EdgeDevice":
                possible_resource_need_types_per_device[edge_device.efootprint_id] = [
                    {"label": FORM_TYPE_OBJECT["RecurrentEdgeDeviceNeed"]["label"], "value": "RecurrentEdgeDeviceNeed"}
                ]
            else:
                raise ValueError(f"Unknown edge device class: {device_class}")

        dynamic_selects = [
            {
                "input_id": "type_object_available",
                "filter_by": "edge_device",
                "list_value": possible_resource_need_types_per_device
            }
        ]

        return {
            'available_classes': available_resource_need_classes,
            'helper_fields': helper_fields,
            'dynamic_selects': dynamic_selects,
        }
