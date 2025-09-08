from copy import deepcopy
from typing import List

from efootprint.builders.services.generative_ai_ecologits import GenAIModel
from efootprint.core.all_classes_in_order import SERVICE_CLASSES
from efootprint.core.hardware.gpu_server import GPUServer
from django.shortcuts import render
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.job import Job, GPUJob

from model_builder.class_structure import generate_object_creation_structure, MODELING_OBJECT_CLASSES_DICT, \
    FORM_TYPE_OBJECT
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_web import ModelWeb, ATTRIBUTES_TO_SKIP_IN_FORMS
from model_builder.object_creation_and_edition_utils import render_exception_modal


def generate_generic_add_panel_http_response(request, efootprint_class_str: str,  model_web: ModelWeb):
    efootprint_class = MODELING_OBJECT_CLASSES_DICT[efootprint_class_str]
    form_sections, dynamic_form_data = generate_object_creation_structure(
        efootprint_class_str,
        available_efootprint_classes=[efootprint_class],
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web
    )
    context_data = {"form_sections": form_sections,
                    "header_name": "Add new " + FORM_TYPE_OBJECT[efootprint_class_str]["label"].lower(),
                    "object_type": efootprint_class_str,
                    "obj_formatting_data": FORM_TYPE_OBJECT[efootprint_class_str],}
    if request.GET.get("efootprint_id_of_parent_to_link_to"):
        context_data["efootprint_id_of_parent_to_link_to"] = request.GET["efootprint_id_of_parent_to_link_to"]

    http_response = render(request, f"model_builder/side_panels/add/add_panel__generic.html", context=context_data)

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_object_with_storage_add_panel_http_response(
    request, model_web: ModelWeb, object_type: str, available_efootprint_classes: List,
    storage_type: str, available_storage_classes: List):
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

    http_response = render(request, f"model_builder/side_panels/server/server_add.html",
                           context={
                               "object_type": object_type,
                               "form_sections": form_sections,
                               "dynamic_form_data": dynamic_form_data,
                               "storage_form_sections": storage_form_sections,
                               "storage_dynamic_form_data": storage_dynamic_form_data,
                               "header_name": f"Add new {FORM_TYPE_OBJECT[object_type]['label'].lower()}",
                           })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_service_add_panel_http_response(request, model_web: ModelWeb):
    server_efootprint_id = request.GET.get("efootprint_id_of_parent_to_link_to")
    server = model_web.get_web_object_from_efootprint_id(server_efootprint_id)

    installable_services = server.installable_services()
    services_dict, dynamic_form_data = generate_object_creation_structure(
        "Service",
        available_efootprint_classes=installable_services,
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web,
    )

    http_response = render(
        request, "model_builder/side_panels/add/add_panel__generic.html", {
            "server": server,
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "Service",
            "efootprint_id_of_parent_to_link_to": server.efootprint_id,
            "obj_formatting_data": FORM_TYPE_OBJECT["Service"],
            "header_name": "Add new service",
        })

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


