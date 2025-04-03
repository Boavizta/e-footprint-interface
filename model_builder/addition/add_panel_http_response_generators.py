from efootprint.core.all_classes_in_order import SERVER_CLASSES, SERVICE_CLASSES, SERVER_BUILDER_CLASSES
from efootprint.core.hardware.storage import Storage
from django.shortcuts import render
from efootprint.core.usage.job import Job

from model_builder.class_structure import generate_object_creation_structure, efootprint_class_structure
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_web import ModelWeb, default_networks, default_countries, default_devices
from model_builder.object_creation_and_edition_utils import render_exception_modal


def generate_generic_add_panel_http_response(request, object_type: str,  model_web: ModelWeb):
    structure_dict = efootprint_class_structure(object_type, ModelWeb(request.session))
    assert object_type in ["UsageJourney", "UsageJourneyStep"]
    template_name_mapping = {
        "UsageJourney": "usage_journey", "UsageJourneyStep": "usage_journey_step"}
    template_name = template_name_mapping[object_type]
    context_data = {"object_structure": structure_dict,
                    "header_name": "Add new " + template_name.replace("_", " "),
                    "new_object_name": "New " + template_name.replace("_", " ")}
    if request.GET.get('efootprint_id_of_parent_to_link_to'):
        context_data['efootprint_id_of_parent_to_link_to'] = request.GET['efootprint_id_of_parent_to_link_to']
    if request.GET.get("name"):
        context_data["new_object_name"] = request.GET["name"]

    context_data["obj_type"] = object_type
    context_data["next_efootprint_object_rank"] = len(model_web.__getattribute__(f"{template_name}s")) + 1

    return render(request, f"model_builder/side_panels/{template_name}_add.html", context=context_data)


def generate_server_add_panel_http_response(request, model_web: ModelWeb):
    form_sections, dynamic_form_data = generate_object_creation_structure(
        SERVER_CLASSES + SERVER_BUILDER_CLASSES, "Server type", ["fixed_nb_of_instances"])

    storage_form_sections, storage_dynamic_form_data = generate_object_creation_structure(
        [Storage], "Storage type", ["fixed_nb_of_instances"])

    http_response = render(request, f"model_builder/side_panels/server/server_add.html",
                           context={
                               'form_sections': form_sections,
                               "dynamic_form_data": dynamic_form_data,
                               "storage_form_sections": storage_form_sections,
                               "storage_dynamic_form_data": storage_dynamic_form_data,
                               "obj_type": "server",
                               "storage_obj_type": "storage",
                               "header_name": "Add new server",
                               "next_efootprint_object_rank": len(model_web.servers) + 1,
                               "storage_next_efootprint_object_rank": len(model_web.servers) + 1
                           })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_service_add_panel_http_response(request, model_web: ModelWeb):
    server_efootprint_id = request.GET.get('efootprint_id_of_parent_to_link_to')
    server = model_web.get_web_object_from_efootprint_id(server_efootprint_id)

    installable_services = server.installable_services()
    services_dict, dynamic_form_data = generate_object_creation_structure(
        installable_services, "Services available for this server", ["gpu_latency_alpha", "gpu_latency_beta"])

    http_response = render(
        request, "model_builder/side_panels/service_add.html", {
            "server_id": server_efootprint_id,
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "obj_type": "service",
            "header_name": "Add new service",
            "next_efootprint_object_rank": len(model_web.services) + 1
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

    form_sections, dynamic_form_data = generate_object_creation_structure(list(available_job_classes), "Job type")
    additional_item = {
        "category": "job_creation_helper",
        "header": "Job creation helper",
        "class": "",
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
            "input": "service",
            "filter_by": "server",
            "list_value": {
                server.efootprint_id:
                    [{"label": "direct call to server", "value": "direct_server_call"}]
                    + [{"label": service.name, "value": service.efootprint_id}
                       for service in server.installed_services] for server in servers
            }
        },
        {
            "input": "type_object_available",
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
            "next_efootprint_object_rank": len(model_web.jobs) + 1
        })
    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def generate_usage_pattern_add_panel_http_response(request, model_web: ModelWeb):
    usage_journeys = [{'efootprint_id': uj.efootprint_id, 'name': uj.name} for uj in model_web.usage_journeys]
    if len(usage_journeys) == 0:
        error = PermissionError("You need to have created at least one usage journey to create a usage pattern.")
        return render_exception_modal(request, error)

    networks = [{"efootprint_id": network["id"], "name": network["name"]} for network in default_networks().values()]
    countries = [{"efootprint_id": country["id"], "name": country["name"]} for country in default_countries().values()]
    devices = [{"efootprint_id": device["id"], "name": device["name"]} for device in default_devices().values()]

    modeling_obj_attributes = [
        {"attr_name": "devices", "existing_objects": devices, "selected_efootprint_id": devices[0]["efootprint_id"]},
        {"attr_name": "network", "existing_objects": networks, "selected_efootprint_id": networks[0]["efootprint_id"]},
        {"attr_name": "country", "existing_objects": countries,
         "selected_efootprint_id": countries[0]["efootprint_id"]},
        {"attr_name": "usage_journey", "existing_objects": usage_journeys,
         "selected_efootprint_id": usage_journeys[0]["efootprint_id"]},
    ]

    form_sections, dynamic_form_data = generate_object_creation_structure([UsagePatternFromForm], "Usage pattern")

    dynamic_lists = dynamic_form_data["dynamic_lists"]
    dynamic_lists[0]["list_value"] = {
        key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in value]
        for key, value in dynamic_lists[0]["list_value"].items()
    }

    http_response = render(
        request, "model_builder/side_panels/usage_pattern/usage_pattern_add.html", {
            "modeling_obj_attributes": modeling_obj_attributes,
            "usage_pattern_input_values": UsagePatternFromForm.default_values(),
            "dynamic_form_data": {"dynamic_selects": dynamic_lists},
            'header_name': "Add new usage pattern",
            'obj_type': "Usage pattern",
            "next_efootprint_object_rank": len(model_web.usage_patterns) + 1
        })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response
