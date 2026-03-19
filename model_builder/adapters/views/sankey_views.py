import json

from django.shortcuts import render

from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.utils.impact_repartition.sankey import ImpactRepartitionSankey
from efootprint.utils.tools import display_co2_amount, format_co2_amount

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error
from model_builder.domain.entities.web_core.model_web import ModelWeb

DEFAULT_SKIPPED_CLASSES = [
    "UsagePattern", "EdgeUsagePattern", "JobBase",
    "RecurrentEdgeDeviceNeed", "RecurrentServerNeed", "RecurrentEdgeComponentNeed",
]

EXCLUDABLE_CLASSES = ["Device", "EdgeDevice", "Network", "ServerBase", "ExternalAPI", "Storage", "EdgeStorage"]

SKIPPABLE_CLASSES = [
    "Country", "UsagePattern", "EdgeUsagePattern", "UsageJourney", "EdgeUsageJourney", "EdgeFunction",
    "JobBase", "EdgeDevice", "RecurrentEdgeDeviceNeed", "RecurrentServerNeed", "RecurrentEdgeComponentNeed",
    "Service", "ExternalAPI",
]

_LIFECYCLE_PHASE_MAP = {
    "Manufacturing": LifeCyclePhases.MANUFACTURING,
    "Usage": LifeCyclePhases.USAGE,
}

_SANKEY_NAME_DELIMITER = "\u2063"
_SANKEY_SIDE_PADDING_PX = 30
_SANKEY_RIGHT_PADDING_MIN_PX = 90
_SANKEY_RIGHT_PADDING_MAX_PX = 260
_SANKEY_LABEL_CHAR_WIDTH_PX = 7
_SANKEY_LABEL_BUFFER_PX = 36


def _get_present_classes(model_web: ModelWeb) -> set[str]:
    return set(model_web.response_objs.keys())


def _class_or_subclass_present(candidate_class_name: str, present_class_names: set[str]) -> bool:
    """Check if candidate class or any of its subclasses is present in the system.

    Handles base class names like ServerBase, JobBase matching concrete classes like Server, Job.
    """
    candidate_cls = ALL_EFOOTPRINT_CLASSES_DICT.get(candidate_class_name)
    if candidate_cls is None:
        return candidate_class_name in present_class_names
    return any(
        pname in ALL_EFOOTPRINT_CLASSES_DICT and issubclass(ALL_EFOOTPRINT_CLASSES_DICT[pname], candidate_cls)
        for pname in present_class_names
    )


def _build_chip_list(candidate_classes: list[str], present_classes: set[str], default_active: list[str]) -> list[dict]:
    chips = []
    for cls_name in candidate_classes:
        if not _class_or_subclass_present(cls_name, present_classes):
            continue
        chips.append({
            "class_name": cls_name,
            "label": ClassUIConfigProvider.get_label(cls_name),
            "active": cls_name in default_active,
        })
    return chips


def _estimate_sankey_right_padding(nodes: list[dict]) -> int:
    if not nodes:
        return _SANKEY_SIDE_PADDING_PX

    max_depth = max(node["depth"] for node in nodes)
    longest_right_label_length = max(
        (len(node["label"]) for node in nodes if node["depth"] == max_depth),
        default=0,
    )

    if longest_right_label_length == 0:
        return _SANKEY_SIDE_PADDING_PX

    estimated_padding = longest_right_label_length * _SANKEY_LABEL_CHAR_WIDTH_PX + _SANKEY_LABEL_BUFFER_PX
    return max(_SANKEY_RIGHT_PADDING_MIN_PX, min(_SANKEY_RIGHT_PADDING_MAX_PX, estimated_padding))


def _build_column_headers_context(sankey: ImpactRepartitionSankey) -> list[dict]:
    headers = []
    for info in sorted(sankey.get_column_information(), key=lambda x: x["column_index"]):
        lines = [info["description"]] if info["column_type"] == "manual_split" else [ClassUIConfigProvider.get_label(cn) for cn in info["class_names"]]
        headers.append({"lines": lines, "x_center": info["x_center"]})
    return headers


def _resolve_visible_node_idx(node_idx: int, adjacency: dict[int, list[int]], spacer_nodes: set[int]) -> int:
    current = node_idx
    while current in spacer_nodes:
        neighbors = adjacency.get(current, [])
        if not neighbors:
            break
        current = neighbors[0]
    return current


