import random
import string
from datetime import datetime

from django.shortcuts import redirect, render
from django.urls import reverse
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.api_utils.json_to_system import json_to_system
from efootprint import __version__ as efootprint_version
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.tools import time_it

from model_builder.model_web import ModelWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal
from utils import htmx_render

import json
import os
from django.http import HttpResponse
import matplotlib

matplotlib.use('Agg')
DEFAULT_GRAPH_WIDTH = 700


def model_builder_main(request, reboot=False):
    if reboot and reboot != "reboot":
        raise ValueError("reboot must be False or 'reboot'")
    if reboot == "reboot":
        with open(os.path.join("model_builder", "default_system_data.json"), "r") as file:
            system_data = json.load(file)
            request.session["system_data"] = system_data
        return redirect("model-builder")
    if "system_data" not in request.session.keys():
        return redirect("model-builder", reboot="reboot")

    if "efootprint_version" not in request.session["system_data"].keys():
        request.session["system_data"]["efootprint_version"] = "9.1.4"
    system_data_efootprint_version = request.session["system_data"]["efootprint_version"]

    model_web = ModelWeb(request.session)

    if efootprint_version != system_data_efootprint_version:
        logger.info(f"Upgraded system data from version {system_data_efootprint_version} to {efootprint_version}")
        request.session["system_data"]["efootprint_version"] = efootprint_version
        request.session.modified = True

    http_response = htmx_render(
        request, "model_builder/model_builder_main.html", context={"model_web": model_web})

    if request.headers.get("HX-Request") == "true":
        http_response["HX-Trigger-After-Settle"] = "initModelBuilderMain"

    return http_response

def open_import_json_panel(request):
    return render(request, "model_builder/side_panels/import_model.html", context={
              'header_name':'Import a model'})

def download_json(request):
    data = request.session.get('system_data', {})
    json_data = json.dumps(data, indent=4)
    system_name = request.session["system_data"]['System'][
        next(iter(request.session["system_data"]['System'].keys()), None)]['name']
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    response = HttpResponse(json_data, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="{current_date_time}_UTC {system_name}.e-f.json"'
    return response

def upload_json(request):
    import_error_message = ""
    if "import-json-input" in request.FILES:
        try:
            file = request.FILES['import-json-input']
            if file and file.name.lower().endswith('.json'):
                data = json.load(file)
            else:
                import_error_message = "Invalid file format ! Please use a JSON file"
        except ValueError:
            import_error_message = "Invalid JSON data"
        try:
            from model_builder.class_structure import MODELING_OBJECT_CLASSES_DICT
            if "efootprint_version" not in data.keys():
                data["efootprint_version"] = "9.1.4"
            json_to_system(data, launch_system_computations=False, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
            request.session["system_data"] = data
            return redirect("model-builder")
        except Exception as e:
            import_error_message += (
                f"Not a valid e-footprint model ! Please only input files generated by e-footprint "
                f"or the interface. Exception raised: {e}")

    import_error_message += "No file uploaded"

    http_response = render(request, "model_builder/model_builder_main.html",
                  context={"import_error_message": import_error_message})
    http_response["HX-Trigger-After-Swap"] = "alertImportError"

    return http_response

@time_it
def result_chart(request):
    model_web = ModelWeb(request.session)
    exception = None

    if len(model_web.system.servers) == 0:
        exception = ValueError(
            "No impact could be computed because the modeling is incomplete. Please make sure you have at least "
            "one usage pattern linked to a usage journey with at least one step making a request to a server.")
    else:
        usage_journeys_linked_to_usage_pattern_and_without_uj_steps = []
        for usage_journey in model_web.usage_journeys:
            if len(usage_journey.usage_patterns) > 0 and len(usage_journey.uj_steps) == 0:
                usage_journeys_linked_to_usage_pattern_and_without_uj_steps.append(usage_journey)

        if len(usage_journeys_linked_to_usage_pattern_and_without_uj_steps) > 0:
            exception = ValueError(
                f"The following usage journey(s) have no usage journey step:  "
                f"{[uj.name for uj in usage_journeys_linked_to_usage_pattern_and_without_uj_steps]}."
                f" Please add at least one step in each of the above usage journey(s), so that the model can be "
                f"computed.\n\n"
                "(Alternatively, if they are work in progress, you can delete the usage patterns pointing to them: "
                "in that way the usage journeys will be ignored in the computation.)"
            )

    if exception is not None:
        http_response = render_exception_modal(request, exception)
        return http_response

    try:
        model_web.system.after_init()
    except Exception as e:
        return render_exception_modal(request, e)

    http_response = htmx_render(
        request, "model_builder/result_panel.html", context={'model_web': model_web})

    return http_response

def get_calculus_graph(request, cache_key, efootprint_id, attr_name, graph_key):
    content_to_return = request.session[cache_key][f"{efootprint_id}-{attr_name}-{graph_key}"]
    cache_content = request.session[cache_key]
    del cache_content[f"{efootprint_id}-{attr_name}-{graph_key}"]
    request.session[cache_key] = cache_content

    return HttpResponse(content_to_return, content_type="text/html")

def display_calculus_graph(request, efootprint_id, attr_name):
    model_web = ModelWeb(request.session)
    model_web.system.after_init()
    efootprint_object = model_web.get_web_object_from_efootprint_id(efootprint_id)
    graphs = []
    graphs_html_contents = {}
    iframe_height = 95
    cache_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    calculated_attribute_to_display = efootprint_object.__getattr__(attr_name)

    if isinstance(calculated_attribute_to_display, ExplainableObjectDict):
        for key, value in calculated_attribute_to_display.items():
            url = reverse("get-graph", kwargs={
                "cache_key": cache_key,
                "efootprint_id": efootprint_id,
                "attr_name": attr_name,
                "graph_key": key.id
            })
            graphs.append({"url": url, "name": f"{attr_name} - {key.name}"})
            calculus_graph = build_calculus_graph(value)
            calculus_graph.cdn_resources = "remote"
            graphs_html_contents[f"{efootprint_id}-{attr_name}-{key.id}"] = calculus_graph.generate_html()

        if len(list(calculated_attribute_to_display.keys())) > 1:
            iframe_height=45
    else :
        url = reverse("get-graph", kwargs={
            "cache_key": cache_key,
            "efootprint_id": efootprint_id,
            "attr_name": attr_name,
            "graph_key": 'none'
        })
        graphs.append({"url": url, "name": f"{attr_name}"})
        calculus_graph = build_calculus_graph(calculated_attribute_to_display)
        calculus_graph.cdn_resources = "remote"
        graphs_html_contents[f"{efootprint_id}-{attr_name}-none"] = calculus_graph.generate_html()

    request.session[cache_key] = graphs_html_contents

    return render(request, "model_builder/calculus_graphs.html", {
        "graphs": graphs,
        'iframe_height': iframe_height,
    })


