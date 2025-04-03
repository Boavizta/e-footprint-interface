import json
from urllib.parse import urlencode

from django.http import QueryDict
from efootprint.core.all_classes_in_order import SERVER_CLASSES, SERVICE_CLASSES, SERVER_BUILDER_CLASSES
from efootprint.core.hardware.storage import Storage
from django.shortcuts import render
from efootprint.core.usage.job import Job

from model_builder.class_structure import generate_object_creation_structure, efootprint_class_structure
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.model_web import ModelWeb, default_networks, default_countries, default_devices
from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data, render_exception_modal
from model_builder.edition.views_edition import edit_object


def open_create_object_panel(request, object_type):
    model_web = ModelWeb(request.session)
    new_object_structure = efootprint_class_structure(object_type, ModelWeb(request.session))
    assert object_type in ["UsageJourney", "UsageJourneyStep"]
    template_name_mapping = {
        "UsageJourney": "usage_journey", "UsageJourneyStep": "usage_journey_step"}
    template_name = template_name_mapping[object_type]
    context_data = {"object_structure": new_object_structure,
                    "header_name": "Add new " +  template_name.replace("_", " "),
                    "new_object_name": "New " + template_name.replace("_", " ")}
    if request.GET.get('efootprint_id_of_parent_to_link_to'):
        context_data['efootprint_id_of_parent_to_link_to'] = request.GET['efootprint_id_of_parent_to_link_to']
    if request.GET.get("name"):
        context_data["new_object_name"] = request.GET["name"]

    context_data["obj_type"] = object_type
    context_data["next_efootprint_object_rank"] = len(model_web.__getattribute__(f"{template_name}s")) + 1

    return render(request, f"model_builder/side_panels/{template_name}_add.html", context=context_data)


def open_create_server_panel(request):
    model_web = ModelWeb(request.session)
    structure_dict, dynamic_form_data = generate_object_creation_structure(
        SERVER_CLASSES + SERVER_BUILDER_CLASSES, "Server type", ["fixed_nb_of_instances"])

    storage_structure_dict, storage_dynamic_form_data = generate_object_creation_structure(
        [Storage], "Storage type", ["fixed_nb_of_instances"])


    http_response = render(request, f"model_builder/side_panels/server/server_add.html",
                context={
                    'structure_dict': structure_dict,
                    "dynamic_form_data": dynamic_form_data,
                    "storage_structure_dict": storage_structure_dict,
                    "storage_dynamic_form_data": storage_dynamic_form_data,
                    "obj_type": "server",
                    "storage_obj_type": "storage",
                    "header_name": "Add new server",
                    "next_efootprint_object_rank": len(model_web.servers) + 1,
                    "storage_next_efootprint_object_rank": len(model_web.servers) + 1
                })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response


def open_create_service_panel(request, server_efootprint_id):
    model_web = ModelWeb(request.session)
    server = model_web.get_web_object_from_efootprint_id(server_efootprint_id)

    installable_services = server.installable_services()
    services_dict, dynamic_form_data = generate_object_creation_structure(
        installable_services, "Services available for this server", ["gpu_latency_alpha", "gpu_latency_beta"])

    http_response = render(
        request, "model_builder/side_panels/service_add.html", {
            "server_id": server_efootprint_id,
            "structure_dict": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "obj_type": "service",
            "header_name": "Add new service",
            "next_efootprint_object_rank": len(model_web.services) + 1
        })

    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response

def open_create_job_panel(request):
    model_web = ModelWeb(request.session)
    servers = model_web.servers

    if len(servers) == 0:
        exception = ValueError("Please create a server before adding a job")
        return render_exception_modal(request, exception)

    available_job_classes = {Job}
    for service in SERVICE_CLASSES:
        if service.__name__ in request.session["system_data"].keys():
            available_job_classes.update(service.compatible_jobs())

    structure_dict, dynamic_form_data = generate_object_creation_structure(list(available_job_classes), "Job type")
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
    structure_dict["items"] = [additional_item] + structure_dict["items"]

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
            "structure_dict": structure_dict,
            "dynamic_form_data": dynamic_form_data,
            "obj_type": "job",
            "efootprint_id_of_parent_to_link_to": request.GET.get('efootprint_id_of_parent_to_link_to'),
            "header_name": "Add new job",
            "next_efootprint_object_rank": len(model_web.jobs) + 1
        })
    http_response["HX-Trigger-After-Swap"] = "initDynamicForm"

    return http_response

