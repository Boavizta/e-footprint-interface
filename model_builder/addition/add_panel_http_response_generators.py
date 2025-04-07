from efootprint.core.all_classes_in_order import SERVER_CLASSES, SERVICE_CLASSES, SERVER_BUILDER_CLASSES
from efootprint.core.hardware.storage import Storage
from django.shortcuts import render
from efootprint.core.usage.job import Job

from model_builder.class_structure import generate_object_creation_structure, MODELING_OBJECT_CLASSES_DICT
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_web import ModelWeb, default_networks, default_countries, default_devices, \
    ATTRIBUTES_TO_SKIP_IN_FORMS
from model_builder.object_creation_and_edition_utils import render_exception_modal


def generate_generic_add_panel_http_response(request, object_type: str,  model_web: ModelWeb):
    efootprint_class = MODELING_OBJECT_CLASSES_DICT[object_type]
    form_sections, dynamic_form_data = generate_object_creation_structure(
        [efootprint_class], "", ATTRIBUTES_TO_SKIP_IN_FORMS, model_web)
    template_name_mapping = {
        "UsageJourney": "usage_journey", "UsageJourneyStep": "usage_journey_step"}
    template_name = template_name_mapping[object_type]
    context_data = {"form_fields": form_sections[1]["fields"],
                    "header_name": "Add new " + template_name.replace("_", " "),
                    "obj_type": object_type}
    if request.GET.get('efootprint_id_of_parent_to_link_to'):
        context_data['efootprint_id_of_parent_to_link_to'] = request.GET['efootprint_id_of_parent_to_link_to']

    return render(request, f"model_builder/side_panels/{template_name}_add.html", context=context_data)


def generate_server_add_panel_http_response(request, model_web: ModelWeb):
    form_sections, dynamic_form_data = generate_object_creation_structure(
        SERVER_CLASSES + SERVER_BUILDER_CLASSES, "Server type",
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS + ["storage"], model_web=model_web)

    storage_form_sections, storage_dynamic_form_data = generate_object_creation_structure(
        [Storage], "Storage type", ATTRIBUTES_TO_SKIP_IN_FORMS, model_web)

    http_response = render(request, f"model_builder/side_panels/server/server_add.html",
                           context={
                               'form_sections': form_sections,
                               "dynamic_form_data": dynamic_form_data,
                               "storage_form_sections": storage_form_sections,
                               "storage_dynamic_form_data": storage_dynamic_form_data,
                               "obj_type": "server",
                               "storage_obj_type": "storage",
                               "header_name": "Add new server",
                           })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_service_add_panel_http_response(request, model_web: ModelWeb):
    server_efootprint_id = request.GET.get('efootprint_id_of_parent_to_link_to')
    server = model_web.get_web_object_from_efootprint_id(server_efootprint_id)

    installable_services = server.installable_services()
    services_dict, dynamic_form_data = generate_object_creation_structure(
        installable_services, "Services available for this server", ["gpu_latency_alpha", "gpu_latency_beta", "server"],
        model_web)

    http_response = render(
        request, "model_builder/side_panels/service_add.html", {
            "server_id": server_efootprint_id,
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "obj_type": "service",
            "header_name": "Add new service",
        })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_job_add_panel_http_response(request, model_web: ModelWeb):
    servers = model_web.servers

    if len(servers) == 0:
        exception = ValueError("Please create a server before adding a job")
        return render_exception_modal(request, exception)

    available_job_classes = {Job}
    for service in SERVICE_CLASSES:
        if service.__name__ in request.session["system_data"].keys():
            available_job_classes.update(service.compatible_jobs())

    form_sections, dynamic_form_data = generate_object_creation_structure(
        list(available_job_classes), "Job type",
        attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS + ["server", "service"], model_web=model_web)
    additional_item = {
        "category": "job_creation_helper",
        "header": "Job creation helper",
        "fields": [
            {
                "input_type": "select",
                "id": "server",
                "name": "Server",
                "options": [
                    {'label': server.name, 'value': server.efootprint_id} for server in servers]
            },
            {
                "input_type": "select",
                "id": "service",
                "name": "Service used",
                "options": None
            },
        ]
    }
    form_sections = [additional_item] + form_sections

    possible_job_types_per_service = {"direct_server_call": [{"label": "Manually defined job", "value": "Job"}]}
    possible_job_types_per_service.update({
        service.efootprint_id: [
            {"label": job.__name__, "value": job.__name__} for job in service.compatible_jobs()]
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
                + [{"label": "direct call to server", "value": "direct_server_call"}]
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
            "efootprint_id_of_parent_to_link_to": request.GET.get('efootprint_id_of_parent_to_link_to'),
            "header_name": "Add new job",
        })
    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_usage_pattern_add_panel_http_response(request, model_web: ModelWeb):
    if len(model_web.usage_journeys) == 0:
        error = PermissionError("You need to have created at least one usage journey to create a usage pattern.")
        return render_exception_modal(request, error)

    form_sections, dynamic_form_data = generate_object_creation_structure(
    [UsagePatternFromForm], "Usage pattern",
        attributes_to_skip=["start_date", "modeling_duration_value", "modeling_duration_unit",
                            "initial_usage_journey_volume", "initial_usage_journey_volume_timespan",
                            "net_growth_rate_in_percentage", "net_growth_rate_timespan"], model_web=model_web)

    dynamic_select_options = {
        str(conditional_value): [str(possible_value) for possible_value in possible_values]
        for conditional_value, possible_values in
        UsagePatternFromForm.conditional_list_values()["net_growth_rate_timespan"]["conditional_list_values"].items()
    }
    dynamic_select = {
        "input_id": "net_growth_rate_timespan",
        "filter_by": "initial_usage_journey_volume_timespan",
        "list_value": {
            key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in value]
            for key, value in dynamic_select_options.items()
        }
    }

    for field in form_sections[1]["fields"]:
        if field["name"] == "devices":
            field["input_type"] = "select"

    http_response = render(
        request, "model_builder/side_panels/usage_pattern/usage_pattern_add.html", {
            "form_fields": form_sections[1]["fields"],
            "usage_pattern_input_values": UsagePatternFromForm.default_values(),
            "dynamic_form_data": {"dynamic_selects": [dynamic_select]},
            'header_name': "Add new usage pattern",
            'obj_type': "Usage pattern",
        })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response