def _build_node_tooltip(sankey: ImpactRepartitionSankey, node_idx: int) -> str:
    kg = sankey.node_total_kg[node_idx]
    amount_str = display_co2_amount(format_co2_amount(kg))
    pct = (kg / sankey.total_system_kg * 100) if sankey.total_system_kg > 0 else 0
    if node_idx in sankey.aggregated_node_members:
        members_str = "<br>".join(
            f"{label}: {display_co2_amount(format_co2_amount(member_kg))} CO2eq"
            for label, member_kg in sankey.aggregated_node_members[node_idx]
        )
        return f"{sankey.full_node_labels[node_idx]}<br>{amount_str} CO2eq ({pct:.1f}%)<br><br>Aggregated objects:<br>{members_str}"
    return f"{sankey.full_node_labels[node_idx]}<br>{amount_str} CO2eq ({pct:.1f}%)"


def _build_link_tooltip(sankey: ImpactRepartitionSankey, source_idx: int, target_idx: int, value_tonnes: float) -> str:
    kg = value_tonnes * 1000
    amount_str = display_co2_amount(format_co2_amount(kg))
    pct = (kg / sankey.total_system_kg * 100) if sankey.total_system_kg > 0 else 0
    return f"{sankey.full_node_labels[source_idx]} → {sankey.full_node_labels[target_idx]}<br>{amount_str} CO2eq ({pct:.1f}%)"


def _build_sankey_payload(sankey: ImpactRepartitionSankey) -> dict:
    sankey.build()
    node_columns = getattr(sankey, "_node_columns", {})
    spacer_nodes = getattr(sankey, "_spacer_nodes", set())
    category_nodes = getattr(sankey, "_category_node_indices", set())
    leaf_nodes = getattr(sankey, "_leaf_node_indices", set())
    breakdown_nodes = getattr(sankey, "_breakdown_node_indices", set())
    node_colors = sankey._compute_node_colors()

    incoming_by_target = {}
    outgoing_by_source = {}
    for source, target in zip(sankey.link_sources, sankey.link_targets):
        incoming_by_target.setdefault(target, []).append(source)
        outgoing_by_source.setdefault(source, []).append(target)

    visible_columns = [column for node_idx, column in node_columns.items() if node_idx not in spacer_nodes]
    min_column = min(visible_columns) if visible_columns else 0

    nodes_per_column: dict[int, int] = {}
    nodes = []
    for node_idx, label in enumerate(sankey.node_labels):
        if node_idx in spacer_nodes:
            continue
        column = node_columns.get(node_idx, min_column)
        nodes_per_column[column] = nodes_per_column.get(column, 0) + 1
        name_key = f"{label}{_SANKEY_NAME_DELIMITER}{node_idx}"
        nodes.append({
            "key": f"node-{node_idx}",
            "name_key": name_key,
            "label": label,
            "full_name": sankey.full_node_labels[node_idx],
            "value_kg": sankey.node_total_kg[node_idx],
            "value_tonnes": sankey.node_total_kg[node_idx] / 1000,
            "depth": column - min_column,
            "column": column,
            "color": node_colors[node_idx],
            "tooltip_html": _build_node_tooltip(sankey, node_idx),
            "is_aggregated": node_idx in sankey.aggregated_node_members,
            "is_category": node_idx in category_nodes,
            "is_leaf": node_idx in leaf_nodes,
            "is_breakdown": node_idx in breakdown_nodes,
        })

    right_padding_px = _estimate_sankey_right_padding(nodes)

    collapsed_links = {}
    for source, target, value_tonnes in zip(sankey.link_sources, sankey.link_targets, sankey.link_values):
        if source in spacer_nodes:
            continue
        visible_source = _resolve_visible_node_idx(source, incoming_by_target, spacer_nodes)
        visible_target = _resolve_visible_node_idx(target, outgoing_by_source, spacer_nodes)
        if visible_source == visible_target or visible_source in spacer_nodes or visible_target in spacer_nodes:
            continue
        collapsed_links[(visible_source, visible_target)] = collapsed_links.get((visible_source, visible_target), 0.0) + value_tonnes

    links = []
    for (source_idx, target_idx), value_tonnes in sorted(collapsed_links.items()):
        links.append({
            "source_key": f"node-{source_idx}",
            "target_key": f"node-{target_idx}",
            "source_name_key": f"{sankey.node_labels[source_idx]}{_SANKEY_NAME_DELIMITER}{source_idx}",
            "target_name_key": f"{sankey.node_labels[target_idx]}{_SANKEY_NAME_DELIMITER}{target_idx}",
            "value": value_tonnes,
            "value_kg": value_tonnes * 1000,
            "color": node_colors[source_idx].replace("0.8)", "0.35)"),
            "tooltip_html": _build_link_tooltip(sankey, source_idx, target_idx, value_tonnes),
        })

    node_width, node_gap, chart_top, chart_bottom = 20, 20, 10, 30
    max_nodes_per_col = max(nodes_per_column.values()) if nodes_per_column else 1
    recommended_height = max(400, max_nodes_per_col * (node_width + node_gap) + chart_top + chart_bottom)

    return {
        "nodes": nodes,
        "links": links,
        "layout": {
            "left_padding_px": _SANKEY_SIDE_PADDING_PX,
            "right_padding_px": right_padding_px,
            "horizontal_padding_px": _SANKEY_SIDE_PADDING_PX + right_padding_px,
        },
    }, recommended_height


