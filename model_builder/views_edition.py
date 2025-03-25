import json
from copy import copy

from django.http import HttpResponse, QueryDict
from django.shortcuts import render
from django.template.loader import render_to_string
from efootprint.builders.services.service_base_class import Service
from efootprint.core.hardware.server_base import ServerBase

from model_builder.class_structure import generate_object_edition_structure
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_web import ModelWeb, ATTRIBUTES_TO_SKIP_IN_FORMS, default_networks, default_countries, \
    default_devices
from model_builder.modeling_objects_web import ModelingObjectWeb
from model_builder.object_creation_and_edition_utils import edit_object_in_system, render_exception_modal


def open_edit_object_panel(request, object_id):
    model_web = ModelWeb(request.session)
    obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)

    structure_dict, dynamic_form_data = generate_object_edition_structure(
        obj_to_edit, attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS)

    object_belongs_to_computable_system = False
    if (len(model_web.system.servers) > 0) and (len(obj_to_edit.systems) > 0):
        object_belongs_to_computable_system = True

    if issubclass(obj_to_edit.efootprint_class, UsagePatternFromForm):
        http_response = generate_usage_pattern_edit_panel_http_response(
            request, model_web, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)
    elif issubclass(obj_to_edit.efootprint_class, ServerBase):
        http_response = generate_server_edit_panel_http_response(
            request, structure_dict, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)
    elif issubclass(obj_to_edit.efootprint_class, Service):
        http_response = generate_service_edit_panel_http_response(
            request, structure_dict, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)
    else:
        http_response = generate_generic_edit_panel_http_response(
            request, structure_dict, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response

def edit_object(request, object_id, model_web=None):
    try:
        if model_web is None:
            model_web = ModelWeb(request.session)
        obj_to_edit = model_web.get_web_object_from_efootprint_id(object_id)
        if issubclass(obj_to_edit.efootprint_class, ServerBase):
            storage_data = json.loads(request.POST.get('storage_form_data'))
            storage = model_web.get_web_object_from_efootprint_id(storage_data["storage_id"])
            edit_object_in_system(storage_data, storage)
        response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids = (
            compute_edit_object_html_and_event_response(request.POST, obj_to_edit))
    except Exception as e:
        return render_exception_modal(request, e)

    return generate_http_response_from_edit_html_and_events(
        response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids)

def save_model_name(request):
    if request.method == "POST":
        model_web = ModelWeb(request.session)
        obj_to_edit = model_web.system
        edited_obj = edit_object_in_system(request.POST, obj_to_edit)
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=400)

def generate_usage_pattern_edit_panel_http_response(
    request, model_web: ModelWeb, obj_to_edit: ModelingObjectWeb, object_belongs_to_computable_system: bool,
    dynamic_form_data: dict):
    networks = [{"efootprint_id": network["id"], "name": network["name"]} for network in
                default_networks().values()]
    countries = [{"efootprint_id": country["id"], "name": country["name"]} for country in
                 default_countries().values()]
    devices = [{"efootprint_id": device["id"], "name": device["name"]} for device in default_devices().values()]
    usage_journeys = [{'efootprint_id': uj.efootprint_id, 'name': uj.name} for uj in model_web.usage_journeys]

    modeling_obj_attributes = [
        {"attr_name": "devices", "existing_objects": devices,
         "selected_efootprint_id": obj_to_edit.devices[0].efootprint_id},
        {"attr_name": "network", "existing_objects": networks,
         "selected_efootprint_id": obj_to_edit.network.efootprint_id},
        {"attr_name": "country", "existing_objects": countries,
         "selected_efootprint_id": obj_to_edit.country.efootprint_id},
        {"attr_name": "usage_journey", "existing_objects": usage_journeys,
         "selected_efootprint_id": obj_to_edit.usage_journey.efootprint_id},
    ]

    dynamic_selects = dynamic_form_data["dynamic_lists"]
    dynamic_selects[0]["list_value"] = {
        key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in value]
        for key, value in dynamic_selects[0]["list_value"].items()
    }

    http_response = render(
        request, "model_builder/side_panels/usage_pattern/usage_pattern_edit.html",
        {
            "modeling_obj_attributes": modeling_obj_attributes,
            "object_to_edit": obj_to_edit,
            "object_to_edit_type": 'UsagePattern',
            "dynamic_form_data": {"dynamic_selects": dynamic_selects},
            "object_belongs_to_computable_system": object_belongs_to_computable_system,
            "header_name": f"Edit {obj_to_edit.name}"
        }
    )

    return http_response

