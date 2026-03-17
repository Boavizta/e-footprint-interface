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


def _build_column_headers_context(sankey: ImpactRepartitionSankey) -> list[dict]:
    headers = []
    for info in sorted(sankey.get_column_information(), key=lambda x: x["column_index"]):
        lines = [info["description"]] if info["column_type"] == "manual_split" else [ClassUIConfigProvider.get_label(cn) for cn in info["class_names"]]
        headers.append({"lines": lines, "x_center": info["x_center"]})
    return headers


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
    fig = sankey.figure()
    fig.update_layout(title=None, margin=dict(t=10, b=30, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)")
    plotly_json = fig.to_json()

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
        "plotly_json": plotly_json,
        "column_headers": column_headers,
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
