import json

from django.http import HttpResponse
from django.shortcuts import render
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.logger import logger

from model_builder.class_structure import efootprint_class_structure
from model_builder.model_web import ModelWeb
from model_builder.modeling_objects_web import JobWeb, UsageJourneyStepWeb, UsagePatternWeb, UsageJourneyWeb, ServerWeb
from model_builder.edition.edit_object_http_response_generator import compute_edit_object_html_and_event_response, \
    generate_http_response_from_edit_html_and_events


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
        if isinstance(web_obj, UsageJourneyWeb):
            message= (f"This usage journey is associated with {len(web_obj.uj_steps)} steps. This action will delete "
                      f"them all")
            sub_message = "Steps and jobs used in other usage journeys will remain in those."
        if isinstance(web_obj, UsageJourneyStepWeb):
            message= (f"This usage journey step is associated with {len(web_obj.jobs)} jobs. This action will "
                      f"delete "
                      f"them all")
        remove_card_with_hyperscript = True
        if isinstance(web_obj, JobWeb) or isinstance(web_obj, UsageJourneyStepWeb):
            remove_card_with_hyperscript = False
            if len(web_obj.duplicated_cards) > 1:
                message = (f"This {web_obj.class_as_simple_str} is mirrored {len(web_obj.duplicated_cards)} times, "
                           f"this action will delete all mirrored {web_obj.class_as_simple_str}s.")
                sub_message = f"To delete only one {web_obj.class_as_simple_str}, break the mirroring link first."

        http_response = render(
            request, "model_builder/modals/delete_card_modal.html",
            context={"obj": web_obj, "message": message, "sub_message": sub_message,
                     "remove_card_with_hyperscript": remove_card_with_hyperscript})

    http_response["HX-Trigger-After-Swap"] = "openModalDialog"

    return http_response


def delete_object(request, object_id):
    model_web = ModelWeb(request.session)

    web_obj = model_web.get_web_object_from_efootprint_id(object_id)
    obj_type = web_obj.efootprint_class
    system = model_web.system

    elements_with_lines_to_remove = []

    http_response = HttpResponse(status=204)

    if issubclass(obj_type, UsagePattern):
        new_up_list = [up for up in system.get_efootprint_value("usage_patterns") if up.id != object_id]
        system.set_efootprint_value("usage_patterns", new_up_list)
        system_id = next(iter(request.session["system_data"]["System"].keys()))
        request.session["system_data"]["System"][system_id]["usage_patterns"] = [up.id for up in new_up_list]
        obj_type_str = obj_type.__name__
        request.session["system_data"][obj_type_str].pop(object_id)
        if len(new_up_list) == 0:
            del request.session["system_data"][obj_type_str]
        request.session.modified = True
        elements_with_lines_to_remove.append(object_id)
    elif isinstance(web_obj, JobWeb) or isinstance(web_obj, UsageJourneyStepWeb):
        response_html = ""
        ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids = [], [], []
        for duplicated_card in web_obj.duplicated_cards:
            mutable_post = request.POST.copy()
            parent = duplicated_card.accordion_parent
            logger.info(f"Removing {duplicated_card.name} from {parent.name}")
            mutable_post['name'] = parent.name
            new_list_attribute_ids = [list_attribute.efootprint_id for list_attribute in parent.accordion_children
                                      if list_attribute.efootprint_id != duplicated_card.efootprint_id]
            list_attribute_name = efootprint_class_structure(
                parent.class_as_simple_str)["list_attributes"][0]["attr_name"]
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
                response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids)
    else:
        web_obj.self_delete()
        elements_with_lines_to_remove.append(object_id)

    if elements_with_lines_to_remove:
        http_response["HX-Trigger"] = json.dumps({
            "removeLinesAndUpdateDataAttributes": {
                "elementIdsOfLinesToRemove": elements_with_lines_to_remove,
                "dataAttributeUpdates": []
            }
        })

    return http_response
