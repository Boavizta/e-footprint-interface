import math
import random
import string
from datetime import datetime
from io import BytesIO
from time import time
import json
import os

import numpy as np
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from openpyxl import Workbook
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes
from efootprint import __version__ as efootprint_version
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.tools import time_it

from model_builder.web_core.model_web_utils import to_rounded_daily_values, reindex_array
from model_builder.web_core.model_web import ModelWeb
from model_builder.web_abstract_modeling_classes.object_linked_to_modeling_obj_web import ObjectLinkedToModelingObjWeb
from model_builder.web_abstract_modeling_classes.explainable_objects_web import ExplainableObjectWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal_if_error
from utils import htmx_render, sanitize_filename, smart_truncate


def model_builder_main(request, reboot=False):
    if reboot and reboot != "reboot":
        raise ValueError("reboot must be False or 'reboot'")
    if reboot == "reboot":
        with open(os.path.join("model_builder", "reference_data", "default_system_data.json"), "r") as file:
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
        # Lines updates are triggered at the after settle element, so might be triggered before initModelBuilderMain
        # and cause an error, unless we remove all lines before.
        http_response["HX-Trigger"] = "removeAllLines"
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
    filename = smart_truncate(filename)
    response["Content-Disposition"] = f"attachment; filename={filename}.e-f.json"
    return response

def upload_json(request):
    start = time()
    import_error_message = ""
    initial_session_data = request.session.get("system_data", None)
    data = None
    
    if "import-json-input" in request.FILES:
        file = request.FILES["import-json-input"]
        try:
            if file and file.name.lower().endswith(".json"):
                data = json.load(file)
                file.close()
            else:
                import_error_message = "Invalid file format ! Please use a JSON file\n"
        except ValueError:
            import_error_message = "Invalid JSON data\n"
        finally:
            if file:
                file.close()
        
        if data and not import_error_message:
            try:
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
                del model_web
                return redirect("model-builder")
            except Exception as e:
                if os.environ.get("RAISE_EXCEPTIONS"):
                    raise e
                import_error_message += (
                    f"Not a valid e-footprint model ! Please only input files generated by e-footprint "
                    f"or the interface. \nException raised: {type(e).__name__}: {e}")

    request.session["system_data"] = initial_session_data
    if initial_session_data:
        model_web = ModelWeb(request.session)
    else:
        request.session["system_data"] = {}
        model_web = None

    context = {"import_error_modal_id": "error-import-modal", "import_error_message": import_error_message}
    if model_web:
        context["model_web"] = model_web
    
    http_response = render(request, "model_builder/model_builder_main.html", context=context)
    http_response["HX-Trigger-After-Swap"] = json.dumps({"openModalDialog": {"modal_id": "error-import-modal"}})

    return http_response

@render_exception_modal_if_error
@time_it
def result_chart(request):
    model_web = ModelWeb(request.session)
    model_web.raise_incomplete_modeling_errors()

    http_response = htmx_render(
        request, "model_builder/result/result_panel.html", context={"model_web": model_web})
    http_response["HX-Trigger-After-Settle"] = "triggerResultRendering"

    return http_response

def get_calculus_graph(request, cache_key):
    content_to_return = request.session.pop(cache_key)
    request.session.modified = True

    return HttpResponse(content_to_return, content_type="text/html")

def display_calculus_graph(request, efootprint_id: str, attr_name: str, id_of_key_in_dict: str=None):
    model_web = ModelWeb(request.session)
    efootprint_object = model_web.get_web_object_from_efootprint_id(efootprint_id)
    iframe_height = 95
    cache_key = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    web_attr = getattr(efootprint_object, attr_name)
    if id_of_key_in_dict is None:
        calculated_attribute = web_attr
    else:
        calculated_attribute = ExplainableObjectWeb(
            web_attr.efootprint_object[
                model_web.get_efootprint_object_from_efootprint_id(
                    id_of_key_in_dict,
                    "object_type unnecessary because the usage pattern necessarily already belongs to the system")],
            model_web)

    calculus_graph = build_calculus_graph(calculated_attribute)
    calculus_graph.cdn_resources = "remote"
    request.session[cache_key] = calculus_graph.generate_html()

    url = reverse("get-graph", kwargs={"cache_key": cache_key})

    return render(request, "model_builder/calculus_graph.html", {
        "graph": {"url": url, "calculated_attribute": calculated_attribute}, "iframe_height": iframe_height
    })


