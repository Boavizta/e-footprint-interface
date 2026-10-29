"""The experimental AI assistant box, its generate and edit paths, with the provider call replaced by a fake."""
import json
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from efootprint.abstract_modeling_classes.source_objects import Source, SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u

from model_builder.adapters.repositories import InMemorySystemRepository, SessionSystemRepository
from model_builder.adapters.views import views_ai_assistant
from model_builder.domain.entities.web_core.model_web import ModelWeb
# importable once views_ai_assistant has put ai_sandbox on sys.path
from dsl import build_system, validate_tolerating_extras
from edit import apply_edits, system_to_dsl
from providers import Completion

HANDWRITTEN_CASE = Path(django_settings.BASE_DIR) / "ai_sandbox" / "cases" / "_handwritten_01_recipe_app.json"
URL = "/model_builder/ai-assistant/"
EDIT_ANSWER = {
    "changed": {
        "usage_patterns": [{"name": "Browsing", "volume": {"value": 5200000, "per": "month"},
                            "comments": {"volume": "Doubled as asked."}}],
        "jobs": [{"name": "Push notification", "server": "API server", "data_transferred_kb": 2}],
        "journeys": [{"name": "Browse recipes", "steps": [
            {"name": "Open feed", "jobs": ["Recipe list", "Recipe query", "Recipe thumbnails", "Push notification"]}]}]},
    "removed": {"jobs": ["Photo upload"]},
    "note": "Doubled the browsing volume, added the push job, removed the photo upload.",
}


def _fake_complete(text, calls):
    def fake(model, system, prompt):
        calls.append((model, prompt))
        return Completion(text=text, input_tokens=5000, output_tokens=800, latency_s=12.5)
    return fake


def _system_name(system_data):
    return next(iter(system_data["System"].values()))["name"]


@pytest.fixture
def assistant_on(settings):
    settings.AI_ASSISTANT_ENABLED = True


def _generate_recipe_app(client, monkeypatch):
    monkeypatch.setattr(views_ai_assistant, "complete", _fake_complete(HANDWRITTEN_CASE.read_text(), []))
    client.get("/model_builder/")  # starts the session with the empty model
    assert client.post(URL, {"prompt": "A recipe app", "model": "zai-glm-5-3-flash"}).status_code == 200
    return ModelWeb(SessionSystemRepository(client.session))


def _named(objects, name):
    return next(obj for obj in objects if obj.name == name)


def _steps(system):
    return {step.name: step for journey in system.usage_journeys for step in journey.uj_steps}


@pytest.mark.django_db
def test_generate_on_empty_model_loads_the_answer_and_shows_the_feedback(client, assistant_on, monkeypatch):
    calls = []
    monkeypatch.setattr(views_ai_assistant, "complete", _fake_complete(HANDWRITTEN_CASE.read_text(), calls))
    page = client.get("/model_builder/")
    assert b'id="ai-assistant"' in page.content
    assert b'<option value="zai-glm-5-3-flash"' in page.content.split(b'name="model"')[1].split(b"</option>")[0]

    response = client.post(URL, {"prompt": "A recipe app", "model": "zai-glm-5-3-flash"})

    assert response.status_code == 200
    assert calls == [("zai-glm-5-3-flash", "A recipe app")]
    assert _system_name(SessionSystemRepository(client.session).get_system_data()) == "Recipe app"
    assert client.session["ai_assistant_model"] == "zai-glm-5-3-flash"
    canvas, assistant_box = response.content.decode().split('id="ai-assistant"')
    assert "Recipe app" in canvas  # the re-rendered builder shows the loaded model, not only the echoed answer
    assert "USD" in assistant_box
    assert "Values set from the description carry a comment" in assistant_box
    assert "Raw answer" in assistant_box
    assert 'id="example-picker"' not in canvas + assistant_box


@pytest.mark.django_db
def test_unparseable_answer_leaves_the_model_untouched(client, assistant_on, monkeypatch):
    monkeypatch.setattr(views_ai_assistant, "complete", _fake_complete("I would build a nice model.", []))
    client.get("/model_builder/")
    before = SessionSystemRepository(client.session).get_system_data()

    response = client.post(URL, {"prompt": "A recipe app", "model": "claude-haiku-5-5"})

    assert response.status_code == 200
    assert SessionSystemRepository(client.session).get_system_data() == before
    assert "The answer is not JSON" in response.content.decode()


