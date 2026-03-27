import json
import uuid

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from pint import Quantity

from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT, SANKEY_COLUMNS, SANKEY_BREAKDOWN_ONLY_CLASSES
from efootprint.constants.units import u
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.utils.display import best_display_unit, human_readable_unit, display_quantity_as_str
from efootprint.utils.impact_repartition.sankey import ImpactRepartitionSankey
from efootprint.utils.tools import time_it

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
from model_builder.adapters.ui_config.object_category_ui_config_provider import ObjectCategoryUIConfigProvider
from model_builder.adapters.views.exception_handling import render_exception_modal_if_error
from model_builder.domain.entities.web_core.model_web import ModelWeb

EXCLUDABLE_CLASSES = ["Device", "EdgeDevice", "Network", "ServerBase", "ExternalAPI", "Storage", "EdgeStorage"]

# Virtual column for breakdown-only classes (e.g. EdgeComponent), appended after SANKEY_COLUMNS
_BREAKDOWN_COLUMN_INDEX = len(SANKEY_COLUMNS)
_ALL_COLUMNS = list(SANKEY_COLUMNS) + [SANKEY_BREAKDOWN_ONLY_CLASSES]

# "Analyse by" chips: ordered list of (identifier, label, classes_for_presence_check_or_None)
# "phase" and "category" are virtual chips mapping to backend boolean flags.
# Numbered entries map to SANKEY_COLUMNS / breakdown indices.
ANALYSE_BY_CHIPS = [
    ("0", "Total impact", _ALL_COLUMNS[0]),
    ("phase", "Phase", None),
    ("1", "Countries", _ALL_COLUMNS[1]),
    ("2", "Usage patterns", _ALL_COLUMNS[2]),
    ("3", "Usage journeys", _ALL_COLUMNS[3]),
    ("4", "Steps / Functions", _ALL_COLUMNS[4]),
    ("5", "Recurrent edge and server needs", _ALL_COLUMNS[5]),
    ("6", "Jobs / component needs", _ALL_COLUMNS[6]),
    ("category", "Category", None),
    ("7", "Hardware", _ALL_COLUMNS[7]),
    (str(_BREAKDOWN_COLUMN_INDEX), "Component breakdown", _ALL_COLUMNS[_BREAKDOWN_COLUMN_INDEX]),
]

# Chips active by default — matches previous behavior (Phase, Category on; columns 2, 5, 6 skipped)
DEFAULT_ACTIVE_COLUMNS = {"0", "phase", "1", "3", "4", "category", "7", str(_BREAKDOWN_COLUMN_INDEX)}

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


def _build_exclude_chip_list(candidate_classes: list[str], present_classes: set[str]) -> list[dict]:
    chips = []
    for cls_name in candidate_classes:
        if not _class_or_subclass_present(cls_name, present_classes):
            continue
        chips.append({"class_name": cls_name, "label": ClassUIConfigProvider.get_label(cls_name), "active": False})
    return chips


def _column_has_present_classes(column_classes: list[type], present_classes: set[str]) -> bool:
    return any(_class_or_subclass_present(cls.__name__, present_classes) for cls in column_classes)


def _build_analyse_by_chips(present_classes: set[str]) -> list[dict]:
    chips = []
    for chip_id, label, column_classes in ANALYSE_BY_CHIPS:
        if column_classes is not None and not _column_has_present_classes(column_classes, present_classes):
            continue
        chips.append({"chip_id": chip_id, "label": label, "active": chip_id in DEFAULT_ACTIVE_COLUMNS})
    return chips


def _expand_skipped_columns(column_indices: list[str]) -> list[str]:
    class_names = []
    for col_id in column_indices:
        idx = int(col_id)
        if 0 <= idx < len(_ALL_COLUMNS):
            class_names.extend(cls.__name__ for cls in _ALL_COLUMNS[idx])
    return class_names


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
        headers.append({
            "lines": lines,
            "x_left": info["x_left"],
            "x_shift_px": sankey.get_column_header_x_shift_px(),
        })
    return headers


