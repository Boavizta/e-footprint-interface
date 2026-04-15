"""Renderer registry for `OobRegion` descriptors emitted by domain hooks.

Each renderer takes `(model_web, params_dict)` and returns an HTML string containing one
or more `hx-swap-oob` elements. `render_oob_regions` deduplicates and concatenates them.
"""
from typing import Callable, Dict, Iterable

from django.template.loader import render_to_string

from model_builder.domain.oob_region import OobRegion


def _render_edge_device_lists(model_web, params) -> str:
    del params
    classes = "list-group d-flex flew-column w-75 ms-25"
    groups_html = render_to_string(
        "model_builder/object_cards/partials/root_edge_device_groups_list.html",
        {"model_web": model_web},
    )
    devices_html = render_to_string(
        "model_builder/object_cards/partials/ungrouped_edge_devices_list.html",
        {"model_web": model_web},
    )
    return (
        f"<div id='edge-device-groups-list' class='{classes}' "
        f"hx-swap-oob='outerHTML:#edge-device-groups-list'>{groups_html}</div>"
        f"<div id='edge-devices-list' class='{classes}' "
        f"hx-swap-oob='outerHTML:#edge-devices-list'>{devices_html}</div>"
    )


def _render_group_membership_section(model_web, params) -> str:
    from model_builder.adapters.forms.form_context_builder import FormContextBuilder

    object_id = params["object_id"]
    web_obj = model_web.get_web_object_from_efootprint_id(object_id)
    context = {"object_to_edit": web_obj, **web_obj.get_edition_context_overrides()}
    if context.get("group_memberships"):
        context["group_memberships"] = FormContextBuilder.hydrate_group_memberships(
            context["group_memberships"])
    section_html = render_to_string(
        "model_builder/side_panels/edit/group_membership_section.html", context)
    return f"<div hx-swap-oob='outerHTML:#group-membership-section-{object_id}'>{section_html}</div>"


OOB_REGION_RENDERERS: Dict[str, Callable] = {
    "edge_device_lists": _render_edge_device_lists,
    "group_membership_section": _render_group_membership_section,
}


def render_oob_regions(model_web, regions: Iterable[OobRegion]) -> str:
    seen = set()
    html = ""
    for region in regions:
        if region in seen:
            continue
        seen.add(region)
        html += OOB_REGION_RENDERERS[region.key](model_web, region.params_dict)
    return html
