import json
import math

from django.shortcuts import render
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.constants.units import u

from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response, \
    generate_http_response_from_edit_html_and_events
from model_builder.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import (
    create_efootprint_obj_from_post_data, render_exception_modal_if_error)


def add_new_journey(request, model_web: ModelWeb, journey_type: str):
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, journey_type)
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    response = render(
        request, f"model_builder/object_cards/{added_obj.template_name}_card.html",
        {added_obj.template_name: added_obj})

    response["HX-Trigger-After-Swap"] = json.dumps({
        "resetLeaderLines": "",
        "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
        "displayToastAndHighlightObjects": {
            "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
    })

    return response


def add_new_usage_journey_step(request, model_web: ModelWeb):
    usage_journey_efootprint_id = request.POST.get("efootprint_id_of_parent_to_link_to")
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, "UsageJourneyStep")
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    usage_journey_to_edit = model_web.get_web_object_from_efootprint_id(usage_journey_efootprint_id)
    mutable_post = request.POST.copy()
    mutable_post["name"] = usage_journey_to_edit.name
    usage_journey_step_ids = [uj_step.efootprint_id for uj_step in usage_journey_to_edit.uj_steps]
    usage_journey_step_ids.append(added_obj.efootprint_id)
    mutable_post["uj_steps"] =  ";".join(usage_journey_step_ids)
    request.POST = mutable_post

    response_html = compute_edit_object_html_and_event_response(request.POST, usage_journey_to_edit)

    # There will always be only one mirrored card for a newly created usage journey step
    toast_and_highlight_data = {
        "ids": [added_obj.mirrored_cards[0].web_id], "name": added_obj.name,
        "action_type": "add_new_object"
    }

    return generate_http_response_from_edit_html_and_events(response_html, toast_and_highlight_data)


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

@render_exception_modal_if_error
def add_new_job(request, model_web: ModelWeb):
    usage_journey_step_efootprint_id = request.POST.get("efootprint_id_of_parent_to_link_to")
    usage_journey_step_to_edit = model_web.get_web_object_from_efootprint_id(usage_journey_step_efootprint_id)

    new_efootprint_obj = create_efootprint_obj_from_post_data(
        request.POST, model_web, request.POST.get("type_object_available"))

    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    mutable_post = request.POST.copy()
    mutable_post["name"] = usage_journey_step_to_edit.name
    mutable_post["user_time_spent"] = usage_journey_step_to_edit.user_time_spent.magnitude
    mutable_post["user_time_spent_unit"] = str(usage_journey_step_to_edit.user_time_spent.value.units)
    job_ids = [job.efootprint_id for job in usage_journey_step_to_edit.jobs]
    job_ids.append(added_obj.efootprint_id)
    mutable_post["jobs"]= ";".join(job_ids)
    request.POST = mutable_post

    response_html = compute_edit_object_html_and_event_response(request.POST, usage_journey_step_to_edit)

    toast_and_highlight_data = {
        "ids": [mirrored_card.web_id for mirrored_card in added_obj.mirrored_cards], "name": added_obj.name,
        "action_type": "add_new_object"
    }

    return generate_http_response_from_edit_html_and_events(response_html, toast_and_highlight_data)


def add_new_usage_pattern(request, model_web: ModelWeb):
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, "UsagePatternFromForm")
    model_web.system.modeling_obj.usage_patterns.append(new_efootprint_obj)
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    response = render(
        request, "model_builder/object_cards/usage_pattern_card.html", {"usage_pattern": added_obj})

    response["HX-Trigger-After-Swap"] = json.dumps({
        "resetLeaderLines": "",
        "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
        "displayToastAndHighlightObjects": {
            "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
    })

    return response
