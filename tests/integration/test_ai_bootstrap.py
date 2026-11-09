"""Handwritten generation through library computation, persistence and ordinary editing."""
import json
import subprocess
import sys

import pytest
from pathlib import Path

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u

from ai_sandbox import run
from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.presenters.simplified_inputs import input_catalog
from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.application.ai_bootstrap.service import build_answer
from model_builder.application.use_cases import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb

ANSWER = Path(__file__).parents[2] / "ai_sandbox/cases/_handwritten_01_recipe_app.json"


@pytest.fixture(autouse=True)
def offline_boavizta(monkeypatch):
    monkeypatch.setenv("USE_BOAVIZTAPI_PACKAGE", "1")


def test_handwritten_answer_computes_roundtrips_and_remains_editable():
    generated = build_answer(ANSWER.read_text())
    system = generated.system
    assert system.total_footprint.sum().value.to(u.kg).magnitude > 0
    patterns = list(system.usage_patterns)
    assert patterns[0].devices[0].id == patterns[1].devices[0].id
    assert patterns[0].network.id == patterns[1].network.id
    assert patterns[0].country.id == patterns[1].country.id
    browsing = next(p for p in patterns if p.name == "Browsing")
    assert browsing.hourly_occurrences.form_inputs["start_date"] == "2027-01-01"
    assert browsing.hourly_occurrences.form_inputs["modeling_duration_value"] == 1
    assert browsing.hourly_occurrences.comment == "200,000 monthly users opening the app 3 times a week."
    assert any(r.kind == "cloud_instance" for r in generated.resolutions)
    raw = system_to_json(system, save_computed_state=False)
    objects, _, _ = json_to_system(raw)
    restored = next(iter(objects["System"].values()))
    assert restored.total_footprint.sum().value.to(u.kg).magnitude > 0
    repository = InMemorySystemRepository(initial_data=raw)
    model = ModelWeb(repository)
    job = next(j for j in model.system.modeling_obj.jobs if j.name == "Recipe list")
    parsed = parse_form_data({"data_transferred": "200", "data_transferred__unit": str(u.kB)}, "Job")
    EditObjectUseCase(model, input_catalog).execute(EditObjectInput(job.id, parsed))
    reloaded = ModelWeb(repository)
    edited = reloaded.get_web_object_from_efootprint_id(job.id).modeling_obj
    assert edited.data_transferred.value.to(u.kB).magnitude == 200
    assert reloaded.system.modeling_obj.total_footprint.sum().value.to(u.kg).magnitude > 0


def test_offline_evaluation_and_replay_keep_reports_and_exports(tmp_path):
    case = run.load_cases(["01"])[0]
    exported = tmp_path / "answer.e-f.json"
    result = run.evaluate(json.loads(ANSWER.read_text()), case, exported)
    assert all(result[k] for k in ("schema_ok", "build_ok", "compute_ok", "export_ok"))
    assert result["counts"]["jobs"] == 5 and result["catalog_resolutions"]
    record = {"case": case["id"], "model": "zai-glm-5-3-flash", "rep": 1, "raw_output": ANSWER.read_text(),
              "input_tokens": None, "output_tokens": None, "cost_usd": None, "latency_s": 0}
    path = tmp_path / "01__flash__r1.json"
    path.write_text(json.dumps(record))
    run.replay(tmp_path)
    replayed = json.loads(path.read_text())
    assert replayed["export_ok"] and replayed["counts"]["jobs"] == 5
    assert (tmp_path / "summary.md").exists() and (tmp_path / "summary.html").exists()
    assert "unavailable" in (tmp_path / "summary.md").read_text()
    completed = subprocess.run([sys.executable, "-m", "ai_sandbox.report", str(tmp_path)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