def _resolve_visible_node_idx(node_idx: int, adjacency: dict[int, list[int]], spacer_nodes: set[int]) -> int:
    current = node_idx
    while current in spacer_nodes:
        neighbors = adjacency.get(current, [])
        if not neighbors:
            break
        current = neighbors[0]
    return current


def _get_display_category_label(raw_label: str) -> str:
    for category_name in ObjectCategoryUIConfigProvider.get_category_names():
        if raw_label == category_name:
            return ObjectCategoryUIConfigProvider.get_label(category_name)
        if raw_label.startswith(f"{category_name} "):
            return f"{ObjectCategoryUIConfigProvider.get_label(category_name)} {raw_label[len(category_name) + 1:]}"
    return raw_label


def _get_display_node_label(sankey: ImpactRepartitionSankey, node_idx: int, raw_label: str) -> str:
    category_nodes = getattr(sankey, "_category_node_indices", set())
    return _get_display_category_label(raw_label) if node_idx in category_nodes else raw_label


def _get_sankey_total_value(sankey: ImpactRepartitionSankey):
    return sankey.total_system_value


def _get_sankey_node_value(sankey: ImpactRepartitionSankey, node_idx: int):
    return sankey.node_total_values[node_idx]


def _format_sankey_value(sankey: ImpactRepartitionSankey, value) -> str:
    formatter = getattr(sankey, "format_value_in_root_unit", None)
    if callable(formatter):
        formatted = formatter(value)
        if isinstance(formatted, str):
            return formatted
    quantity = value if isinstance(value, Quantity) else value * u.kg
    return display_quantity_as_str(quantity)


def _get_sankey_display_unit(sankey: ImpactRepartitionSankey):
    getter = getattr(sankey, "get_root_display_unit", None)
    if callable(getter):
        return getter()
    return best_display_unit(_get_sankey_total_value(sankey))


def _get_sankey_percentage(sankey: ImpactRepartitionSankey, value: Quantity) -> float:
    getter = getattr(sankey, "get_percentage_of_total", None)
    if callable(getter):
        return getter(value)
    display_unit = _get_sankey_display_unit(sankey)
    total = sankey.total_system_value.to(display_unit).magnitude
    if total <= 0:
        return 0.0
    return value.to(display_unit).magnitude / total * 100


def _build_node_tooltip(sankey: ImpactRepartitionSankey, node_idx: int, display_full_label: str) -> str:
    value = _get_sankey_node_value(sankey, node_idx)
    amount_str = _format_sankey_value(sankey, value)
    pct = _get_sankey_percentage(sankey, value)
    if node_idx in sankey.aggregated_node_members:
        members_str = "<br>".join(
            f"{_get_display_category_label(label)}: {_format_sankey_value(sankey, member_value)} CO2eq"
            for label, member_value in sankey.aggregated_node_members[node_idx]
        )
        return f"{display_full_label}<br>{amount_str} CO2eq ({pct:.1f}%)<br><br>Aggregated objects:<br>{members_str}"
    return f"{display_full_label}<br>{amount_str} CO2eq ({pct:.1f}%)"


def _build_link_tooltip(
        sankey: ImpactRepartitionSankey, source_full_label: str, target_full_label: str, value: Quantity) -> str:
    amount_str = _format_sankey_value(sankey, value)
    pct = _get_sankey_percentage(sankey, value)
    return f"{source_full_label} → {target_full_label}<br>{amount_str} CO2eq ({pct:.1f}%)"


