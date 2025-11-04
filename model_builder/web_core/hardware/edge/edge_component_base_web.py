from typing import TYPE_CHECKING

from django.shortcuts import render
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeComponentBaseWeb(ModelingObjectWeb):
    """Base web wrapper for EdgeComponent and its subclasses."""
    @property
    def template_name(self):
        return "edge_component"

    @property
    def class_title_style(self):
        return "h8"

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        edge_device = model_web.get_web_object_from_efootprint_id(efootprint_id_of_parent_to_link_to)

        available_component_types = [EdgeCPUComponent, EdgeRAMComponent, EdgeStorage, EdgeWorkloadComponent]
        components_dict, dynamic_form_data = generate_object_creation_structure(
            "EdgeComponentBase",
            available_efootprint_classes=available_component_types,
            model_web=model_web,
        )

        context_data = {
            "edge_device": edge_device,
            "form_sections": components_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "EdgeComponentBase",
            "obj_formatting_data": FORM_TYPE_OBJECT["EdgeComponentBase"],
            "header_name": "Add new component"
        }

        return context_data

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for component creation forms - link to parent edge device."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
        }

    def generate_ask_delete_http_response(self, request):
        delete_modal_context = self.generate_ask_delete_modal_context()
        delete_modal_context["modal_id"] = "model-builder-modal"

        http_response = render(
            request, "model_builder/modals/delete_card_modal.html",
            context=delete_modal_context)

        return http_response

    def generate_delete_http_response(self, request):
        new_component_list = [comp for comp in self.edge_device.get_efootprint_value("components")
                              if comp.id != self.efootprint_id]
        self.edge_device.set_efootprint_value("components", new_component_list)

        return super().generate_delete_http_response(request)
