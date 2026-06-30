from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.utils.tools import time_it

from model_builder.adapters.forms.form_data_parser import parse_count
from model_builder.adapters.presenters import HtmxPresenter
from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error
from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.oob_region import OobRegion
from model_builder.domain.services.object_linking_service import (
    dict_attr_names_for_class, resolve_dict_attr, serialize_weighted_dict_entry)


def _load_parent_and_key(model_web: ModelWeb, parent_id: str, key_id: str):
    parent_obj = model_web.flat_efootprint_objs_dict.get(parent_id)
    if parent_obj is None:
        raise ValueError(f"Parent {parent_id} not found.")
    key_obj = model_web.flat_efootprint_objs_dict.get(key_id)
    if key_obj is None:
        raise ValueError(f"Object {key_id} not found.")
    return parent_obj, key_obj


def _build_edit_form_data(parent_obj, mutated_attr: str, mutated_key, new_count) -> dict:
    """Build a parsed form_data payload for editing `parent_obj` with one dict mutation applied.

    `new_count` is `None` for a removal. All dict attributes of the parent are serialized so the
    edit use case sees a complete picture of the post-mutation state; untouched entries keep their
    weights, labels and sources.
    """
    form_data = {}
    for attr in dict_attr_names_for_class(type(parent_obj)):
        current = getattr(parent_obj, attr)
        entries = {key.id: serialize_weighted_dict_entry(value) for key, value in current.items()}
        if attr == mutated_attr:
            if new_count is None:
                entries.pop(mutated_key.id, None)
            else:
                label = entries.get(mutated_key.id, {}).get("label") or type(parent_obj).weight_labels[attr]
                entries[mutated_key.id] = {"value": new_count, "unit": "dimensionless", "label": label}
        form_data[attr] = entries
    return form_data


def _run_edit_and_present(request, model_web: ModelWeb, parent_obj, form_data: dict, panel_object_id: str,
                          refresh_cards: bool = True):
    use_case = EditObjectUseCase(model_web)
    # Preserve the side-panel sync side-effect: if a child object's edit panel is currently
    # open, its membership section needs to refresh too.
    extra_oob_regions = [OobRegion.make("dict_membership_section", object_id=panel_object_id)]
    output = use_case.execute(EditObjectInput(
        object_id=parent_obj.id, form_data=form_data, extra_oob_regions=extra_oob_regions,
        refresh_cards=refresh_cards))
    presenter = HtmxPresenter(request, model_web)
    recompute = bool(request.POST.get("recomputation"))
    return presenter.present_edited_object(output, recompute=recompute)


@render_exception_modal_if_error
@time_it
def update_dict_count(request, parent_id, key_id):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    parent_obj, key_obj = _load_parent_and_key(model_web, parent_id, key_id)
    attr_name = resolve_dict_attr(parent_obj, key_obj)
    count = parse_count(request.POST.get("count"), error_prefix="Count")
    form_data = _build_edit_form_data(parent_obj, attr_name, key_obj, count)
    # A magnitude-only edit is already reflected in the DOM (the user typed it), so don't swap the
    # parent card back — that would clobber a sibling count input being edited within the round-trip.
    # The 0-count dimming class is toggled client-side by inline_count.html; a count of 0 that also
    # flips a creation constraint still repaints via the independent model_canvas OOB region.
    return _run_edit_and_present(request, model_web, parent_obj, form_data, key_id, refresh_cards=False)


@render_exception_modal_if_error
@time_it
def unlink_dict_entry(request, parent_id, key_id):
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    parent_obj, key_obj = _load_parent_and_key(model_web, parent_id, key_id)
    attr_name = resolve_dict_attr(parent_obj, key_obj)
    form_data = _build_edit_form_data(parent_obj, attr_name, key_obj, None)
    return _run_edit_and_present(request, model_web, parent_obj, form_data, key_id)


@render_exception_modal_if_error
@time_it
def link_dict_entry(request, key_id):
    parent_id = request.POST.get("parent_id")
    if not parent_id:
        raise ValueError("Missing parent_id in request body.")
    model_web = ModelWeb(SessionWorkspaceRepository(request.session).active_repository())
    parent_obj, key_obj = _load_parent_and_key(model_web, parent_id, key_id)

    if isinstance(key_obj, EdgeDeviceGroup) and isinstance(parent_obj, EdgeDeviceGroup) and (
            key_obj is parent_obj or key_obj in parent_obj._find_all_ancestor_groups()):
        raise ValueError("A group cannot be linked to itself or one of its descendants.")

    attr_name = resolve_dict_attr(parent_obj, key_obj)
    form_data = _build_edit_form_data(parent_obj, attr_name, key_obj, 1)
    return _run_edit_and_present(request, model_web, parent_obj, form_data, key_id)
