import json

from django.http import HttpResponse
from django.shortcuts import render
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.logger import logger

from model_builder.model_web import ModelWeb
from model_builder.modeling_objects_web import JobWeb, UsageJourneyStepWeb, UsagePatternWeb, UsageJourneyWeb, ServerWeb
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
            context={"msg": msg})
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
            context={"obj": web_obj, "message": message, "sub_message": sub_message,
                     "remove_card_with_hyperscript": remove_card_with_hyperscript})

    http_response["HX-Trigger-After-Swap"] = "openModalDialog"

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
        ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids = [], [], []
        for mirrored_card in web_obj.mirrored_cards:
            mutable_post = request.POST.copy()
            parent = mirrored_card.accordion_parent
            logger.info(f"Removing {mirrored_card.name} from {parent.name}")
            mutable_post['name'] = parent.name
            new_list_attribute_ids = [list_attribute.efootprint_id for list_attribute in parent.accordion_children
                                      if list_attribute.efootprint_id != mirrored_card.efootprint_id]
            list_attribute_name = mirrored_card.modeling_obj.contextual_modeling_obj_containers[0].attr_name_in_mod_obj_container
            mutable_post.setlist(f'{list_attribute_name}', new_list_attribute_ids)
            request.POST = mutable_post
            (partial_response_html, partial_ids_of_web_elements_with_lines_to_remove,
             partial_data_attribute_updates, partial_top_parent_ids) = compute_edit_object_html_and_event_response(
                request.POST, parent)
            response_html += partial_response_html
            ids_of_web_elements_with_lines_to_remove += partial_ids_of_web_elements_with_lines_to_remove
            data_attribute_updates += partial_data_attribute_updates
            top_parent_ids += partial_top_parent_ids

            http_response = generate_http_response_from_edit_html_and_events(
                response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids,
                toast_and_highlight_data)
    else:
        if issubclass(obj_type, UsagePattern):
            new_up_list = [up for up in system.get_efootprint_value("usage_patterns") if up.id != object_id]
            system.set_efootprint_value("usage_patterns", new_up_list)
        elements_with_lines_to_remove.append(object_id)
        web_obj.self_delete()

    model_web.update_system_data_with_up_to_date_calculated_attributes()

    if elements_with_lines_to_remove:
        http_response["HX-Trigger"] = json.dumps({
            "removeLinesAndUpdateDataAttributes": {
                "elementIdsOfLinesToRemove": elements_with_lines_to_remove,
                "dataAttributeUpdates": []
            },
            "displayToastAndHighlightObjects": toast_and_highlight_data
        })

    return http_response