def generate_job_add_panel_http_response(request, model_web: ModelWeb):
    servers = model_web.servers
    if len(servers) == 0:
        exception = ValueError("Please go to the infrastructure section and create a server before adding a job")
        return render_exception_modal(request, exception)

    available_job_classes = {Job, GPUJob}
    for service in SERVICE_CLASSES:
        if service.__name__ in model_web.response_objs:
            available_job_classes.update(service.compatible_jobs())

    form_sections, dynamic_form_data = generate_object_creation_structure(
        "Job",
        available_efootprint_classes=list(available_job_classes),
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web,
    )
    additional_item = {
        "category": "job_creation_helper",
        "header": "Job creation helper",
        "fields": [
            {
                "input_type": "select-object",
                "web_id": "server",
                "name": "Server",
                "options": [
                    {"label": server.name, "value": server.efootprint_id} for server in servers],
                "label": "Choose a server",
            },
            {
                "input_type": "select-object",
                "web_id": "service",
                "name": "Service used",
                "options": None,
                "label": "Service used",
            },
        ]
    }
    form_sections = [additional_item] + form_sections

    possible_job_types_per_service = {
        "direct_server_call": [{"label": "Manually defined job", "value": "Job"}],
        "direct_server_call_gpu": [{"label": "Manually defined GPU job", "value": "GPUJob"}]
    }
    possible_job_types_per_service.update({
        service.efootprint_id: [
            {"label": FORM_TYPE_OBJECT[job.__name__]["label"], "value": job.__name__} for job in
            service.compatible_jobs()]
        for service in model_web.services}
    )
    dynamic_form_data["dynamic_selects"] = [
        {
            "input_id": "service",
            "filter_by": "server",
            "list_value": {
                server.efootprint_id:
                    [{"label": service.name, "value": service.efootprint_id}
                       for service in server.installed_services]
                + [{"label": f"direct call to{' GPU' if isinstance(server.modeling_obj, GPUServer) else ''} server",
                    "value": f"direct_server_call{'_gpu' if isinstance(server.modeling_obj, GPUServer) else ''}"}]
                for server in servers
            }
        },
        {
            "input_id": "type_object_available",
            "filter_by": "service",
            "list_value": possible_job_types_per_service
        }]

    http_response = render(
        request, "model_builder/side_panels/add/add_panel__generic.html", {
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "Job",
            "obj_formatting_data": FORM_TYPE_OBJECT["Job"],
            "efootprint_id_of_parent_to_link_to": request.GET.get("efootprint_id_of_parent_to_link_to"),
            "header_name": "Add new job",
        })
    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_usage_pattern_add_panel_http_response(request, model_web: ModelWeb):
    if len(model_web.usage_journeys) == 0:
        error = PermissionError("You need to have created at least one usage journey to create a usage pattern.")
        return render_exception_modal(request, error)
    form_sections, dynamic_form_data = generate_object_creation_structure(
        "UsagePatternFromForm",
        available_efootprint_classes=[UsagePatternFromForm],
        attributes_to_skip=["start_date", "modeling_duration_value", "modeling_duration_unit",
                            "initial_usage_journey_volume", "initial_usage_journey_volume_timespan",
                            "net_growth_rate_in_percentage", "net_growth_rate_timespan"],
        model_web=model_web
    )

    # Turn dynamic list into dynamic select for conditional values
    dynamic_list_options = dynamic_form_data["dynamic_lists"][0]["List_value"]
    dynamic_select = {
        "input_id": "net_growth_rate_timespan",
        "filter_by": "initial_usage_journey_volume_timespan",
        "list_value": {
            key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in value]
            for key, value in dynamic_list_options.items()
        }
    }
    usage_pattern_input_values = deepcopy(UsagePatternFromForm.default_values)
    usage_pattern_input_values["initial_usage_journey_volume"] = None
    http_response = render(
        request, "model_builder/side_panels/usage_pattern/usage_pattern_add.html", {
            "form_fields": form_sections[1]["fields"],
            "usage_pattern_input_values": usage_pattern_input_values,
            "dynamic_form_data": {"dynamic_selects": [dynamic_select]},
            "header_name": "Add new usage pattern",
            "object_type": "UsagePatternFromForm",
            "obj_label": FORM_TYPE_OBJECT["UsagePatternFromForm"]["label"],
        })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_edge_usage_journey_add_panel_http_response(request, model_web: ModelWeb):
    edge_devices_that_are_not_already_linked = [edge_device for edge_device in model_web.edge_devices
                                                if edge_device.edge_usage_journey is None]
    if len(edge_devices_that_are_not_already_linked) == 0:
        error = PermissionError(
            "You need to have at least one edge device not already linked to an edge usage journey to create a "
            "new edge usage journey.")
        return render_exception_modal(request, error)

    efootprint_class_str = "EdgeUsageJourney"
    form_sections, dynamic_form_data = generate_object_creation_structure(
        efootprint_class_str,
        available_efootprint_classes=[EdgeUsageJourney],
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web
    )

    # Enforce constraint to only be able to select edge devices that are not already linked to another edge UJ.
    edge_usage_journey_creation_data = form_sections[1]
    for field in edge_usage_journey_creation_data["fields"]:
        if field["attr_name"] == "edge_device":
            selection_options = edge_devices_that_are_not_already_linked
            selected = selection_options[0]
            field.update({
                "selected": selected.efootprint_id,
                "options": [
                    {"label": attr_value.name, "value": attr_value.efootprint_id} for attr_value in selection_options]
            })
            break

    context_data = {"form_sections": form_sections,
                    "header_name": "Add new " + FORM_TYPE_OBJECT[efootprint_class_str]["label"].lower(),
                    "object_type": efootprint_class_str,
                    "obj_formatting_data": FORM_TYPE_OBJECT[efootprint_class_str]["label"], }

    http_response = render(request, f"model_builder/side_panels/add/add_panel__generic.html", context=context_data)

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response
