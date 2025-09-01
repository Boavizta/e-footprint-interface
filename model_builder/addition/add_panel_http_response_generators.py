from copy import deepcopy

from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.services.generative_ai_ecologits import GenAIModel
from efootprint.core.all_classes_in_order import SERVICE_CLASSES
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_storage import EdgeStorage
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from django.shortcuts import render
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
    template_name_mapping = {
        "UsageJourney": "usage_journey", "UsageJourneyStep": "usage_journey_step"}
    template_name = template_name_mapping[efootprint_class_str]
    context_data = {"form_fields": form_sections[1]["fields"],
                    "header_name": "Add new " + FORM_TYPE_OBJECT[efootprint_class_str]["label"].lower(),
                    "obj_type": efootprint_class_str,
                    "obj_label": FORM_TYPE_OBJECT[efootprint_class_str]["label"],}
    if request.GET.get("efootprint_id_of_parent_to_link_to"):
        context_data["efootprint_id_of_parent_to_link_to"] = request.GET["efootprint_id_of_parent_to_link_to"]

    http_response = render(request, f"model_builder/side_panels/{template_name}_add.html", context=context_data)

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_server_add_panel_http_response(request, model_web: ModelWeb):
    form_sections, dynamic_form_data = generate_object_creation_structure(
        "ServerBase",
        available_efootprint_classes = [GPUServer, BoaviztaCloudServer, Server],
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web,
    )

    storage_form_sections, storage_dynamic_form_data = generate_object_creation_structure(
        "Storage",
        available_efootprint_classes=[Storage],
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web,
    )

    http_response = render(request, f"model_builder/side_panels/server/server_add.html",
                           context={
                               "object_type": "ServerBase",
                               "form_sections": form_sections,
                               "dynamic_form_data": dynamic_form_data,
                               "storage_form_sections": storage_form_sections,
                               "storage_dynamic_form_data": storage_dynamic_form_data,
                               "header_name": "Add new server",
                           })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_edge_device_add_panel_http_response(request, model_web: ModelWeb):
    form_sections, dynamic_form_data = generate_object_creation_structure(
        "EdgeDevice",
        available_efootprint_classes = [EdgeDevice],
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web,
    )

    storage_form_sections, storage_dynamic_form_data = generate_object_creation_structure(
        "EdgeStorage",
        available_efootprint_classes=[EdgeStorage],
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
        model_web=model_web,
    )

    http_response = render(request, f"model_builder/side_panels/server/server_add.html",
                           context={
                               "object_type": "EdgeDevice",
                               "form_sections": form_sections,
                               "dynamic_form_data": dynamic_form_data,
                               "storage_form_sections": storage_form_sections,
                               "storage_dynamic_form_data": storage_dynamic_form_data,
                               "header_name": "Add new edge device",
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
        request, "model_builder/side_panels/service_add.html", {
            "server": server,
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "obj_type": "service",
            "obj_label": FORM_TYPE_OBJECT["Service"]["label"],
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
        request, "model_builder/side_panels/external_api.html", {
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "obj_type": "service",
            "obj_label": FORM_TYPE_OBJECT["Service"]["label"],
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
        request, "model_builder/side_panels/job_add.html", {
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "obj_type": "job",
            "obj_label": FORM_TYPE_OBJECT["Job"]["label"],
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

    dynamic_select_options = {
        str(conditional_value): [str(possible_value) for possible_value in possible_values]
        for conditional_value, possible_values in
        UsagePatternFromForm.conditional_list_values["net_growth_rate_timespan"]["conditional_list_values"].items()
    }
    dynamic_select = {
        "input_id": "net_growth_rate_timespan",
        "filter_by": "initial_usage_journey_volume_timespan",
        "list_value": {
            key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in value]
            for key, value in dynamic_select_options.items()
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
            "obj_type": "Usage pattern",
            "obj_label": FORM_TYPE_OBJECT["UsagePatternFromForm"]["label"],
        })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response
