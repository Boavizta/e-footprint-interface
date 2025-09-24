import json

from django.http import HttpResponse
from django.shortcuts import render
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.logger import logger

from model_builder.web_core.model_web import ModelWeb
from model_builder.efootprint_to_web_mapping import (JobWeb, UsageJourneyStepWeb, UsagePatternWeb, UsageJourneyWeb,
                                                     ServerWeb)
from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response, \
    generate_http_response_from_edit_html_and_events
from model_builder.object_creation_and_edition_utils import render_exception_modal_if_error


def ask_delete_object(request, object_id):
    model_web = ModelWeb(request.session)
    web_obj = model_web.get_web_object_from_efootprint_id(object_id)

    if (not (isinstance(web_obj, UsagePatternWeb) or isinstance(web_obj, JobWeb)
             or isinstance(web_obj, UsageJourneyStepWeb)) and web_obj.modeling_obj_containers):

        if isinstance(web_obj, ServerWeb) and web_obj.jobs:
            msg = (f"This server is requested by {", ".join([obj.name for obj in web_obj.jobs])}. "
                   f"To delete it, first delete or reorient these jobs making requests to it.")
        else:
            msg = (f"This {web_obj.class_as_simple_str} is referenced by "
                   f"{", ".join([obj.name for obj in web_obj.modeling_obj_containers])}. "
                   f"To delete it, first delete or reorient these "
                   f"{web_obj.modeling_obj_containers[0].class_as_simple_str}s.")

        http_response = render(request, "model_builder/modals/cant_delete_modal.html",
            context={"modal_id": "model-builder-modal", "message": msg})
    else:
        message = f"Are you sure you want to delete this {web_obj.class_as_simple_str} ?"
        sub_message = ""
        if isinstance(web_obj, UsageJourneyWeb) and len(web_obj.uj_steps) > 0:
            message= (f"This usage journey is associated with {len(web_obj.uj_steps)} steps. This action will delete "
                      f"them all")
            sub_message = "Steps and jobs used in other usage journeys will remain in those."
        if isinstance(web_obj, UsageJourneyStepWeb) and len(web_obj.jobs) > 0:
            message= (f"This usage journey step is associated with {len(web_obj.jobs)} jobs. This action will "
                      f"delete them all")
        remove_card_with_hyperscript = True
        if isinstance(web_obj, JobWeb) or isinstance(web_obj, UsageJourneyStepWeb):
            remove_card_with_hyperscript = False
            if len(web_obj.mirrored_cards) > 1:
                message = (f"This {web_obj.class_as_simple_str} is mirrored {len(web_obj.mirrored_cards)} times, "
                           f"this action will delete all mirrored {web_obj.class_as_simple_str}s.")
                sub_message = f"To delete only one {web_obj.class_as_simple_str}, break the mirroring link first."

        http_response = render(
            request, "model_builder/modals/delete_card_modal.html",
            context={"modal_id": "model-builder-modal", "obj": web_obj, "message": message, "sub_message": sub_message,
                     "remove_card_with_hyperscript": remove_card_with_hyperscript})

    http_response["HX-Trigger-After-Swap"] = json.dumps({"openModalDialog": {"modal_id": "model-builder-modal"}})

    return http_response


@render_exception_modal_if_error
def delete_object(request, object_id):
    model_web = ModelWeb(request.session)

    web_obj = model_web.get_web_object_from_efootprint_id(object_id)
    obj_type = web_obj.efootprint_class
    system = model_web.system

    elements_with_lines_to_remove = []

    toast_and_highlight_data = {
        "ids": [],
        "name": web_obj.name,
        "action_type": "delete_object"
    }

    http_response = HttpResponse(status=204)

    if isinstance(web_obj, JobWeb) or isinstance(web_obj, UsageJourneyStepWeb):
        response_html = ""
        for contextual_modeling_obj_container in web_obj.contextual_modeling_obj_containers:
            modeling_obj_container = contextual_modeling_obj_container.modeling_obj_container
            attr_name_in_mod_obj_container = contextual_modeling_obj_container.attr_name_in_mod_obj_container
            mutable_post = request.POST.copy()
            logger.info(f"Removing {web_obj.name} from {modeling_obj_container.name}")
            mutable_post['name'] = modeling_obj_container.name
            new_list_attribute_ids = [
                list_attribute.efootprint_id
                for list_attribute in getattr(modeling_obj_container, attr_name_in_mod_obj_container)
                if list_attribute.efootprint_id != web_obj.efootprint_id]
            mutable_post[attr_name_in_mod_obj_container] = ";".join(new_list_attribute_ids)
            request.POST = mutable_post
            partial_response_html = compute_edit_object_html_and_event_response(request.POST, modeling_obj_container)
            response_html += partial_response_html

            http_response = generate_http_response_from_edit_html_and_events(response_html, toast_and_highlight_data)
    else:
        if issubclass(obj_type, UsagePattern):
            new_up_list = [up for up in system.get_efootprint_value("usage_patterns") if up.id != object_id]
            system.set_efootprint_value("usage_patterns", new_up_list)
        elements_with_lines_to_remove.append(object_id)
        web_obj.self_delete()

    model_web.update_system_data_with_up_to_date_calculated_attributes()

    http_response["HX-Trigger"] = json.dumps({
        "resetLeaderLines": "",
        "displayToastAndHighlightObjects": toast_and_highlight_data
    })

    return http_response
