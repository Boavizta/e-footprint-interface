"""Mutation endpoints for opted-in, non-nested list relationships."""

from efootprint.utils.tools import time_it

from model_builder.adapters.presenters import HtmxPresenter
from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error
from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.oob_region import OobRegion
from model_builder.domain.services.object_linking_service import resolve_reverse_list_attr


def _load_parent_and_child(model_web: ModelWeb, parent_id: str, child_id: str):
    parent_obj = model_web.flat_efootprint_objs_dict.get(parent_id)
    if parent_obj is None:
        raise ValueError(f"Parent {parent_id} not found.")
    child_obj = model_web.flat_efootprint_objs_dict.get(child_id)
    if child_obj is None:
        raise ValueError(f"Object {child_id} not found.")
    return parent_obj, child_obj


def _run_edit_and_present(request, model_web: ModelWeb, parent_obj, attr_name: str, child_obj, link: bool):
    child_ids = [obj.id for obj in getattr(parent_obj, attr_name)]
    if link and child_obj.id not in child_ids:
        child_ids.append(child_obj.id)
    elif not link:
        child_ids = [child_id for child_id in child_ids if child_id != child_obj.id]

    output = EditObjectUseCase(model_web).execute(
        EditObjectInput(
            object_id=parent_obj.id,
            form_data={attr_name: child_ids},
            extra_oob_regions=[OobRegion.make("list_membership_section", object_id=child_obj.id)],
        )
    )
    presenter = HtmxPresenter(request, model_web)
    recompute = bool(request.POST.get("recomputation"))
    return presenter.present_edited_object(output, recompute=recompute)


@render_exception_modal_if_error
@time_it
def unlink_list_entry(request, parent_id, child_id):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    parent_obj, child_obj = _load_parent_and_child(model_web, parent_id, child_id)
    attr_name = resolve_reverse_list_attr(parent_obj, child_obj)
    return _run_edit_and_present(request, model_web, parent_obj, attr_name, child_obj, link=False)


@render_exception_modal_if_error
@time_it
def link_list_entry(request, child_id):
    parent_id = request.POST.get("parent_id")
    if not parent_id:
        raise ValueError("Missing parent_id in request body.")
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    parent_obj, child_obj = _load_parent_and_child(model_web, parent_id, child_id)
    attr_name = resolve_reverse_list_attr(parent_obj, child_obj)
    return _run_edit_and_present(request, model_web, parent_obj, attr_name, child_obj, link=True)
