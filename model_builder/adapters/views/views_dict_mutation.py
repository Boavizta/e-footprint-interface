from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.utils.tools import time_it

from model_builder.adapters.presenters import HtmxPresenter
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error
from model_builder.domain.entities.web_core.model_web import ModelWeb


def _get_group_dict_and_key(model_web: ModelWeb, parent_id: str, key_id: str):
    parent_group = model_web.get_efootprint_object_from_efootprint_id(parent_id, "EdgeDeviceGroup")
    if not isinstance(parent_group, EdgeDeviceGroup):
        raise ValueError(f"Parent {parent_id} is not an EdgeDeviceGroup.")

    key_obj = model_web.flat_efootprint_objs_dict[key_id]
    if isinstance(key_obj, EdgeDeviceGroup):
        return parent_group, parent_group.sub_group_counts, key_obj
    if isinstance(key_obj, EdgeDevice):
        return parent_group, parent_group.edge_device_counts, key_obj
    raise ValueError(f"Object {key_id} cannot be linked in an edge device group.")


def _parse_count(raw_count: str) -> int:
    try:
        count = int(raw_count)
    except (TypeError, ValueError) as exc:
        raise ValueError("Count must be an integer.") from exc
    if count < 1:
        raise ValueError("Count must be at least 1.")
    return count


def _persist_and_present(request, model_web: ModelWeb, panel_object_id: str):
    model_web.persist_to_cache()
    recompute = bool(request.POST.get("recomputation"))
    return HtmxPresenter(request, model_web).present_dict_mutation(
        recompute=recompute, panel_object_id=panel_object_id)


@render_exception_modal_if_error
@time_it
def update_dict_count(request, parent_id, key_id):
    model_web = ModelWeb(SessionSystemRepository(request.session))
    _parent_group, target_dict, key_obj = _get_group_dict_and_key(model_web, parent_id, key_id)
    target_dict[key_obj] = SourceValue(_parse_count(request.POST.get("count")) * u.dimensionless)
    return _persist_and_present(request, model_web, panel_object_id=key_id)


@render_exception_modal_if_error
@time_it
def unlink_dict_entry(request, parent_id, key_id):
    model_web = ModelWeb(SessionSystemRepository(request.session))
    _parent_group, target_dict, key_obj = _get_group_dict_and_key(model_web, parent_id, key_id)
    del target_dict[key_obj]
    return _persist_and_present(request, model_web, panel_object_id=key_id)


@render_exception_modal_if_error
@time_it
def link_dict_entry(request, key_id):
    parent_id = request.POST.get("parent_id")
    if not parent_id:
        raise ValueError("Missing parent_id in request body.")
    model_web = ModelWeb(SessionSystemRepository(request.session))
    parent_group, target_dict, key_obj = _get_group_dict_and_key(model_web, parent_id, key_id)

    if isinstance(key_obj, EdgeDeviceGroup) and (key_obj is parent_group or key_obj in parent_group._find_all_ancestor_groups()):
        raise ValueError("A group cannot be linked to itself or one of its descendants.")

    target_dict[key_obj] = SourceValue(1 * u.dimensionless)
    return _persist_and_present(request, model_web, panel_object_id=key_id)
