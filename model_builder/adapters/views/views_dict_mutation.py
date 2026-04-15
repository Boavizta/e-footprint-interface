from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.utils.tools import time_it

from model_builder.adapters.forms.form_data_parser import parse_count
from model_builder.adapters.presenters import HtmxPresenter
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error
from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb


def _load_group_and_key(model_web: ModelWeb, parent_id: str, key_id: str):
    parent_group = model_web.flat_efootprint_objs_dict.get(parent_id)
    if not isinstance(parent_group, EdgeDeviceGroup):
        raise ValueError(f"Parent {parent_id} is not an EdgeDeviceGroup.")
    key_obj = model_web.flat_efootprint_objs_dict.get(key_id)
    if key_obj is None:
        raise ValueError(f"Object {key_id} not found.")
    return parent_group, key_obj


def _resolve_target_dict_attr(key_obj) -> str:
    if isinstance(key_obj, EdgeDeviceGroup):
        return "sub_group_counts"
    if isinstance(key_obj, EdgeDevice):
        return "edge_device_counts"
    raise ValueError(f"Object {key_obj.id} cannot be linked in an edge device group.")


def _serialize_dict_entry(value) -> dict:
    return {"value": value.value.magnitude, "unit": "dimensionless", "label": value.label}


def _build_edit_form_data(parent_group, mutated_attr: str, mutated_key, new_count) -> dict:
    """Build a parsed form_data payload for editing `parent_group` with one dict mutation applied.

    `new_count` is `None` for a removal. Both dict attributes are always serialized so the edit
    use case sees a complete picture of the post-mutation state.
    """
    form_data = {}
    for attr in ("sub_group_counts", "edge_device_counts"):
        current = getattr(parent_group, attr)
        entries = {key.id: _serialize_dict_entry(value) for key, value in current.items()}
        if attr == mutated_attr:
            if new_count is None:
                entries.pop(mutated_key.id, None)
            else:
                existing_label = entries.get(mutated_key.id, {}).get("label", "no label")
                entries[mutated_key.id] = {
                    "value": new_count, "unit": "dimensionless", "label": existing_label}
        form_data[attr] = entries
    return form_data


def _run_edit_and_present(request, model_web: ModelWeb, parent_group, form_data: dict, panel_object_id: str):
    use_case = EditObjectUseCase(model_web)
    output = use_case.execute(EditObjectInput(object_id=parent_group.id, form_data=form_data))
    presenter = HtmxPresenter(request, model_web)
    recompute = bool(request.POST.get("recomputation"))
    response = presenter.present_edited_object(output, recompute=recompute)
    # Preserve the side-panel sync side-effect: if a child object's edit panel is currently
    # open, its group membership section needs to refresh too.
    response.content += presenter._render_group_membership_section_oob_html(panel_object_id).encode("utf-8")
    return response


@render_exception_modal_if_error
@time_it
def update_dict_count(request, parent_id, key_id):
    model_web = ModelWeb(SessionSystemRepository(request.session))
    parent_group, key_obj = _load_group_and_key(model_web, parent_id, key_id)
    attr_name = _resolve_target_dict_attr(key_obj)
    count = parse_count(request.POST.get("count"), error_prefix="Count")
    form_data = _build_edit_form_data(parent_group, attr_name, key_obj, count)
    return _run_edit_and_present(request, model_web, parent_group, form_data, key_id)


@render_exception_modal_if_error
@time_it
def unlink_dict_entry(request, parent_id, key_id):
    model_web = ModelWeb(SessionSystemRepository(request.session))
    parent_group, key_obj = _load_group_and_key(model_web, parent_id, key_id)
    attr_name = _resolve_target_dict_attr(key_obj)
    form_data = _build_edit_form_data(parent_group, attr_name, key_obj, None)
    return _run_edit_and_present(request, model_web, parent_group, form_data, key_id)


@render_exception_modal_if_error
@time_it
def link_dict_entry(request, key_id):
    parent_id = request.POST.get("parent_id")
    if not parent_id:
        raise ValueError("Missing parent_id in request body.")
    model_web = ModelWeb(SessionSystemRepository(request.session))
    parent_group, key_obj = _load_group_and_key(model_web, parent_id, key_id)

    if isinstance(key_obj, EdgeDeviceGroup) and (
            key_obj is parent_group or key_obj in parent_group._find_all_ancestor_groups()):
        raise ValueError("A group cannot be linked to itself or one of its descendants.")

    attr_name = _resolve_target_dict_attr(key_obj)
    form_data = _build_edit_form_data(parent_group, attr_name, key_obj, 1)
    return _run_edit_and_present(request, model_web, parent_group, form_data, key_id)
