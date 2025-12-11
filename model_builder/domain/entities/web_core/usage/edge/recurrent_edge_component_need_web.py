from typing import TYPE_CHECKING

from efootprint.constants.sources import Sources
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed

from model_builder.domain.entities.efootprint_extensions.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant)
from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class RecurrentEdgeComponentNeedWeb(ModelingObjectWeb):
    """Web wrapper for RecurrentEdgeComponentNeed."""
    attributes_to_skip_in_forms = ["edge_component"]
    add_template = "add_recurrent_edge_component_need.html"
    edit_template = "edit_recurrent_edge_component_need.html"
    default_values = {
        "recurrent_need": ExplainableRecurrentQuantitiesFromConstant(
            form_inputs={"constant_value": 1.0, "constant_unit": "concurrent"},
            label="Default recurrent need", source=Sources.HYPOTHESIS)
    }

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'nested_parent_selection',
    }

    @property
    def template_name(self):
        return "recurrent_edge_component_need"

    @property
    def class_title_style(self):
        return "h8"

    @classmethod
    def get_form_creation_data(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to: str) -> dict:
        """Provide form data for nested_parent_selection strategy.

        Returns data for FormContextBuilder to build the form structure.
        Domain logic stays here; form generation happens in adapter.
        """
        recurrent_edge_device_need = model_web.get_web_object_from_efootprint_id(efootprint_id_of_parent_to_link_to)
        edge_device = recurrent_edge_device_need.edge_device
        edge_components = edge_device.components

        if len(edge_components) == 0:
            raise ValueError(
                f"Please add components to edge device '{edge_device.name}' before adding recurrent edge component needs")

        # Build helper field for component selection
        helper_fields = [
            {
                "input_type": "select_object",
                "web_id": "edge_component",
                "name": "Edge Component",
                "options": [
                    {"label": component.name, "value": component.efootprint_id}
                    for component in edge_components],
                "label": "Choose an edge component",
            },
        ]

        # Create mapping of component IDs to their compatible units for dynamic default value generation
        component_units_mapping = {}
        for component in edge_components:
            compatible_units = component.get_efootprint_value("compatible_root_units")
            if compatible_units and len(compatible_units) > 0:
                compatible_unit = str(compatible_units[0])
                if compatible_unit == "bit_ram":
                    compatible_unit = "GB_ram"
                component_units_mapping[component.efootprint_id] = compatible_unit
            else:
                raise ValueError(f"Component {component.name} has no compatible_root_units defined")

        return {
            'available_classes': [RecurrentEdgeComponentNeed],
            'helper_fields': helper_fields,
            'parent_context_key': 'recurrent_edge_device_need',
            'parent': recurrent_edge_device_need,
            'extra_dynamic_data': {'component_units_mapping': component_units_mapping},
        }

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for component need creation forms - link to parent."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
        }
