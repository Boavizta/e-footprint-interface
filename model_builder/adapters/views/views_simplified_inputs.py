"""Thin focused-view rendering and explicit configuration-save adapters."""
import json

from django.shortcuts import render
from django.http import JsonResponse, Http404
from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.forms.form_context_builder import FormContextBuilder
from model_builder.adapters.forms.simplified_input_context import bookmark_context
from model_builder.domain.services.simplified_inputs import FieldAddress, normalize_definition
from django.views.decorators.http import require_POST

from model_builder.adapters.presenters.simplified_inputs import build_workspace_context, input_catalog, present_edited_input
from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views.exception_handling import render_exception_modal
from model_builder.application.use_cases.simplified_inputs import (
    UpdateSimplifiedDefinitionUseCase, EditSimplifiedInput, EditSimplifiedInputUseCase,
)
from model_builder.domain.entities.web_core.model_web import ModelWeb


def simplified_inputs(request):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    context = build_workspace_context(model_web, configure=request.GET.get("configure") == "1")
    return render(request, "model_builder/simplified_inputs/workspace.html", context)


def simplified_input_field(request, object_id, attribute):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    context = build_workspace_context(model_web, addresses={FieldAddress(object_id, attribute)})
    fields = [field for group in context["groups"] for obj in group["objects"] for field in obj["fields"]]
    if not fields:
        raise Http404("This input is not selected.")
    return render(request, "model_builder/simplified_inputs/field.html", {"field": fields[0]})


def simplified_timeseries_panel(request, object_id, attribute):
    try:
        model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
        catalog = input_catalog(model_web)
        address = FieldAddress(object_id, attribute)
        definition = normalize_definition(model_web.repository.interface_config.get("simplified_inputs"))
        if not definition["fields"].get(object_id, {}).get(attribute, {}).get("included"):
            raise ValueError("This input is not selected.")
        if not catalog.fields[address].eligible:
            raise ValueError("This input has no supported editor.")
        owner = model_web.get_web_object_from_efootprint_id(object_id)
        field = FormContextBuilder(model_web).build_input_fields(owner, {attribute})[0]
        field.pop("bookmark", None)
        field.pop("metadata", None)
        if field["input_type"] not in ("recurrent_timeseries_builder", "hourly_quantities_from_growth"):
            raise ValueError("This input is not an editable timeseries.")
        return render(request, "model_builder/simplified_inputs/timeseries_panel.html", {
            "field": field, "address": address, "header_name": f"{owner.name}: {field['label']}",
            "dynamic_form_data": {},
            "simplified_timeseries": True, "focused_canvas_id": field["web_id"] + "__focused_chart",
        })
    except Exception as error:
        return render_exception_modal(request, error, preserve_panels=True)


@require_POST
def edit_simplified_input(request, object_id, attribute):
    try:
        model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
        catalog = input_catalog(model_web)
        owner = model_web.get_web_object_from_efootprint_id(object_id)
        prefix = f"si-{model_web.system.efootprint_id}-{object_id}-{attribute}-value"
        if request.POST.get("timeseries") == "true":
            prefix = f"{owner.class_as_simple_str}_{attribute}"
        form_data = {}
        for key in request.POST:
            if key == prefix or key.startswith(prefix + "__"):
                values = request.POST.getlist(key)
                form_data[attribute + key[len(prefix):]] = ";".join(values)
        if form_data.get(attribute) == "" and attribute + "__unit" in form_data:
            form_data[attribute] = None
            form_data.pop(attribute + "__unit", None)
        parsed = parse_form_data(form_data, owner.class_as_simple_str)
        output = EditSimplifiedInputUseCase(model_web, catalog).execute(
            EditSimplifiedInput(FieldAddress(object_id, attribute), parsed[attribute]))
        return present_edited_input(request, model_web, output, catalog,
                                    recompute=request.POST.get("recomputation") == "true")
    except Exception as error:
        return render_exception_modal(request, error, preserve_panels=True)


@require_POST
def save_simplified_inputs(request):
    try:
        repository = SessionWorkspaceRepository(request.session).active_repository()
        model_web = ModelWeb(repository)
        catalog = input_catalog(model_web)
        definition = json.loads(request.POST["definition"])
        UpdateSimplifiedDefinitionUseCase(repository, catalog).execute(definition, replace=True)
        return render(request, "model_builder/simplified_inputs/workspace.html",
                      build_workspace_context(model_web, catalog=catalog))
    except Exception as error:
        return render_exception_modal(request, error, preserve_workspace=True)


def simplified_input_bookmark(request, object_id, attribute):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    field = bookmark_context(model_web, FieldAddress(object_id, attribute), suffix="sources")
    if field is None:
        raise Http404("This input cannot be included.")
    return render(request, "model_builder/simplified_inputs/bookmark_controls.html", {"field": field})


@require_POST
def patch_simplified_inputs(request):
    try:
        repository = SessionWorkspaceRepository(request.session).active_repository()
        model_web = ModelWeb(repository)
        catalog = input_catalog(model_web)
        previous = normalize_definition(repository.interface_config.get("simplified_inputs"))
        patch = json.loads(request.POST["patch"])
        output = UpdateSimplifiedDefinitionUseCase(repository, catalog).execute(patch)
        current = normalize_definition(repository.interface_config.get("simplified_inputs"))
        affected = set(output.changed_fields)
        affected.update(FieldAddress(owner, attribute) for owner, attributes in patch.get("fields", {}).items()
                        for attribute in attributes)
        pending = list(affected)
        for address in pending:
            for dependent in catalog.dependents.get(address, []):
                if dependent not in affected:
                    affected.add(dependent)
                    pending.append(dependent)
        fields, inverse = [], {}
        for address in sorted(affected, key=lambda value: (value.object_id, value.attribute)):
            context = bookmark_context(model_web, address, catalog=catalog, definition=current)
            fields.append({"object_id": address.object_id, "attribute": address.attribute,
                           "setting": context["setting"], "required_by": context["required_by"]})
            old = previous["fields"].get(address.object_id, {}).get(address.attribute, {}).get("included", False)
            new = current["fields"].get(address.object_id, {}).get(address.attribute, {}).get("included", False)
            if old != new:
                inverse.setdefault(address.object_id, {})[address.attribute] = {"included": old}
        return JsonResponse({"fields": fields, "inverse": {"fields": inverse}})
    except Exception as error:
        return render_exception_modal(request, error, preserve_workspace=True)
