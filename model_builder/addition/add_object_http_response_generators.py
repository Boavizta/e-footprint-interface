import json

from django.shortcuts import render

from model_builder.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data, render_exception_modal
from model_builder.edition.views_edition import edit_object


def add_new_usage_journey(request, model_web: ModelWeb):
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, 'UsageJourney')
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    response = render(
        request, "model_builder/object_cards/usage_journey_card.html", {"usage_journey": added_obj})
    response["HX-Trigger-After-Swap"] = json.dumps({
        "updateTopParentLines": {"topParentIds": [added_obj.web_id]},
        "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
    })

    return response


def add_new_usage_journey_step(request, model_web: ModelWeb):
    usage_journey_efootprint_id = request.POST.get('efootprint_id_of_parent_to_link_to')
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, 'UsageJourneyStep')
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    usage_journey_to_edit = model_web.get_web_object_from_efootprint_id(usage_journey_efootprint_id)
    mutable_post = request.POST.copy()
    mutable_post['name'] = usage_journey_to_edit.name
    usage_journey_step_ids = [uj_step.efootprint_id for uj_step in usage_journey_to_edit.uj_steps]
    usage_journey_step_ids.append(added_obj.efootprint_id)
    mutable_post.setlist('uj_steps', usage_journey_step_ids)
    request.POST = mutable_post

    return edit_object(request, usage_journey_efootprint_id, model_web)


def add_new_server(request, model_web: ModelWeb):
    storage_data = json.loads(request.POST.get('storage_form_data'))

    storage = create_efootprint_obj_from_post_data(storage_data, model_web, "Storage")
    added_storage = model_web.add_new_efootprint_object_to_system(storage)

    mutable_post = request.POST.copy()
    mutable_post['storage'] = added_storage.efootprint_id
    request.POST = mutable_post
    server_type = request.POST.get('type_object_available')

    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, server_type)
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    response = render(
        request, "model_builder/object_cards/server_card.html", {"server": added_obj})

    return response


def add_new_service(request, model_web: ModelWeb):
    server_efootprint_id = request.POST.get('efootprint_id_of_parent_to_link_to')
    mutable_post = request.POST.copy()
    mutable_post['server'] = server_efootprint_id
    try:
        new_efootprint_obj = create_efootprint_obj_from_post_data(
            mutable_post, model_web, request.POST.get('type_object_available'))

        efootprint_server = model_web.get_web_object_from_efootprint_id(server_efootprint_id).modeling_obj
        efootprint_server.compute_calculated_attributes()

        added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

        response = render(request, "model_builder/object_cards/service_card.html",
                          context={"service": added_obj})

        return response

    except Exception as e:
        return render_exception_modal(request, e)


def add_new_job(request, model_web: ModelWeb):
    usage_journey_step_efootprint_id = request.POST.get('efootprint_id_of_parent_to_link_to')
    usage_journey_step_to_edit = model_web.get_web_object_from_efootprint_id(usage_journey_step_efootprint_id)

    try:
        new_efootprint_obj = create_efootprint_obj_from_post_data(
            request.POST, model_web, request.POST.get('type_object_available'))
    except Exception as e:
        return render_exception_modal(request, e)

    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    mutable_post = request.POST.copy()
    mutable_post['name'] = usage_journey_step_to_edit.name
    mutable_post['user_time_spent'] = usage_journey_step_to_edit.user_time_spent.rounded_magnitude
    job_ids = [job.efootprint_id for job in usage_journey_step_to_edit.jobs]
    job_ids.append(added_obj.efootprint_id)
    mutable_post.setlist('jobs', job_ids)
    request.POST = mutable_post

    return edit_object(request, usage_journey_step_efootprint_id, model_web)


def add_new_usage_pattern(request, model_web: ModelWeb):
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, 'UsagePatternFromForm')
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    new_efootprint_obj.to_json()
    system_id = next(iter(request.session["system_data"]["System"].keys()))
    request.session["system_data"]["System"][system_id]["usage_patterns"].append(new_efootprint_obj.id)
    request.session.modified = True

    response = render(
        request, "model_builder/object_cards/usage_pattern_card.html", {"usage_pattern": added_obj})

    response["HX-Trigger-After-Swap"] = json.dumps({
        "updateTopParentLines": {"topParentIds": [added_obj.web_id]},
        "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
    })

    return response