def download_sources(request):
    model_web = ModelWeb(request.session)
    sources = []

    for efootprint_object in model_web.flat_efootprint_objs_dict.values():
        for attr_name, attr_value in get_instance_attributes(efootprint_object, ExplainableQuantity).items():
            source = attr_value.source
            web_efootprint_object = model_web.get_web_object_from_efootprint_id(efootprint_object.id)
            web_attr_value = ObjectLinkedToModelingObjWeb(attr_value, model_web)
            if attr_name in efootprint_object.calculated_attributes:
                source = Source("Computed", "")

            sources.append([
                web_attr_value.attr_name_web,
                web_efootprint_object.name,
                web_efootprint_object.class_label,
                attr_value.value.magnitude,
                str(attr_value.value.units),
                source.name if source else "",
                source.link if source else "",
            ])

    wb = Workbook()
    ws = wb.active
    ws.title = "Sources"

    headers = ["Item name", "Attribute of", "Object type", "Value", "Unit", "Source name", "Source link"]
    ws.append(headers)

    for row in sources:
        ws.append(row)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 30

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    system_name = next(iter(request.session["system_data"]["System"].values()))["name"]
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f"attachment; filename={current_date_time}_UTC {system_name}_sources.xlsx"

    return response

@time_it
def get_explainable_hourly_quantity_chart_and_explanation(
    request, efootprint_id: str, attr_name: str, id_of_key_in_dict: str=None):
    model_web = ModelWeb(request.session)
    edited_web_obj = model_web.get_web_object_from_efootprint_id(efootprint_id)
    web_attr = getattr(edited_web_obj, attr_name)
    if id_of_key_in_dict is None:
        web_ehq = web_attr
    else:
        web_ehq = ExplainableObjectWeb(
            web_attr.efootprint_object[
                model_web.get_efootprint_object_from_efootprint_id(
                    id_of_key_in_dict,
                    "object_type unnecessary because the usage pattern necessarily already belongs to the system")],
            model_web)

    if web_ehq.start_date.hour == 0:
        reindexed_values = web_ehq.value
        start_date_starting_at_midnight = web_ehq.start_date
    else:
        start_date_starting_at_midnight = web_ehq.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        reindexed_values = reindex_array(
            web_ehq, start_date_starting_at_midnight, len(web_ehq.value) + web_ehq.start_date.hour)
    n_days = math.ceil(len(reindexed_values) / 24)
    start = np.datetime64(start_date_starting_at_midnight, "D")
    dates = (start + np.arange(n_days)).astype(str).tolist()
    daily_data = to_rounded_daily_values(reindexed_values)
    data_dict = dict(zip(dates, daily_data))
    literal_formula, ancestors_mapped_to_symbols_list = (
        web_ehq.compute_literal_formula_and_ancestors_mapped_to_symbols_list())

    context = {
        "web_ehq": web_ehq,
        "data_timeseries": data_dict,
        "literal_formula": literal_formula,
        "ancestors_mapped_to_symbols_list": ancestors_mapped_to_symbols_list,
    }

    return render(
        request,
        "model_builder/side_panels/edit/calculated_attributes/calculated_attribute_chart.html", context=context)


def get_calculated_attribute_explanation(request, efootprint_id, attr_name):
    model_web = ModelWeb(request.session)
    explained_obj = getattr(model_web.get_web_object_from_efootprint_id(efootprint_id), attr_name)
    literal_formula, ancestors_mapped_to_symbols_list = (
        explained_obj.compute_literal_formula_and_ancestors_mapped_to_symbols_list())

    return render(
        request,
        "model_builder/side_panels/edit/calculated_attributes/calculated_attribute_explanation.html",
        {
            "literal_formula": literal_formula,
            "ancestors_mapped_to_symbols_list": ancestors_mapped_to_symbols_list,
            "explained_obj": explained_obj
        }
    )
