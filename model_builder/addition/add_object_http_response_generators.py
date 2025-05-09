import json

from django.http import QueryDict
from django.shortcuts import render

from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response, \
    generate_http_response_from_edit_html_and_events
from model_builder.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import (create_efootprint_obj_from_post_data,
                                                             render_exception_modal_if_error, edit_object_in_system)


def add_new_usage_journey(request, model_web: ModelWeb):
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, "UsageJourney")
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    response = render(
        request, "model_builder/object_cards/usage_journey_card.html", {"usage_journey": added_obj})

    response["HX-Trigger-After-Swap"] = json.dumps({
        "updateTopParentLines": {"topParentIds": [added_obj.web_id]},
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
    mutable_post.setlist("uj_steps", usage_journey_step_ids)
    request.POST = mutable_post

    response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids = (
        compute_edit_object_html_and_event_response(request.POST, usage_journey_to_edit))

    # There will always be only one mirrored card for a newly created usage journey step
    toast_and_highlight_data = {
        "ids": [added_obj.mirrored_cards[0].web_id], "name": added_obj.name,
        "action_type": "add_new_object"
    }

    return generate_http_response_from_edit_html_and_events(
        response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids,
        toast_and_highlight_data)


def add_new_server(request, model_web: ModelWeb):
    storage_data = json.loads(request.POST.get("storage_form_data"))

    storage = create_efootprint_obj_from_post_data(storage_data, model_web, "Storage")
    added_storage = model_web.add_new_efootprint_object_to_system(storage)

    mutable_post = request.POST.copy()
    request.POST = mutable_post
    server_type = request.POST.get("type_object_available")
    mutable_post[server_type + "_" + "storage"] = added_storage.efootprint_id

    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, server_type)
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    response = render(
        request, "model_builder/object_cards/server_card.html", {"server": added_obj})
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

    efootprint_server = model_web.get_web_object_from_efootprint_id(server_efootprint_id).modeling_obj
    efootprint_server.compute_calculated_attributes()

    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    response = render(request, "model_builder/object_cards/service_card.html",
                      context={"service": added_obj})
    response["HX-Trigger-After-Swap"] = json.dumps({
        "displayToastAndHighlightObjects": {
            "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
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
    mutable_post.setlist("jobs", job_ids)
    request.POST = mutable_post

    response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids = (
        compute_edit_object_html_and_event_response(request.POST, usage_journey_step_to_edit))

    toast_and_highlight_data = {
        "ids": [mirrored_card.web_id for mirrored_card in added_obj.mirrored_cards], "name": added_obj.name,
        "action_type": "add_new_object"
    }

    return generate_http_response_from_edit_html_and_events(
        response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids,
        toast_and_highlight_data)


def add_new_usage_pattern(request, model_web: ModelWeb):
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, "UsagePatternFromForm")
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    mutable_post = QueryDict(mutable=True)
    mutable_post["name"] = model_web.system.name
    usage_patterns_ids = [usage_pattern.efootprint_id for usage_pattern in model_web.system.usage_patterns]
    usage_patterns_ids.append(added_obj.efootprint_id)
    mutable_post.setlist("usage_patterns", usage_patterns_ids)
    request.POST = mutable_post
    edit_object_in_system(request.POST, model_web.system)

    response = render(
        request, "model_builder/object_cards/usage_pattern_card.html", {"usage_pattern": added_obj})

    response["HX-Trigger-After-Swap"] = json.dumps({
        "updateTopParentLines": {"topParentIds": [added_obj.web_id]},
        "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
        "displayToastAndHighlightObjects": {
            "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
    })

    return response
