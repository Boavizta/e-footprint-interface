import json
from typing import TYPE_CHECKING

from django.http import QueryDict

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class ServiceWeb(ModelingObjectWeb):
    attributes_to_skip_in_forms = ["gpu_latency_alpha", "gpu_latency_beta", "server"]
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False
    skip_parent_linking = True  # Service links to server via 'server' field, not via parent list

    @property
    def class_title_style(self):
        return "h8"

    @property
    def template_name(self):
        return "service"

    @classmethod
    def generate_object_creation_context(
    cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None, object_type: str=None):
        server = model_web.get_web_object_from_efootprint_id(efootprint_id_of_parent_to_link_to)

        installable_services = server.installable_services()
        services_dict, dynamic_form_data = generate_object_creation_structure(
            "Service",
            available_efootprint_classes=installable_services,
            model_web=model_web,
        )

        context_data = {
            "server": server,
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "Service",
            "obj_formatting_data": FORM_TYPE_OBJECT["Service"],
            "header_name": "Add new service"
        }

        return context_data

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for service creation forms - link to parent server, swap beforebegin."""
        server = context_data.get("server")
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
            "hx_target": f"#add-service-to-{server.web_id}" if server else None,
            "hx_swap": "beforebegin"
        }

    @classmethod
    def prepare_creation_input(cls, form_data):
        """Map server ID from parent_to_link_to to service-specific server field."""
        server_efootprint_id = form_data.get("efootprint_id_of_parent_to_link_to")
        service_type = form_data.get("type_object_available")

        if isinstance(form_data, QueryDict):
            form_data = form_data.copy()
        else:
            form_data = dict(form_data)

        form_data[f"{service_type}_server"] = server_efootprint_id
        return form_data
