"""The experimental AI assistant box and its generate path, with the provider call replaced by a fake."""
import json
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from efootprint.api_utils.system_to_json import system_to_json

from model_builder.adapters.repositories import InMemorySystemRepository, SessionSystemRepository
from model_builder.adapters.views import views_ai_assistant
from model_builder.domain.entities.web_core.model_web import ModelWeb
# importable once views_ai_assistant has put ai_sandbox on sys.path
from dsl import build_system, validate_tolerating_extras
from edit import system_to_dsl
from providers import Completion

HANDWRITTEN_CASE = Path(django_settings.BASE_DIR) / "ai_sandbox" / "cases" / "_handwritten_01_recipe_app.json"
URL = "/model_builder/ai-assistant/"


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

    read_back = system_to_dsl(model_web)
    rebuilt, _ = build_system(validate_tolerating_extras(json.loads(json.dumps(read_back)))[0])

    original_kg = system.total_footprint.sum().to("kg").magnitude
    assert rebuilt.total_footprint.sum().to("kg").magnitude == pytest.approx(original_kg, rel=0.01)
    steps = {st["name"]: st for jo in read_back["journeys"] for st in jo["steps"]}
    assert steps["Ask a question"]["jobs"] == ["Chef answer", "Chef answer"]
    servers = {s["name"]: s for s in read_back["servers"]}
    assert servers["Photo store"]["comments"] == {"storage_gb": "About 1 million dish photos of 2 MB each."}
    jobs = {j["name"]: j for j in read_back["jobs"]}
    assert jobs["Recipe thumbnails"]["comments"] == {"data_transferred_kb": "6 thumbnails of 80 kB per recipe page."}
