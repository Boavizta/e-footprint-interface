"""Thin focused-view rendering and explicit configuration-save adapters."""
from django.shortcuts import render
from django.views.decorators.http import require_POST

from model_builder.adapters.presenters.simplified_inputs import (
    build_workspace_context, definition_from_form, input_catalog)
from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views.exception_handling import render_exception_modal
from model_builder.application.use_cases.simplified_inputs import UpdateSimplifiedDefinitionUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb


def simplified_inputs(request):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    context = build_workspace_context(model_web, configure=request.GET.get("configure") == "1")
    return render(request, "model_builder/simplified_inputs/workspace.html", context)


@require_POST
def save_simplified_inputs(request):
    try:
        repository = SessionWorkspaceRepository(request.session).active_repository()
        model_web = ModelWeb(repository)
        catalog = input_catalog(model_web)
        UpdateSimplifiedDefinitionUseCase(repository, catalog).execute(definition_from_form(request.POST), replace=True)
        return render(request, "model_builder/simplified_inputs/workspace.html",
                      build_workspace_context(model_web, catalog=catalog))
    except Exception as error:
        return render_exception_modal(request, error, preserve_workspace=True)
