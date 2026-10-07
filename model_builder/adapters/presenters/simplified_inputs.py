"""Current modeling inputs grouped by their actual type and owner for both focused views."""
from collections import defaultdict
import json

from django.http import HttpResponse
from django.template.loader import render_to_string

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.adapters.forms.form_context_builder import FormContextBuilder
from model_builder.adapters.forms.timeseries_builder_registry import can_edit_timeseries
from model_builder.adapters.label_resolver import LabelResolver
from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider
from model_builder.domain.services.simplified_inputs import FieldAddress, build_catalog, normalize_definition


def input_catalog(model_web):
    return build_catalog(model_web, can_edit_timeseries=can_edit_timeseries)


def present_edited_input(request, model_web, output, catalog, *, recompute=False):
    from model_builder.adapters.presenters import HtmxPresenter
    from model_builder.adapters.presenters.oob_regions import render_oob_regions
    from model_builder.adapters.views.data_status import append_workspace_storage_status
    from model_builder.domain.oob_region import OobRegion

    html = render_input_fields_oob(request, model_web, output.changed_fields, catalog=catalog)
    html += render_oob_regions(model_web, [OobRegion("results_buttons")])
    triggers = {"simplifiedInputSaved": {"notices": output.notices}}
    if recompute:
        html += HtmxPresenter(request, model_web)._recomputation_html()
        triggers["triggerResultRendering"] = ""
    response = HttpResponse(html)
    response["HX-Trigger-After-Settle"] = json.dumps(triggers)
    append_workspace_storage_status(response, request.session)
    return response


def render_input_fields_oob(request, model_web, addresses, *, catalog=None):
    context = build_workspace_context(model_web, catalog=catalog, addresses=addresses)
    return "".join(render_to_string("model_builder/simplified_inputs/field.html", {"field": field, "oob": True},
                                  request=request)
                   for group in context["groups"] for obj in group["objects"] for field in obj["fields"])


def _preview(value):
    if isinstance(value, EmptyExplainableObject):
        return "No value"
    if isinstance(value, ModelingObject):
        return value.name
    if isinstance(value, list):
        return ", ".join(item.name for item in value)
    return str(value)


def build_workspace_context(model_web, *, configure=False, catalog=None, addresses=None):
    catalog = catalog or input_catalog(model_web)
    definition = normalize_definition(model_web.repository.interface_config.get("simplified_inputs"))
    attributes_by_owner = defaultdict(set)
    for address, descriptor in catalog.fields.items():
        setting = definition["fields"].get(address.object_id, {}).get(address.attribute, {})
        if descriptor.eligible and (configure or setting.get("included")) and (addresses is None or address in addresses):
            attributes_by_owner[address.object_id].add(address.attribute)
    unavailable_inputs = []
    if configure:
        for address, descriptor in catalog.fields.items():
            if descriptor.eligible or address not in catalog.dependents:
                continue
            owner = model_web.flat_efootprint_objs_dict[address.object_id]
            label = FieldUIConfigProvider.get_config(address.attribute, owner.efootprint_class.__name__)["label"]
            unavailable_inputs.append(f"{owner.name}: {label} cannot be included because a required input has no supported editor.")
    groups = {}
    form_builder = FormContextBuilder(model_web)
    system_id = model_web.system.efootprint_id
    first = True
    for owner_id, attributes in attributes_by_owner.items():
        web_obj = model_web.get_web_object_from_efootprint_id(owner_id)
        type_name = web_obj.class_as_simple_str
        group = groups.setdefault(type_name, {"object_type": LabelResolver.get_class_label(type_name),
                                             "dom_id": f"si-{system_id}-type-{type_name}", "objects": []})
        fields = []
        for editor in form_builder.build_input_fields(web_obj, attributes):
            if editor.get("hide_field"):
                continue
            attribute = editor["attr_name"]
            address = FieldAddress(owner_id, attribute)
            descriptor = catalog.fields[address]
            dom_id = f"si-{system_id}-{owner_id}-{attribute}"
            editor["web_id"] = f"{dom_id}-value"
            fields.append({"address": address, "dom_id": f"si-{system_id}-{owner_id}-{attribute}",
                           "setting": definition["fields"].get(owner_id, {}).get(
                               attribute, {"included": False, "help": ""}),
                           "editor": editor, "preview": _preview(getattr(web_obj.modeling_obj, attribute)),
                           "controller": descriptor.controller,
                           "dependents": [f"si-{system_id}-{dep.object_id}-{dep.attribute}"
                                          for dep in catalog.dependents.get(address, ())]})
        group["objects"].append({"object_id": owner_id, "dom_id": f"si-{system_id}-object-{owner_id}",
                                 "name": web_obj.name, "fields": fields, "open": first,
                                 "selected_count": sum(field["setting"]["included"] for field in fields)})
        first = False
    selected_input_count = sum(obj["selected_count"] for group in groups.values() for obj in group["objects"])
    return {"system_id": system_id, "slot": getattr(model_web.repository, "slot", 0),
            "configure": configure, "title": definition["title"], "guidance": definition["guidance"],
            "groups": list(groups.values()), "selected_input_count": selected_input_count,
            "unavailable_inputs": unavailable_inputs}
