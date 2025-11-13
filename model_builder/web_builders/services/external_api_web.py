import json
import math
from typing import TYPE_CHECKING

from django.shortcuts import render
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.services.generative_ai_ecologits import GenAIModel
from efootprint.constants.units import u
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class ExternalApiWeb(ModelingObjectWeb):
    @classmethod
    def generate_object_creation_context(
    cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None, object_type: str=None):
        services_dict, dynamic_form_data = generate_object_creation_structure(
            "Service",
            available_efootprint_classes=[GenAIModel],
            model_web=model_web,
        )

        services_dict[0]["fields"][0]["label"] = "Available services"

        context_data = {
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "ExternalApi",
            "obj_formatting_data": FORM_TYPE_OBJECT["ExternalApi"],
            "header_name": "Add new external API",
        }

        return context_data

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for external API creation forms - append to #server-list."""
        return {"hx_target": "#server-list", "hx_swap": "beforeend"}

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        new_storage = Storage.ssd()

        model_web.add_new_efootprint_object_to_system(new_storage)
        service_type = request.POST.get("type_object_available")
        if service_type != "GenAIModel":
            raise Exception(f"External service {service_type} not supported yet.")

        new_server = GPUServer.from_defaults(
            name=f'{request.POST.get("GenAIModel_name")} API servers', server_type=ServerTypes.serverless(),
            storage=new_storage, compute=SourceValue(1 * u.gpu))
        new_server_web = model_web.add_new_efootprint_object_to_system(new_server)
        mutable_post = request.POST.copy()
        mutable_post[f"{service_type}_server"] = new_server.id

        try:
            new_service = create_efootprint_obj_from_post_data(mutable_post, model_web, service_type)
        except InsufficientCapacityError as e:
            new_service = new_server.installed_services[0]
            nb_of_gpus_required = math.ceil((e.requested_capacity / new_server.ram_per_gpu).to(u.gpu).magnitude)
            new_server.compute = SourceValue(
                nb_of_gpus_required * u.gpu, source=Source("Computed to match model size", link=None))
            # Important to re-run after_init because it had been interrupted by the error.
            # Otherwise, server base ram and compute consumption won’t be updated and neither will System total footprint.
            new_service.after_init()

        model_web.add_new_efootprint_object_to_system(new_service)

        response = render(
            request, "model_builder/object_cards/server_card.html", {"object": new_server_web})
        response["HX-Trigger-After-Swap"] = json.dumps({
            "displayToastAndHighlightObjects": {
                "ids": [new_server_web.web_id], "name": new_server_web.name, "action_type": "add_new_object"}
        })

        return response