def _build_sankey_payload(sankey: ImpactRepartitionSankey) -> dict:
    sankey.build()
    node_columns = getattr(sankey, "_node_columns", {})
    # Spacer nodes are necessary for Plotly (which is used for e-footprint sankey graph generation) because Plotly
    # doesn’t support setting the node depth, contrary to ECharts. One day, Plotly might be dropped in e-footprint
    # to make data ECharts compatible from the start and simplify the whole system.
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

    display_labels_by_idx = {}
    display_full_labels_by_idx = {}
    display_unit = _get_sankey_display_unit(sankey)
    display_unit_str = human_readable_unit(display_unit)
    for node_idx, label in enumerate(sankey.node_labels):
        display_labels_by_idx[node_idx] = _get_display_node_label(sankey, node_idx, label)
        display_full_labels_by_idx[node_idx] = _get_display_node_label(sankey, node_idx, sankey.full_node_labels[node_idx])

    nodes_per_column: dict[int, int] = {}
    nodes = []
    for node_idx, label in enumerate(sankey.node_labels):
        if node_idx in spacer_nodes:
            continue
        column = node_columns.get(node_idx, min_column)
        nodes_per_column[column] = nodes_per_column.get(column, 0) + 1
        display_label = display_labels_by_idx[node_idx]
        display_full_label = display_full_labels_by_idx[node_idx]
        name_key = f"{display_label}{_SANKEY_NAME_DELIMITER}{node_idx}"
        nodes.append({
            "key": f"node-{node_idx}",
            "name_key": name_key,
            "label": display_label,
            "full_name": display_full_label,
            "value": sankey.node_total_values[node_idx].to(display_unit).magnitude,
            "depth": column - min_column,
            "column": column,
            "color": node_colors[node_idx],
            "tooltip_html": _build_node_tooltip(sankey, node_idx, display_full_label),
            "is_aggregated": node_idx in sankey.aggregated_node_members,
            "is_category": node_idx in category_nodes,
            "is_leaf": node_idx in leaf_nodes,
            "is_breakdown": node_idx in breakdown_nodes,
        })

    right_padding_px = _estimate_sankey_right_padding(nodes)

    collapsed_links: dict[tuple[int, int], Quantity] = {}
    for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values):
        if source in spacer_nodes:
            continue
        visible_source = _resolve_visible_node_idx(source, incoming_by_target, spacer_nodes)
        visible_target = _resolve_visible_node_idx(target, outgoing_by_source, spacer_nodes)
        if visible_source == visible_target or visible_source in spacer_nodes or visible_target in spacer_nodes:
            continue
        existing = collapsed_links.get((visible_source, visible_target))
        collapsed_links[(visible_source, visible_target)] = value if existing is None else existing + value

    links = []
    for (source_idx, target_idx), value in sorted(collapsed_links.items()):
        links.append({
            "source_key": f"node-{source_idx}",
            "target_key": f"node-{target_idx}",
            "source_name_key": f"{display_labels_by_idx[source_idx]}{_SANKEY_NAME_DELIMITER}{source_idx}",
            "target_name_key": f"{display_labels_by_idx[target_idx]}{_SANKEY_NAME_DELIMITER}{target_idx}",
            "value": value.to(display_unit).magnitude,
            "color": node_colors[source_idx].replace("0.8)", "0.35)"),
            "tooltip_html": _build_link_tooltip(
                sankey, display_full_labels_by_idx[source_idx], display_full_labels_by_idx[target_idx], value),
        })

    node_width, node_gap, chart_top, chart_bottom = 20, 20, 10, 30
    max_nodes_per_col = max(nodes_per_column.values()) if nodes_per_column else 1
    recommended_height = max(400, max_nodes_per_col * (node_width + node_gap) + chart_top + chart_bottom)

    return {
        "nodes": nodes,
        "links": links,
        "display_unit": display_unit_str,
        "layout": {
            "left_padding_px": _SANKEY_SIDE_PADDING_PX,
            "right_padding_px": right_padding_px,
            "horizontal_padding_px": _SANKEY_SIDE_PADDING_PX + right_padding_px,
        },
    }, recommended_height


