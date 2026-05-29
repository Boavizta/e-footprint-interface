"""Load-and-compute coverage for the introductory templates.

Each committed JSON must load through the interface's real import path
(``ProgressiveImportService``) and produce a non-empty computed footprint —
the spec success criterion "complete, working system... results compute without
error". Fails if a template stops loading or computing after a library schema
change (re-run ``python -m scripts.build_intro_templates`` to regenerate).
"""
import json

import pytest
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.api_utils.json_to_system import json_to_system

from model_builder.domain.reference_data.modeling_templates import INTRO_TEMPLATES

_params = pytest.mark.parametrize("tpl", INTRO_TEMPLATES, ids=lambda t: t.id)


def _load_raw(tpl):
    with open(tpl.json_path) as f:
        return json.load(f)


@_params
def test_template_imports_and_computes_through_interface_path(tpl):
    from model_builder.domain.services import ProgressiveImportService

    imported = ProgressiveImportService(max_payload_size_mb=30).import_system(_load_raw(tpl))

    class_obj_dict, _, _ = json_to_system(imported)
    system = next(iter(class_obj_dict["System"].values()))
    assert not isinstance(system.total_footprint, EmptyExplainableObject), (
        f"Template {tpl.id} produced an empty total_footprint")


def test_iot_template_contains_edge_objects():
    """The IoT template must serialize edge objects so the Step 5 edge toggle latches on load."""
    iot = next(tpl for tpl in INTRO_TEMPLATES if tpl.id == "iot_industrial")
    raw = _load_raw(iot)
    assert "EdgeUsagePattern" in raw and "EdgeComputer" in raw, (
        "IoT template JSON must contain edge objects (EdgeUsagePattern + EdgeComputer)")