@render_exception_modal_if_error
def sankey_diagram(request):
    card_id = request.POST.get("card_id", "1")
    model_web = ModelWeb(SessionSystemRepository(request.session))
    system = list(model_web.response_objs["System"].values())[0]

    lifecycle_phase_str = request.POST.get("lifecycle_phase_filter", "")
    lifecycle_phase_filter = _LIFECYCLE_PHASE_MAP.get(lifecycle_phase_str)

    aggregation_threshold_percent = float(request.POST.get("aggregation_threshold_percent", "1.0"))
    skip_phase_footprint_split = "phase_split" not in request.POST
    skip_object_category_footprint_split = "category_split" not in request.POST
    skip_object_footprint_split = "object_split" not in request.POST
    excluded_object_types = request.POST.getlist("excluded_types")
    skipped_classes = request.POST.getlist("skipped_classes")
    display_column_headers = "display_column_headers" in request.POST
    node_label_max_length = int(request.POST.get("node_label_max_length", "15"))

    sankey = ImpactRepartitionSankey(
        system,
        aggregation_threshold_percent=aggregation_threshold_percent,
        node_label_max_length=node_label_max_length,
        skipped_impact_repartition_classes=skipped_classes or None,
        skip_phase_footprint_split=skip_phase_footprint_split,
        skip_object_category_footprint_split=skip_object_category_footprint_split,
        skip_object_footprint_split=skip_object_footprint_split,
        excluded_object_types=excluded_object_types or None,
        lifecycle_phase_filter=lifecycle_phase_filter,
        display_column_information=False,
    )
    sankey_payload, sankey_height = _build_sankey_payload(sankey)
    sankey_payload_json = json.dumps(sankey_payload)

    column_headers = _build_column_headers_context(sankey) if display_column_headers else []

    lifecycle_info = f"{lifecycle_phase_str.lower()} " if lifecycle_phase_filter else ""
    excluded_info = ""
    if excluded_object_types:
        labels = [ClassUIConfigProvider.get_label(cls) for cls in excluded_object_types]
        excluded_info = f" excluding {', '.join(labels)}"
    total_co2 = display_co2_amount(format_co2_amount(sankey.total_system_kg))
    title = f"{system.name} — {lifecycle_info}impact repartition{excluded_info} (total {total_co2} CO₂eq)"
    subtitle_map = {None: "All phases", LifeCyclePhases.MANUFACTURING: "Manufacturing only", LifeCyclePhases.USAGE: "Usage only"}
    subtitle = subtitle_map[lifecycle_phase_filter]

    return render(request, "model_builder/result/sankey_diagram.html", {
        "card_id": card_id,
        "sankey_payload_json": sankey_payload_json,
        "sankey_height": sankey_height,
        "column_headers": column_headers,
        "sankey_layout": sankey_payload["layout"],
        "display_column_headers": display_column_headers,
        "title": title,
        "subtitle": subtitle,
    })


def sankey_form(request):
    counter_key = "sankey_card_counter"
    card_id = request.session.get(counter_key, 0) + 1
    request.session[counter_key] = card_id

    model_web = ModelWeb(SessionSystemRepository(request.session))
    present_classes = _get_present_classes(model_web)

    exclude_chips = _build_chip_list(EXCLUDABLE_CLASSES, present_classes, [])
    skip_chips = _build_chip_list(SKIPPABLE_CLASSES, present_classes, DEFAULT_SKIPPED_CLASSES)

    return render(request, "model_builder/result/sankey_card.html", {
        "card_id": card_id,
        "exclude_chips": exclude_chips,
        "skip_chips": skip_chips,
    })
