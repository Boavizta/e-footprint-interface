"""Remaining developer-only AI edit/read-back checks, pending retirement."""
import json
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from efootprint.abstract_modeling_classes.source_objects import Source, SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.application.ai_bootstrap.dsl import build_system, validate_tolerating_extras
from ai_sandbox.edit import apply_edits, system_to_dsl

HANDWRITTEN_CASE = Path(django_settings.BASE_DIR) / "ai_sandbox" / "cases" / "_handwritten_01_recipe_app.json"


def _named(objects, name):
    return next(obj for obj in objects if obj.name == name)


def _steps(system):
    return {step.name: step for journey in system.usage_journeys for step in journey.uj_steps}


def test_reading_a_built_model_back_rebuilds_the_same_footprint():
    spec, _ = validate_tolerating_extras(json.loads(HANDWRITTEN_CASE.read_text()))
    system, _ = build_system(spec)
    model_web = ModelWeb(InMemorySystemRepository(initial_data=system_to_json(system, save_computed_state=False)))
    model_before = system_to_json(model_web.system.modeling_obj, save_computed_state=False)

    read_back = system_to_dsl(model_web)
    # Reading leaves the live model as it was (the default API server storage stays in TB, not converted to GB).
    assert system_to_json(model_web.system.modeling_obj, save_computed_state=False) == model_before
    rebuilt, _ = build_system(validate_tolerating_extras(json.loads(json.dumps(read_back)))[0])

    original_kg = system.total_footprint.sum().to("kg").magnitude
    assert rebuilt.total_footprint.sum().to("kg").magnitude == pytest.approx(original_kg, rel=0.01)
    steps = {st["name"]: st for jo in read_back["journeys"] for st in jo["steps"]}
    assert steps["Ask a question"]["jobs"] == ["Chef answer", "Chef answer"]
    servers = {s["name"]: s for s in read_back["servers"]}
    assert servers["Photo store"]["comments"] == {"storage_gb": "About 1 million dish photos of 2 MB each."}
    jobs = {j["name"]: j for j in read_back["jobs"]}
    assert jobs["Recipe thumbnails"]["comments"] == {"data_transferred_kb": "6 thumbnails of 80 kB per recipe page."}


def _recipe_app_model_web():
    spec, _ = validate_tolerating_extras(json.loads(HANDWRITTEN_CASE.read_text()))
    system, _ = build_system(spec)
    return ModelWeb(InMemorySystemRepository(initial_data=system_to_json(system, save_computed_state=False)))


def test_an_echoed_field_keeps_its_hand_set_source_and_comment():
    model_web = _recipe_app_model_web()
    job = _named(model_web.system.modeling_obj.jobs, "Recipe list")
    source = Source("Load test", "https://example.org/load-test")
    job.data_transferred = SourceValue(1.2345678 * u.MB, source=source, comment="Measured in production.")
    echoed = next(entry for entry in system_to_dsl(model_web)["jobs"] if entry["name"] == "Recipe list")
    echoed.pop("comments")  # read back as 1234.57 kB; small models repeat the object without its comments

    lines = apply_edits({"changed": {"jobs": [echoed]}}, model_web)

    assert lines == []
    assert (job.data_transferred.value, job.data_transferred.source, job.data_transferred.comment) == (
        1.2345678 * u.MB, source, "Measured in production.")


def test_a_re_list_deletes_only_the_children_nothing_else_uses():
    model_web = _recipe_app_model_web()
    system = model_web.system.modeling_obj
    open_feed = _steps(system)["Open feed"]
    _named(system.usage_journeys, "Upload dish photo").uj_steps[open_feed] = SourceValue(1 * u.dimensionless)
    answer = {"changed": {"journeys": [
        {"name": "Upload dish photo", "steps": [{"name": "Upload photo", "jobs": ["Photo upload", "Recipe query"]}]},
        {"name": "Browse recipes", "steps": [{"name": "Open feed", "jobs": ["Recipe list"]}]}]},
        "removed": {"usage_patterns": ["Chef sessions"], "journeys": ["Ask the chef"], "jobs": ["Chef answer"]}}

    lines = apply_edits(answer, model_web)

    journeys = {journey.name: [step.name for step in journey.uj_steps] for journey in system.usage_journeys}
    assert journeys == {"Browse recipes": ["Open feed"], "Upload dish photo": ["Upload photo"]}
    assert sorted(job.name for job in system.jobs) == ["Photo upload", "Recipe list", "Recipe query"]
    assert "Recipe thumbnails" not in {obj.name for obj in model_web.flat_efootprint_objs_dict.values()}
    assert lines[-5:] == ["removed job Recipe thumbnails", "removed usage pattern Chef sessions",
                          "removed journey Ask the chef", "removed job Chef answer", "removed step Ask a question"]