@render_exception_modal_if_error
@time_it
def sankey_diagram(request):
    card_id = request.POST.get("card_id", "")
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    system = list(model_web.response_objs["System"].values())[0]

    lifecycle_phase_str = request.POST.get("lifecycle_phase_filter", "")
    lifecycle_phase_filter = _LIFECYCLE_PHASE_MAP.get(lifecycle_phase_str)

    aggregation_threshold_percent = float(request.POST.get("aggregation_threshold_percent", "1.0"))
    active_columns = set(request.POST.getlist("active_columns"))
    skip_phase_footprint_split = "phase" not in active_columns
    skip_object_category_footprint_split = "category" not in active_columns
    skip_object_footprint_split = "7" not in active_columns and "8" not in active_columns
    inactive_column_indices = [
        chip_id for chip_id, _, _ in ANALYSE_BY_CHIPS
        if chip_id not in active_columns and chip_id not in ("phase", "category")
    ]
    skipped_classes = _expand_skipped_columns(inactive_column_indices)
    excluded_object_types = request.POST.getlist("excluded_types")
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
    total_co2 = _format_sankey_value(sankey, _get_sankey_total_value(sankey))
    title = f"{system.name} — {lifecycle_info}impact repartition{excluded_info} (total {total_co2} CO₂eq)"
    subtitle_map = {None: "All phases", LifeCyclePhases.MANUFACTURING: "Manufacturing only", LifeCyclePhases.USAGE: "Usage only"}
    subtitle = subtitle_map[lifecycle_phase_filter]

    card_settings = {
        "id": card_id,
        "lifecycle_phase_filter": lifecycle_phase_str,
        "aggregation_threshold_percent": aggregation_threshold_percent,
        "active_columns": sorted(active_columns),
        "excluded_types": excluded_object_types,
        "display_column_headers": display_column_headers,
        "node_label_max_length": node_label_max_length,
    }
    config = repository.interface_config
    diagrams = config.setdefault("sankey_diagrams", [])
    existing_index = next((i for i, diagram in enumerate(diagrams) if diagram["id"] == card_id), None)
    if existing_index is None:
        diagrams.append(card_settings)
    else:
        diagrams[existing_index] = card_settings
    model_web.persist_to_cache()

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
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    present_classes = _get_present_classes(model_web)
    card_id = uuid.uuid4().hex[:8]

    exclude_chips = _build_exclude_chip_list(EXCLUDABLE_CLASSES, present_classes)
    analyse_by_chips = _build_analyse_by_chips(present_classes)

    return render(request, "model_builder/result/sankey_card.html", {
        "card_id": card_id,
        "exclude_chips": exclude_chips,
        "analyse_by_chips": analyse_by_chips,
    })


def sankey_cards(request):
    """Return all saved Sankey cards, or a default one if none exist."""
    repository = SessionSystemRepository(request.session)
    saved_diagrams = repository.interface_config.get("sankey_diagrams", [])

    if not saved_diagrams:
        return sankey_form(request)

    model_web = ModelWeb(repository)
    present_classes = _get_present_classes(model_web)
    cards_html = []

    for saved_diagram in saved_diagrams:
        exclude_chips = _build_exclude_chip_list(EXCLUDABLE_CLASSES, present_classes)
        analyse_by_chips = _build_analyse_by_chips(present_classes)

        saved_active_columns = set(saved_diagram.get("active_columns", []))
        saved_excluded_types = set(saved_diagram.get("excluded_types", []))
        for chip in analyse_by_chips:
            chip["active"] = chip["chip_id"] in saved_active_columns
        for chip in exclude_chips:
            chip["active"] = chip["class_name"] in saved_excluded_types

        cards_html.append(render_to_string(
            "model_builder/result/sankey_card.html",
            {
                "card_id": saved_diagram["id"],
                "exclude_chips": exclude_chips,
                "analyse_by_chips": analyse_by_chips,
                "initial_settings": saved_diagram,
            },
            request=request,
        ))

    return HttpResponse("".join(cards_html))


def sankey_delete_card(request):
    """Delete a persisted Sankey card configuration."""
    card_id = request.POST.get("card_id", "")
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    config = repository.interface_config
    diagrams = config.get("sankey_diagrams", [])
    config["sankey_diagrams"] = [diagram for diagram in diagrams if diagram["id"] != card_id]
    model_web.persist_to_cache()
    return HttpResponse("")
