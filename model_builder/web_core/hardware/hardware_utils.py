from typing import List, TYPE_CHECKING

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ATTRIBUTES_TO_SKIP_IN_FORMS

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


def generate_object_with_storage_creation_context(
    model_web: "ModelWeb", object_type: str, available_efootprint_classes: List, storage_type: str,
    available_storage_classes: List):
    form_sections, dynamic_form_data = generate_object_creation_structure(
        object_type,
        available_efootprint_classes=available_efootprint_classes,
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web,
    )

    storage_form_sections, storage_dynamic_form_data = generate_object_creation_structure(
        storage_type,
        available_efootprint_classes=available_storage_classes,
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
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

    form_fields, form_fields_advanced, dynamic_form_data = generate_object_creation_structure(
        type(obj_to_edit.modeling_obj).__name__,
        available_efootprint_classes=[type(obj_to_edit._modeling_obj)],
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=obj_to_edit.model_web,
        obj_to_edit=obj_to_edit._modeling_obj
    )

    storage_form_fields, storage_form_fields_advanced, storage_dynamic_form_data = generate_object_creation_structure(
        type(storage_to_edit.modeling_obj).__name__,
        available_efootprint_classes=[type(storage_to_edit._modeling_obj)],
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=storage_to_edit.model_web,
        obj_to_edit=storage_to_edit._modeling_obj
    )

    context_data = {
        "object_to_edit": obj_to_edit,
        "form_fields": form_fields,
        "form_fields_advanced": form_fields_advanced,
        "dynamic_form_data": dynamic_form_data,
        "storage_to_edit": storage_to_edit,
        "storage_form_fields": storage_form_fields,
        "storage_form_fields_advanced": storage_form_fields_advanced,
        "storage_dynamic_form_data": storage_dynamic_form_data,
        "object_belongs_to_computable_system": object_belongs_to_computable_system,
        "header_name": f"Edit {obj_to_edit.name}"
    }

    return context_data
