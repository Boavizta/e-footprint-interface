import json
from typing import List, TYPE_CHECKING

from django.shortcuts import render

from model_builder.class_structure import generate_object_creation_structure, generate_dynamic_form
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


def generate_object_with_storage_creation_context(
    model_web: "ModelWeb", object_type: str, available_efootprint_classes: List, storage_type: str,
    available_storage_classes: List):
    form_sections, dynamic_form_data = generate_object_creation_structure(
        object_type,
        available_efootprint_classes=available_efootprint_classes,
        model_web=model_web,
    )

    storage_form_sections, storage_dynamic_form_data = generate_object_creation_structure(
        storage_type,
        available_efootprint_classes=available_storage_classes,
        model_web=model_web,
    )

    context_data = {
        "object_type": object_type,
        "form_sections": form_sections,
        "dynamic_form_data": dynamic_form_data,
        "storage_form_sections": storage_form_sections,
        "storage_dynamic_form_data": storage_dynamic_form_data,
        "header_name": f"Add new {FORM_TYPE_OBJECT[object_type]['label'].lower()}"
    }

    return context_data


def generate_object_with_storage_edition_context(obj_to_edit):
    storage_to_edit = obj_to_edit.storage

    form_fields, form_fields_advanced, dynamic_lists = generate_dynamic_form(
        obj_to_edit.class_as_simple_str, obj_to_edit.modeling_obj.__dict__, obj_to_edit.model_web)

    context_data = {
        "object_to_edit": obj_to_edit,
        "form_fields": form_fields,
        "form_fields_advanced": form_fields_advanced,
        "dynamic_form_data": {"dynamic_lists": dynamic_lists},
        "header_name": f"Edit {obj_to_edit.name}"
    }

    storage_form_fields, storage_form_fields_advanced, storage_dynamic_lists = generate_dynamic_form(
        storage_to_edit.class_as_simple_str, storage_to_edit.modeling_obj.__dict__, storage_to_edit.model_web)

    context_data.update({
        "storage_to_edit": storage_to_edit,
        "storage_form_fields": storage_form_fields,
        "storage_form_fields_advanced": storage_form_fields_advanced,
        "storage_dynamic_form_data": {"dynamic_lists": storage_dynamic_lists},
    })

    return context_data


def add_new_object_with_storage(request, model_web: "ModelWeb", storage_type: str):
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
