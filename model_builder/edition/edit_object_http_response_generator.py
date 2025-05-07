import json
from copy import copy

from django.http import QueryDict, HttpResponse
from django.template.loader import render_to_string

from model_builder.modeling_objects_web import ModelingObjectWeb
from model_builder.object_creation_and_edition_utils import edit_object_in_system


def compute_edit_object_html_and_event_response(edit_form_data: QueryDict, obj_to_edit: ModelingObjectWeb):
    data_attribute_updates = []
    ids_of_web_elements_with_lines_to_remove = []
    accordion_children_before_edit = {}
    for mirrored_card in obj_to_edit.mirrored_cards:
        accordion_children_before_edit[mirrored_card] = copy(mirrored_card.accordion_children)

    edited_obj = edit_object_in_system(edit_form_data, obj_to_edit)
    accordion_children_after_edit = {}
    for mirrored_card in edited_obj.mirrored_cards:
        accordion_children_after_edit[mirrored_card] = copy(mirrored_card.accordion_children)

    assert accordion_children_before_edit.keys() == accordion_children_after_edit.keys()

    response_html = ""
    for mirrored_card in accordion_children_before_edit.keys():
        response_html += (f"<div hx-swap-oob='innerHTML:#button-{mirrored_card.web_id}'>"
                          f"<p class='{mirrored_card.class_title_style} mb-0'>{mirrored_card.name}</p>"
                          f"</div>")
        added_accordion_children = [acc_child for acc_child in accordion_children_after_edit[mirrored_card]
                                    if acc_child not in accordion_children_before_edit[mirrored_card]]

        removed_accordion_children = [acc_child for acc_child in accordion_children_before_edit[mirrored_card]
                                      if acc_child not in accordion_children_after_edit[mirrored_card]]

        for removed_accordion_child in removed_accordion_children:
            response_html += f"<div hx-swap-oob='delete:#{removed_accordion_child.web_id}'></div>"
            ids_of_web_elements_with_lines_to_remove.append(removed_accordion_child.web_id)
            index_removed_accordion_child = accordion_children_before_edit[mirrored_card].index(
                removed_accordion_child)
            if index_removed_accordion_child >= 1:
                previous_accordion = accordion_children_before_edit[mirrored_card][index_removed_accordion_child-1]
                if previous_accordion not in removed_accordion_children:
                    data_attribute_updates += previous_accordion.data_attributes_as_list_of_dict

        unchanged_children = [acc_child for acc_child in accordion_children_after_edit[mirrored_card]
                              if acc_child not in added_accordion_children]

        added_children_html = ""
        for added_accordion_child in added_accordion_children:
            added_children_html += render_to_string(
                f"model_builder/object_cards/{added_accordion_child.template_name}_card.html",
                {added_accordion_child.template_name: added_accordion_child})

        if unchanged_children and added_accordion_children:
            last_unchanged_child = unchanged_children[-1]
            data_attribute_updates += last_unchanged_child.data_attributes_as_list_of_dict
            response_html += (f"<div hx-swap-oob='afterend:#{last_unchanged_child.web_id}'>"
                                  f"{added_children_html}</div>")

        elif added_accordion_children and not unchanged_children:
            response_html += (f"<div hx-swap-oob='afterbegin:#flush-{mirrored_card.web_id} "
                              f".accordion-body'>{added_children_html}</div>")

    # Delete children that don’t have any accordion parent anymore
    # It is only necessary to iterate over the children of the first mirrored card
    first_mirrored_card = list(accordion_children_after_edit.keys())[0]
    removed_accordion_children = [acc_child for acc_child in accordion_children_before_edit[first_mirrored_card]
                                  if acc_child not in accordion_children_after_edit[first_mirrored_card]]
    for removed_accordion_child in removed_accordion_children:
        if len(removed_accordion_child.modeling_obj_containers) == 0:
            removed_accordion_child.self_delete()

    for mirrored_card in edited_obj.mirrored_cards:
        data_attribute_updates += mirrored_card.data_attributes_as_list_of_dict
        for parent in mirrored_card.all_accordion_parents:
            data_attribute_updates += parent.data_attributes_as_list_of_dict

    top_parent_ids = list(set([mirrored_card.top_parent.web_id for mirrored_card in
                                   edited_obj.mirrored_cards]))

    return response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids


def generate_http_response_from_edit_html_and_events(
    response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids,
    toast_and_highlight_data):
    http_response = HttpResponse(response_html)

    http_response["HX-Trigger"] = json.dumps({
        "removeLinesAndUpdateDataAttributes": {
            "elementIdsOfLinesToRemove": ids_of_web_elements_with_lines_to_remove,
            "dataAttributeUpdates": data_attribute_updates
        }
    })

    http_response["HX-Trigger-After-Swap"] = json.dumps({
        "updateTopParentLines": {
            "topParentIds": top_parent_ids
        },
        "displayToastAndHighlightObjects": toast_and_highlight_data
    })

    return http_response