def open_create_usage_pattern_panel(request):
    model_web = ModelWeb(request.session)
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

    structure_dict, dynamic_form_data = generate_object_creation_structure([UsagePatternFromForm], "Usage pattern")

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


def add_new_usage_journey(request):
    model_web = ModelWeb(request.session)

    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, 'UsageJourney')
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    response = render(
        request, "model_builder/object_cards/usage_journey_card.html", {"usage_journey": added_obj})
    response["HX-Trigger-After-Swap"] = json.dumps({
        "updateTopParentLines": {"topParentIds": [added_obj.web_id]},
        "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
    })

    return response


def add_new_usage_journey_step(request, usage_journey_efootprint_id):
    model_web = ModelWeb(request.session)
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, 'UsageJourneyStep')
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    usage_journey_to_edit = model_web.get_web_object_from_efootprint_id(usage_journey_efootprint_id)
    mutable_post = request.POST.copy()
    mutable_post['name'] = usage_journey_to_edit.name
    usage_journey_step_ids = [uj_step.efootprint_id for uj_step in usage_journey_to_edit.uj_steps]
    usage_journey_step_ids.append(added_obj.efootprint_id)
    mutable_post.setlist('uj_steps', usage_journey_step_ids)
    request.POST = mutable_post

    return edit_object(request, usage_journey_efootprint_id, model_web)


def add_new_server(request):
    model_web = ModelWeb(request.session)
    storage_qd = QueryDict(urlencode(json.loads(request.POST.get('storage', '{}')), doseq=True))

    storage = create_efootprint_obj_from_post_data(storage_qd, model_web, "Storage")
    added_storage = model_web.add_new_efootprint_object_to_system(storage)

    server_dict = json.loads(request.POST.get('server', '{}'))
    server_dict['storage'] = added_storage.efootprint_id
    server_qd = QueryDict(urlencode(server_dict, doseq=True))
    server_type = server_qd.get('type_object_available')

    new_efootprint_obj = create_efootprint_obj_from_post_data(server_qd, model_web, server_type)
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    response = render(
        request, "model_builder/object_cards/server_card.html", {"server": added_obj})

    return response


def add_new_service(request, server_efootprint_id):
    model_web = ModelWeb(request.session)
    mutable_post = request.POST.copy()
    mutable_post['server'] = server_efootprint_id
    try:
        new_efootprint_obj = create_efootprint_obj_from_post_data(
            mutable_post, model_web, request.POST.get('type_object_available'))

        efootprint_server = model_web.get_web_object_from_efootprint_id(server_efootprint_id).modeling_obj
        efootprint_server.compute_calculated_attributes()

        added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

        response = render(request, "model_builder/object_cards/service_card.html",
                          context={"service": added_obj})

        return response

    except Exception as e:
        return render_exception_modal(request, e)


def add_new_job(request, usage_journey_step_efootprint_id):
    model_web = ModelWeb(request.session)
    usage_journey_step_to_edit = model_web.get_web_object_from_efootprint_id(usage_journey_step_efootprint_id)

    try:
        new_efootprint_obj = create_efootprint_obj_from_post_data(
            request.POST, model_web, request.POST.get('type_object_available'))
    except Exception as e:
        return render_exception_modal(request, e)

    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    mutable_post = request.POST.copy()
    mutable_post['name'] = usage_journey_step_to_edit.name
    mutable_post['user_time_spent'] = usage_journey_step_to_edit.user_time_spent.rounded_magnitude
    job_ids = [job.efootprint_id for job in usage_journey_step_to_edit.jobs]
    job_ids.append(added_obj.efootprint_id)
    mutable_post.setlist('jobs', job_ids)
    request.POST = mutable_post

    return edit_object(request, usage_journey_step_efootprint_id, model_web)


def add_new_usage_pattern(request):
    model_web = ModelWeb(request.session)
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, 'UsagePatternFromForm')
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
    new_efootprint_obj.to_json()
    system_id = next(iter(request.session["system_data"]["System"].keys()))
    request.session["system_data"]["System"][system_id]["usage_patterns"].append(new_efootprint_obj.id)
    request.session.modified = True

    response = render(
        request, "model_builder/object_cards/usage_pattern_card.html", {"usage_pattern": added_obj})

    response["HX-Trigger-After-Swap"] = json.dumps({
        "updateTopParentLines": {"topParentIds": [added_obj.web_id]},
        "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
    })

    return response
