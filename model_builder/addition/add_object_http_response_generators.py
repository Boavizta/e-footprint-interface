import json
import math
from typing import get_origin, List, get_args

from django.http import QueryDict
from django.shortcuts import render
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.constants.units import u
from efootprint.utils.tools import get_init_signature_params

from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response, \
    generate_http_response_from_edit_html_and_events
from model_builder.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import (
    create_efootprint_obj_from_post_data, render_exception_modal_if_error)


@render_exception_modal_if_error
def add_new_object(request, model_web: ModelWeb, object_type: str):
    object_creation_type = request.POST.get("type_object_available", object_type)
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, object_creation_type)
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    object_to_link_to_id = request.POST.get("efootprint_id_of_parent_to_link_to", None)

    if object_to_link_to_id is None:
        response = render(
            request, f"model_builder/object_cards/{added_obj.template_name}_card.html",
            {added_obj.template_name: added_obj})

        response["HX-Trigger-After-Swap"] = json.dumps({
            "resetLeaderLines": "",
            "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
            "displayToastAndHighlightObjects": {
                "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
        })
    else:
        web_object_to_link_to = model_web.get_web_object_from_efootprint_id(object_to_link_to_id)
        efootprint_object_to_link_to = web_object_to_link_to.modeling_obj
        # Find the attr name for the list of objects to append the added object to in the efootprint_object_to_link_to
        init_sig_params = get_init_signature_params(type(efootprint_object_to_link_to))
        list_attr_name = None
        for attr_name in init_sig_params:
            annotation = init_sig_params[attr_name].annotation
            if (get_origin(annotation) and get_origin(annotation) in (list, List)
                and isinstance(new_efootprint_obj, get_args(annotation)[0])):
                list_attr_name = attr_name
                break
        assert list_attr_name is not None, f"A list attr name should always be found"

        mutable_post = QueryDict(mutable=True)
        existing_element_ids = [elt.id for elt in getattr(efootprint_object_to_link_to, list_attr_name)]
        existing_element_ids.append(added_obj.efootprint_id)
        mutable_post[list_attr_name] = ";".join(existing_element_ids)

        response_html = compute_edit_object_html_and_event_response(mutable_post, web_object_to_link_to)

        toast_and_highlight_data = {
            "ids": [mirrored_card.web_id for mirrored_card in added_obj.mirrored_cards], "name": added_obj.name,
            "action_type": "add_new_object"
        }

        response = generate_http_response_from_edit_html_and_events(response_html, toast_and_highlight_data)

    return response

@render_exception_modal_if_error
def add_new_object_with_storage(request, model_web: ModelWeb, storage_type: str):
    storage_data = json.loads(request.POST.get("storage_form_data"))

    storage = create_efootprint_obj_from_post_data(storage_data, model_web, storage_type)
    added_storage = model_web.add_new_efootprint_object_to_system(storage)

    mutable_post = request.POST.copy()
    request.POST = mutable_post
    server_type = request.POST.get("type_object_available")
    mutable_post[server_type + "_" + "storage"] = added_storage.efootprint_id

    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, server_type)
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    response = render(
        request, f"model_builder/object_cards/{added_obj.template_name}_card.html", {added_obj.template_name: added_obj})
    response["HX-Trigger-After-Swap"] = json.dumps({
        "displayToastAndHighlightObjects": {
            "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
    })

    return response

@render_exception_modal_if_error
def add_new_service(request, model_web: ModelWeb):
    server_efootprint_id = request.POST.get("efootprint_id_of_parent_to_link_to")
    service_type = request.POST.get("type_object_available")
    mutable_post = request.POST.copy()
    mutable_post[f"{service_type}_server"] = server_efootprint_id
    new_efootprint_obj = create_efootprint_obj_from_post_data(mutable_post, model_web, service_type)

    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    response = render(request, "model_builder/object_cards/service_card.html",
                      context={"service": added_obj})
    response["HX-Trigger-After-Swap"] = json.dumps({
        "displayToastAndHighlightObjects": {
            "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
    })
    return response

@render_exception_modal_if_error
def add_new_external_api(request, model_web):
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
        request, "model_builder/object_cards/server_card.html", {"server": new_server_web})
    response["HX-Trigger-After-Swap"] = json.dumps({
        "displayToastAndHighlightObjects": {
            "ids": [new_server_web.web_id], "name": new_server_web.name, "action_type": "add_new_object"}
    })

    return response
