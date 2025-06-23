import random
import string
from datetime import datetime
from io import BytesIO
from time import time

import pandas as pd
from django.shortcuts import redirect, render
from django.urls import reverse
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes
from efootprint import __version__ as efootprint_version
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.tools import time_it

from model_builder.model_web import ModelWeb
from model_builder.modeling_objects_web import ExplainableObjectWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal_if_error
from utils import htmx_render, sanitize_filename, smart_truncate

import json
import os
from django.http import HttpResponse
import matplotlib

matplotlib.use("Agg")
DEFAULT_GRAPH_WIDTH = 700


def model_builder_main(request, reboot=False):
    if reboot and reboot != "reboot":
        raise ValueError("reboot must be False or 'reboot'")
    if reboot == "reboot":
        with open(os.path.join("model_builder", "default_system_data.json"), "r") as file:
            system_data = json.load(file)
        request.session["system_data"] = system_data
        model_web = ModelWeb(request.session)
        model_web.update_system_data_with_up_to_date_calculated_attributes()

        return redirect("model-builder")
    if "system_data" not in request.session:
        return redirect("model-builder", reboot="reboot")

    if "efootprint_version" not in request.session["system_data"]:
        request.session["system_data"]["efootprint_version"] = "9.1.4"
    system_data_efootprint_version = request.session["system_data"]["efootprint_version"]

    model_web = ModelWeb(request.session)

    if efootprint_version != system_data_efootprint_version:
        logger.info(f"Upgrading system data from version {system_data_efootprint_version} to {efootprint_version}")
        request.session["system_data"]["efootprint_version"] = efootprint_version
        model_web.update_system_data_with_up_to_date_calculated_attributes()
        logger.info("Upgrade successful")

    http_response = htmx_render(
        request, "model_builder/model_builder_main.html", context={"model_web": model_web})

    if request.headers.get("HX-Request") == "true":
        http_response["HX-Trigger-After-Settle"] = "initModelBuilderMain"

    return http_response

def open_import_json_panel(request):
    return render(request, "model_builder/side_panels/import_model.html", context={
              "header_name":"Import a model"})

def download_json(request):
    model_web = ModelWeb(request.session)
    system = model_web.system
    system_data_without_calculated_attributes = model_web.to_json(save_calculated_attributes=False)
    json_data = json.dumps(system_data_without_calculated_attributes, indent=4)
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    response = HttpResponse(json_data, content_type="application/json")
    filename = f"{current_date_time} UTC {system.name}"
    filename = sanitize_filename(filename)
    filename = smart_truncate(filename, max_length=45)
    response["Content-Disposition"] = f"attachment; filename={filename}.e-f.json"
    return response

def upload_json(request):
    start = time()
    import_error_message = ""
    if "import-json-input" in request.FILES:
        try:
            file = request.FILES["import-json-input"]
            if file and file.name.lower().endswith(".json"):
                data = json.load(file)
            else:
                import_error_message = "Invalid file format ! Please use a JSON file"
        except ValueError:
            import_error_message = "Invalid JSON data"
        try:
            from model_builder.class_structure import MODELING_OBJECT_CLASSES_DICT
            if "efootprint_version" not in data.keys():
                data["efootprint_version"] = "9.1.4"
            request.session["system_data"] = data
            model_web = ModelWeb(request.session)
            for uj in model_web.usage_journeys:
                if len(uj.systems) == 0 and getattr(uj, "duration", None) is None:
                    # usage journey is not linked to any system and has no duration so it means it has been saved
                    # without its calculated attributes. This can create a bug in case a uj step is later added to it
                    # before it is linked to a system.
                    request.session["system_data"]["UsageJourney"][uj.id] = uj.to_json(
                        save_calculated_attributes=True)
            model_web.update_system_data_with_up_to_date_calculated_attributes()
            logger.info(f"Importing system from JSON took {round((time() - start), 3)} seconds")
            return redirect("model-builder")
        except Exception as e:
            if os.environ.get("RAISE_EXCEPTIONS"):
                raise e
            import_error_message += (
                f"Not a valid e-footprint model ! Please only input files generated by e-footprint "
                f"or the interface. Exception raised: {e}")

    import_error_message += "No file uploaded"

    http_response = render(request, "model_builder/model_builder_main.html",
                  context={"import_error_message": import_error_message})
    http_response["HX-Trigger-After-Swap"] = "alertImportError"

    return http_response

@render_exception_modal_if_error
@time_it
def result_chart(request):
    model_web = ModelWeb(request.session)
    model_web.raise_incomplete_modeling_errors()

    http_response = htmx_render(
        request, "model_builder/result/result_panel.html", context={"model_web": model_web})

    return http_response

def get_calculus_graph(request, cache_key, efootprint_id, attr_name, graph_key):
    content_to_return = request.session[cache_key][f"{efootprint_id}-{attr_name}-{graph_key}"]
    cache_content = request.session[cache_key]
    del cache_content[f"{efootprint_id}-{attr_name}-{graph_key}"]
    request.session[cache_key] = cache_content

    return HttpResponse(content_to_return, content_type="text/html")

def display_calculus_graph(request, efootprint_id, attr_name):
    model_web = ModelWeb(request.session)
    efootprint_object = model_web.get_web_object_from_efootprint_id(efootprint_id)
    graphs = []
    graphs_html_contents = {}
    iframe_height = 95
    cache_key = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

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
            "graph_key": "none"
        })
        graphs.append({"url": url, "name": f"{attr_name}"})
        calculus_graph = build_calculus_graph(calculated_attribute_to_display)
        calculus_graph.cdn_resources = "remote"
        graphs_html_contents[f"{efootprint_id}-{attr_name}-none"] = calculus_graph.generate_html()

    request.session[cache_key] = graphs_html_contents

    return render(request, "model_builder/calculus_graphs.html", {
        "graphs": graphs,
        "iframe_height": iframe_height,
    })


def download_sources(request):
    model_web = ModelWeb(request.session)
    sources = []

    for efootprint_object in model_web.flat_efootprint_objs_dict.values():
        for attr_name, attr_value in get_instance_attributes(efootprint_object, ExplainableQuantity).items():
            source = attr_value.source
            web_efootprint_object = model_web.get_web_object_from_efootprint_id(efootprint_object.id)
            web_attr_value = ExplainableObjectWeb(attr_value, web_efootprint_object)
            if attr_name in efootprint_object.calculated_attributes:
                source = Source("Computed", "")

            sources.append({
                "Item name": web_attr_value.label,
                "Attribute of": web_efootprint_object.name,
                "Object type": web_efootprint_object.class_label,
                "Value": attr_value.value.magnitude,
                "Unit": str(attr_value.value.units),
                "Source name": source.name if source else "",
                "Source link": source.link if source else "",
            })

    df = pd.DataFrame(sources)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sheet_name = "Sources"
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        for col in worksheet.columns:
            worksheet.column_dimensions[col[0].column_letter].width = 30

    output.seek(0)

    system_name = next(iter(request.session["system_data"]["System"].values()))["name"]
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    response = HttpResponse(output.read(),
                            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f"attachment; filename={current_date_time}_UTC {system_name}_sources.xlsx"

    return response
