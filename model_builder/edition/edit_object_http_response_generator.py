import json
from copy import copy

from django.http import QueryDict, HttpResponse
from django.template.loader import render_to_string

from model_builder.modeling_objects_web import ModelingObjectWeb
from model_builder.object_creation_and_edition_utils import edit_object_in_system


def compute_edit_object_html_and_event_response(edit_form_data: QueryDict, obj_to_edit: ModelingObjectWeb):
    accordion_children_before_edit = {}
    for mirrored_card in obj_to_edit.mirrored_cards:
        accordion_children_before_edit[mirrored_card] = copy(mirrored_card.accordion_children)

    edited_obj = edit_object_in_system(edit_form_data, obj_to_edit)

    accordion_children_after_edit = {}
    for mirrored_card in edited_obj.mirrored_cards:
        accordion_children_after_edit[mirrored_card] = copy(mirrored_card.accordion_children)
    response_html = ""

    # Delete children that don’t have any accordion parent anymore
    # It is only necessary to iterate over the children of the first mirrored card
    first_mirrored_card = next(iter(accordion_children_after_edit.keys()))
    removed_accordion_children = [acc_child for acc_child in accordion_children_before_edit[first_mirrored_card]
                                  if acc_child not in accordion_children_after_edit[first_mirrored_card]]
    for removed_accordion_child in removed_accordion_children:
        if len(removed_accordion_child.modeling_obj_containers) == 0:
            removed_accordion_child.self_delete()

    for top_parent_card in list(set([mirrored_card.top_parent for mirrored_card in
                               edited_obj.mirrored_cards])):
        response_html += (
            f"<div hx-swap-oob='outerHTML:#{top_parent_card.web_id}'>"
            f"{render_to_string(f'model_builder/object_cards/{top_parent_card.template_name}_card.html',
                                {top_parent_card.template_name: top_parent_card})}"
            f"</div>"
        )

    return response_html


def generate_http_response_from_edit_html_and_events(
    response_html: str, toast_and_highlight_data: dict, trigger_result_display = False) -> HttpResponse:
    http_response = HttpResponse(response_html)

    http_response["HX-Trigger"] = json.dumps({
        "resetLeaderLines": ""
    })

    after_settle_trigger = {
        "displayToastAndHighlightObjects": toast_and_highlight_data
    }

    if trigger_result_display:
        after_settle_trigger.update({"triggerResultRendering": ""})

    http_response["HX-Trigger-After-Settle"] = json.dumps(after_settle_trigger)

    return http_response
