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
    context = FormContextBuilder.build_group_membership_section_context(web_obj)
    section_html = render_to_string(
        "model_builder/side_panels/edit/group_membership_section.html", context)
    return f"<div hx-swap-oob='outerHTML:#group-membership-section-{object_id}'>{section_html}</div>"


def _render_model_canvas(model_web, params) -> str:
    del params
    content = render_to_string(
        "model_builder/components/model_canvas_content.html", {"model_web": model_web})
    return f"<div id='model-canva' class='d-flex flex-row' hx-swap-oob='innerHTML:#model-canva'>{content}</div>"


def _render_results_buttons(model_web, params) -> str:
    del params
    bar_html = render_to_string(
        "model_builder/components/results_bar_button.html", {"model_web": model_web, "oob": True})
    toolbar_html = render_to_string(
        "model_builder/components/show_results_toolbar_button.html", {"model_web": model_web, "oob": True})
    return bar_html + toolbar_html


OOB_REGION_RENDERERS: Dict[str, Callable] = {
    "edge_device_lists": _render_edge_device_lists,
    "group_membership_section": _render_group_membership_section,
    "model_canvas": _render_model_canvas,
    "results_buttons": _render_results_buttons,
}

# Maps a region key to the set of region keys whose DOM targets live entirely inside it.
# When both a container and one of its contained regions are emitted, rendering the
# contained region is redundant (and in practice harmful — duplicated subtrees in the
# swap fragment can trigger stale Bootstrap handlers on detached nodes).
REGION_CONTAINS: Dict[str, set] = {
    "model_canvas": {"edge_device_lists"},
}


def oob_regions_cover_all_cards(regions: Iterable[OobRegion]) -> bool:
    """True when the given regions already re-render every object card on the canvas.

    Callers use this to skip redundant per-card outerHTML swaps they would otherwise
    emit inline (the canvas innerHTML swap covers them).
    """
    return any(getattr(r, "key", None) == "model_canvas" for r in regions)


def render_oob_regions(model_web, regions: Iterable[OobRegion]) -> str:
    regions = list(regions)
    present_keys = {r.key for r in regions}
    contained_keys = {k for key in present_keys for k in REGION_CONTAINS.get(key, set())}
    seen = set()
    html = ""
    for region in regions:
        if region in seen or region.key in contained_keys:
            continue
        seen.add(region)
        html += OOB_REGION_RENDERERS[region.key](model_web, region.params_dict)
    return html
