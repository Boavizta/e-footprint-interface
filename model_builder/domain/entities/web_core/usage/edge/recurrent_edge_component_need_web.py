from typing import TYPE_CHECKING

from efootprint.constants.sources import Sources
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed

from model_builder.adapters.forms.class_structure import generate_object_creation_structure
from model_builder.domain.entities.efootprint_extensions.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant)
from model_builder.form_references import FORM_TYPE_OBJECT
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

    @property
    def template_name(self):
        return "recurrent_edge_component_need"

    @property
    def class_title_style(self):
        return "h8"

    @classmethod
    def generate_object_creation_context(
    cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None, object_type: str=None):
        """Generate creation context with edge components from parent RecurrentEdgeDeviceNeed."""
        recurrent_edge_device_need = model_web.get_web_object_from_efootprint_id(efootprint_id_of_parent_to_link_to)
        edge_device = recurrent_edge_device_need.edge_device
        edge_components = edge_device.components

        if len(edge_components) == 0:
            raise ValueError(
                f"Please add components to edge device '{edge_device.name}' before adding recurrent edge component needs")

        available_component_need_classes = [RecurrentEdgeComponentNeed]
        base_object_type = "RecurrentEdgeComponentNeed"

        form_sections, dynamic_form_data = generate_object_creation_structure(
            base_object_type,
            available_efootprint_classes=available_component_need_classes,
            model_web=model_web,
        )

        additional_item = {
            "category": "component_need_creation_helper",
            "header": "Component need creation helper",
            "fields": [
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
        }
        form_sections = [additional_item] + form_sections

        # Create mapping of component IDs to their compatible units for dynamic default value generation
        component_units_mapping = {}
        for component in edge_components:
            compatible_units = component.get_efootprint_value("compatible_root_units")
            if compatible_units and len(compatible_units) > 0:
                # Use the first compatible unit as default
                compatible_unit = str(compatible_units[0])
                if compatible_unit == "bit_ram":
                    compatible_unit = "GB_ram"
                component_units_mapping[component.efootprint_id] = compatible_unit
            else:
                raise ValueError(f"Component {component.name} has no compatible_root_units defined")

        dynamic_form_data["component_units_mapping"] = component_units_mapping

        context_data = {
            "recurrent_edge_device_need": recurrent_edge_device_need,
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "object_type": base_object_type,
            "obj_formatting_data": FORM_TYPE_OBJECT.get(base_object_type, {"label": "Recurrent edge component need"}),
            "header_name": "Add new recurrent edge component need"
        }

        return context_data

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for component need creation forms - link to parent."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
        }