@pytest.mark.django_db
def test_edit_changes_only_what_is_asked(client, assistant_on, monkeypatch):
    model_web = _generate_recipe_app(client, monkeypatch)
    system = model_web.system.modeling_obj
    _named(system.servers, "API server").lifespan = SourceValue(7 * u.year, comment="Hand-set, outside the DSL.")
    photo_upload_id = _named(system.jobs, "Photo upload").id
    model_web.repository.interface_config = {"simplified_inputs": {"fields": {
        photo_upload_id: {"data_transferred": {"included": True, "help": ""}}}}}
    model_web.persist_to_cache()
    ids_before = set(model_web.flat_efootprint_objs_dict)
    calls = []
    monkeypatch.setattr(views_ai_assistant, "complete", _fake_complete(json.dumps(EDIT_ANSWER), calls))

    response = client.post(URL, {"prompt": "Double the browsing volume", "model": "zai-glm-5-3-flash"})

    assert response.status_code == 200
    assert calls[0][1].startswith("Current model:\n{") and calls[0][1].endswith("Request: Double the browsing volume")
    edited = ModelWeb(SessionSystemRepository(client.session))
    system = edited.system.modeling_obj
    browsing = _named(system.usage_patterns, "Browsing").hourly_occurrences
    assert browsing.form_inputs["initial_volume"] == 5200000 and browsing.form_inputs["start_date"] == "2026-01-01"
    steps = _steps(system)
    assert [job.name for job in steps["Open feed"].jobs] == ["Recipe list", "Recipe query", "Recipe thumbnails",
                                                             "Push notification"]
    assert _named(system.jobs, "Push notification").data_transferred.value == 2 * u.kB
    assert list(steps["Upload photo"].jobs) == []
    assert "Photo upload" not in {job.name for job in system.jobs}
    assert photo_upload_id not in edited.flat_efootprint_objs_dict
    lifespan = _named(system.servers, "API server").lifespan
    assert lifespan.value == 7 * u.year and lifespan.comment == "Hand-set, outside the DSL."
    assert ids_before - {photo_upload_id} <= set(edited.flat_efootprint_objs_dict)
    assert edited.repository.interface_config["simplified_inputs"]["fields"] == {}  # the removed job's input is dropped
    assistant_box = response.content.decode().split('id="ai-assistant"')[1]
    assert "Doubled the browsing volume, added the push job" in assistant_box
    for line in ("set Browsing.volume to 5,200,000 per month", "added job Push notification on API server",
                 "set Open feed.jobs to Recipe list, Recipe query, Recipe thumbnails, Push notification",
                 "removed job Photo upload"):
        assert f"<li>{line}</li>" in assistant_box


@pytest.mark.django_db
def test_edit_answer_naming_an_unknown_job_leaves_the_model_untouched(client, assistant_on, monkeypatch):
    _generate_recipe_app(client, monkeypatch)
    before = SessionSystemRepository(client.session).get_system_data()
    answer = {"changed": {**EDIT_ANSWER["changed"], "journeys": [{"name": "Browse recipes", "steps": [
        {"name": "Open feed", "jobs": ["Recipe list", "Nightly digest"]}]}]}}  # the volume is doubled before this fails
    monkeypatch.setattr(views_ai_assistant, "complete", _fake_complete(json.dumps(answer), []))

    response = client.post(URL, {"prompt": "Add a nightly digest", "model": "zai-glm-5-3-flash"})

    assert response.status_code == 200
    assert SessionSystemRepository(client.session).get_system_data() == before
    assistant_box = response.content.decode().split('id="ai-assistant"')[1]
    assert "Unknown job" in assistant_box and "Nightly digest" in assistant_box
    assert "<li>" not in assistant_box


@pytest.mark.django_db
def test_edge_model_is_refused_without_a_provider_call(client, assistant_on, monkeypatch):
    calls = []
    monkeypatch.setattr(views_ai_assistant, "complete", _fake_complete(HANDWRITTEN_CASE.read_text(), calls))
    assert client.post("/model_builder/load-example/iot_industrial/").status_code == 200
    before = SessionSystemRepository(client.session).get_system_data()

    response = client.post(URL, {"prompt": "Add a sensor", "model": "zai-glm-5-3-flash"})

    assert response.status_code == 200
    assert calls == []
    assert SessionSystemRepository(client.session).get_system_data() == before
    assert "edge objects" in response.content.decode()


@pytest.mark.django_db
def test_flag_off_hides_the_box_and_404s_the_route(client, settings):
    settings.AI_ASSISTANT_ENABLED = False  # independent of a developer's .env turning the flag on
    assert client.post(URL, {"prompt": "A recipe app", "model": "zai-glm-5-3-flash"}).status_code == 404
    assert b'id="ai-assistant"' not in client.get("/model_builder/").content


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
