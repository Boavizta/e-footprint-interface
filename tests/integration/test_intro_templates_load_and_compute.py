"""Load-and-compute (and freshness) coverage for the introductory templates.

Each committed JSON must load through the interface's real import path
(``ProgressiveImportService``) and produce a non-empty computed footprint —
the success criterion "complete, working system... results compute without
error". Fails if a template stops loading or computing after a library schema
change (re-run ``python -m scripts.build_intro_templates`` to regenerate).

``test_scenario_constructor_round_trips_to_committed_json`` additionally guards
the interface-owned JSONs against silently drifting from their ``build_system()``
source of truth (it rebuilds and compares). Like the load tests it lives in the
integration layer rather than the unit layer because the rebuild does real work,
including a live Boavizta API call via ``BoaviztaCloudServer.from_defaults``.
"""
import importlib
import json

import pytest
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json

from model_builder.domain.reference_data.modeling_templates import INTRO_TEMPLATES
from model_builder.domain.reference_data.modeling_templates.introductory.registry import HERE
from model_builder.domain.services import ProgressiveImportService

# Mirror the production import cap (InMemorySystemRepository(max_payload_size_mb=30.0)).
MAX_PAYLOAD_SIZE_MB = 30.0

_params = pytest.mark.parametrize("tpl", INTRO_TEMPLATES, ids=lambda t: t.id)

# Interface-owned introductory templates commit their JSON next to the registry
# (json_path.parent == HERE) and regenerate it from a
# scripts/intro_template_scenarios/<id>.py build_system(). The e-commerce template
# is library-owned (its JSON and round-trip test live in efootprint), so the
# freshness test below excludes it.
_LOCAL_INTRO_TEMPLATES = tuple(tpl for tpl in INTRO_TEMPLATES if tpl.json_path.parent == HERE)
_local_params = pytest.mark.parametrize("tpl", _LOCAL_INTRO_TEMPLATES, ids=lambda t: t.id)


def _load_raw(tpl):
    with open(tpl.json_path) as f:
        return json.load(f)


@_params
def test_template_imports_and_computes_through_interface_path(tpl):
    imported = ProgressiveImportService(max_payload_size_mb=MAX_PAYLOAD_SIZE_MB).import_system(_load_raw(tpl))

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


def test_freshness_covers_interface_owned_templates_only():
    # A misfiring filter would make the parametrized round-trip test pass vacuously.
    local_ids = {tpl.id for tpl in _LOCAL_INTRO_TEMPLATES}
    assert local_ids, "No interface-owned introductory templates matched; the round-trip test would be vacuous."
    assert "ecommerce" not in local_ids, "ecommerce is library-owned and round-trip-tested in efootprint, not here."


@_local_params
def test_scenario_constructor_round_trips_to_committed_json(tpl):
    """The committed JSON must equal what ``scripts/build_intro_templates`` produces.

    Mirrors the library's how-to round-trip test so the derived JSON snapshots
    cannot silently drift from their ``build_system()`` source of truth. The build
    script flips ``ModelingObject._use_name_as_id`` so serialized ids are readable;
    the interface test suite leaves it False (runtime objects use uuids), so we flip
    it locally for the rebuild only and restore it afterwards.
    """
    build_system = importlib.import_module(f"scripts.intro_template_scenarios.{tpl.id}").build_system
    original_use_name_as_id = ModelingObject._use_name_as_id
    ModelingObject._use_name_as_id = True
    try:
        freshly_built = system_to_json(build_system(), save_calculated_attributes=False)
    finally:
        ModelingObject._use_name_as_id = original_use_name_as_id

    with open(tpl.json_path) as f:
        committed = json.load(f)
    assert freshly_built == committed, (
        f"Template {tpl.id} JSON does not match the output of build_system(); "
        "re-run `python -m scripts.build_intro_templates` and commit the regenerated JSON.")
