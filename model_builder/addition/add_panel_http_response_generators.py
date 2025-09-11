from efootprint.builders.services.generative_ai_ecologits import GenAIModel
from django.shortcuts import render

from model_builder.class_structure import generate_object_creation_structure, FORM_TYPE_OBJECT
from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
from model_builder.web_core.model_web import ModelWeb
from model_builder.web_abstract_modeling_classes.modeling_object_web import ATTRIBUTES_TO_SKIP_IN_FORMS


def generate_generic_add_panel_http_response(request, efootprint_class_str: str,  model_web: ModelWeb):
    efootprint_class_web = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[efootprint_class_str]
    efootprint_id_of_parent_to_link_to = request.GET.get("efootprint_id_of_parent_to_link_to", None)
    context_data = efootprint_class_web.generate_object_creation_context(model_web, efootprint_id_of_parent_to_link_to)
    if efootprint_id_of_parent_to_link_to:
        context_data["efootprint_id_of_parent_to_link_to"] = efootprint_id_of_parent_to_link_to

    http_response = render(
        request, f"model_builder/side_panels/add/{efootprint_class_web.add_template}", context=context_data)

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_external_api_add_panel_http_response(request, model_web: ModelWeb):
    installable_services = [GenAIModel]
    services_dict, dynamic_form_data = generate_object_creation_structure(
        "Service",
        available_efootprint_classes=installable_services,
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web,
    )

    services_dict[0]["fields"][0]["label"] = "Available services"

    http_response = render(
        request, "model_builder/side_panels/add/add_panel__generic.html", {
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "ExternalApi",
            "obj_formatting_data": FORM_TYPE_OBJECT["ExternalApi"],
            "header_name": "Add new external API",
        })
    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response