def generate_server_edit_panel_http_response(
    request, structure_dict: dict, obj_to_edit: ModelingObjectWeb, object_belongs_to_computable_system: bool,
    dynamic_form_data: dict):
    storage_to_edit = obj_to_edit.storage
    structure_dict["modeling_obj_attributes"] = []
    storage_structure_dict, storage_dynamic_form_data = generate_object_edition_structure(
        storage_to_edit, attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS)

    http_response = render(
        request,
        "model_builder/side_panels/server/server_edit.html",
        context={
            "object_to_edit": obj_to_edit,
            "structure_dict": structure_dict,
            "dynamic_form_data": dynamic_form_data,
            "storage_to_edit": storage_to_edit,
            "storage_structure_dict": storage_structure_dict,
            "storage_dynamic_form_data": storage_dynamic_form_data,
            "object_to_edit_type": 'Server',
            "object_belongs_to_computable_system": object_belongs_to_computable_system,
            "header_name": f"Edit {obj_to_edit.name}"
        })

    return http_response

def generate_service_edit_panel_http_response(
    request, structure_dict: dict, obj_to_edit: ModelingObjectWeb, object_belongs_to_computable_system: bool,
    dynamic_form_data: dict):
    structure_dict["modeling_obj_attributes"] = []

    return generate_generic_edit_panel_http_response(
        request, structure_dict, obj_to_edit, object_belongs_to_computable_system, dynamic_form_data)

def generate_generic_edit_panel_http_response(
    request, structure_dict: dict, obj_to_edit: ModelingObjectWeb, object_belongs_to_computable_system: bool,
    dynamic_form_data: dict):
    http_response = render(
        request,
        "model_builder/side_panels/edit/edit_panel__generic.html",
        context={
            "object_to_edit": obj_to_edit,
            "structure_dict": structure_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_belongs_to_computable_system": object_belongs_to_computable_system,
            "header_name": f"Edit {obj_to_edit.name}"
        })

    return http_response

def compute_edit_object_html_and_event_response(edit_form_data: QueryDict, obj_to_edit: ModelingObjectWeb):
    data_attribute_updates = []
    ids_of_web_elements_with_lines_to_remove = []
    accordion_children_before_edit = {}
    for duplicated_card in obj_to_edit.duplicated_cards:
        accordion_children_before_edit[duplicated_card] = copy(duplicated_card.accordion_children)

    edited_obj = edit_object_in_system(edit_form_data, obj_to_edit)
    accordion_children_after_edit = {}
    for duplicated_card in edited_obj.duplicated_cards:
        accordion_children_after_edit[duplicated_card] = copy(duplicated_card.accordion_children)

    assert accordion_children_before_edit.keys() == accordion_children_after_edit.keys()

    response_html = ""
    for duplicated_card in accordion_children_before_edit.keys():
        response_html += f"<p hx-swap-oob='innerHTML:#button-{duplicated_card.web_id}'>{duplicated_card.name}</p>"
        added_accordion_children = [acc_child for acc_child in accordion_children_after_edit[duplicated_card]
                                    if acc_child not in accordion_children_before_edit[duplicated_card]]

        removed_accordion_children = [acc_child for acc_child in accordion_children_before_edit[duplicated_card]
                                      if acc_child not in accordion_children_after_edit[duplicated_card]]

        for removed_accordion_child in removed_accordion_children:
            response_html += f"<div hx-swap-oob='delete:#{removed_accordion_child.web_id}'></div>"
            ids_of_web_elements_with_lines_to_remove.append(removed_accordion_child.web_id)
            index_removed_accordion_child = accordion_children_before_edit[duplicated_card].index(
                removed_accordion_child)
            if index_removed_accordion_child >= 1:
                previous_accordion = accordion_children_before_edit[duplicated_card][index_removed_accordion_child-1]
                if previous_accordion not in removed_accordion_children:
                    data_attribute_updates += previous_accordion.data_attributes_as_list_of_dict
            if len(removed_accordion_child.modeling_obj_containers) == 0:
                removed_accordion_child.self_delete()

        unchanged_children = [acc_child for acc_child in accordion_children_after_edit[duplicated_card]
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
            response_html += (f"<div hx-swap-oob='afterbegin:#flush-{duplicated_card.web_id} "
                              f".accordion-body'>{added_children_html}</div>")

    for duplicated_card in edited_obj.duplicated_cards:
        data_attribute_updates += duplicated_card.data_attributes_as_list_of_dict
        for parent in duplicated_card.all_accordion_parents:
            data_attribute_updates += parent.data_attributes_as_list_of_dict

    top_parent_ids = list(set([duplicated_card.top_parent.web_id for duplicated_card in
                                   edited_obj.duplicated_cards]))

    return response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids


def generate_http_response_from_edit_html_and_events(
    response_html, ids_of_web_elements_with_lines_to_remove, data_attribute_updates, top_parent_ids):
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
        }
    })

    return http_response
