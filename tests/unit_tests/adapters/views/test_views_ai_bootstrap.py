"""Fresh bootstrap through real views and session repositories, with offline inference."""
import json
import logging
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.conf import settings as django_settings
from efootprint.api_utils.system_to_json import system_to_json

from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.adapters.repositories import SessionWorkspaceRepository, SessionSystemRepository
from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.workspace_base import system_id_of
from model_builder.adapters.views import views_ai_bootstrap as views
from model_builder.application.ai_bootstrap.service import Completion, build_answer
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.services import get_example_system_data, is_empty_model

pytestmark = pytest.mark.django_db
START = "/model_builder/start-ai-bootstrap/"
GENERATE = "/model_builder/generate-ai-bootstrap/"
ANSWER = (Path(django_settings.BASE_DIR) / "ai_sandbox/cases/_handwritten_01_recipe_app.json").read_text()


@pytest.fixture(autouse=True)
def configuration(settings, monkeypatch):
    settings.AI_BOOTSTRAP_ENABLED = True
    settings.MISTRAL_API_KEY = "dummy-server-key"
    settings.STORAGES = {**settings.STORAGES, "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")
    monkeypatch.setattr(views, "estimate_call", lambda completion: {
        "cost_usd": 0.001, "cache_discount_unknown": True, "rate_card_date": "2026-11-09",
        "impact_kg": SimpleNamespace(min=0.0001, max=0.0002)})


@pytest.fixture
def provider(monkeypatch):
    fake = Mock(return_value=Completion(ANSWER, 5000, 800, latency_s=12.5))
    monkeypatch.setattr(views, "complete_mistral", fake)
    return fake


def repository(client):
    return SessionWorkspaceRepository(client.session).active_repository()


def saved(client):
    return deepcopy(repository(client).get_system_data())


def seed(client, slot, raw, config=None):
    session = client.session
    workspace = SessionWorkspaceRepository(session)
    repo = workspace.repository_for(slot)
    repo.interface_config = config or {}
    views.load_system_into_session(repo, raw, workspace=workspace)
    session.save()


@pytest.mark.parametrize("slot", [0, 1])
@pytest.mark.parametrize("example", ["ecommerce", "iot_industrial"])
def test_start_replaces_only_active_slot_and_discards_settings(client, slot, example):
    client.get("/model_builder/")
    client.post("/model_builder/add-model/", {"source": "blank"})
    client.post("/model_builder/switch-model/", {"slot": slot})
    seed(client, slot, get_example_system_data(example), {
        "simplified_inputs": {"fields": {"discarded": {"x": {"included": True, "help": "old"}}}},
        "sankey": {"discarded-setting": True}})
    sibling = 1 - slot
    before = deepcopy(SessionWorkspaceRepository(client.session).repository_for(sibling).get_system_data())

    response = client.post(START, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    assert is_empty_model(saved(client))
    assert "discarded" not in json.dumps(repository(client).interface_config)
    assert SessionWorkspaceRepository(client.session).repository_for(sibling).get_system_data() == before
    assert system_id_of(saved(client)) != system_id_of(before)
    body = response.content.decode()
    assert 'data-ai-bootstrap-panel="input"' in body
    assert 'id="example-picker"' not in body
    assert 'id="result-block" class="bg-transparent overflow-y-auto overflow-x-hidden pt-1"></div>' in body
    assert response["HX-Trigger-After-Settle"] == "initModelBuilderMain"
    form = body.split('<form id="sidePanelForm"')[1].split("</form>")[0]
    assert 'hx-disabled-elt="button:not(:disabled)"' in form
    assert 'name="description"' in form and "required" in form
    assert "setRecomputationToTrueIfResultPaneIsOpen" not in body


def test_reference_role_after_remove_and_readd_preserves_actual_sibling(client):
    client.get("/model_builder/")
    client.post("/model_builder/add-model/", {"source": "blank"})
    client.post("/model_builder/remove-model/", {"slot": "0"})
    client.post("/model_builder/load-example/ecommerce/")
    before = saved(client)
    client.post("/model_builder/add-model/", {"source": "blank"})
    assert SessionWorkspaceRepository(client.session).active_slot() == 0
    assert client.post(START).status_code == 200
    assert SessionWorkspaceRepository(client.session).repository_for(1).get_system_data() == before


@pytest.mark.parametrize("slot", [0, 1])
def test_generation_saves_once_preserves_sibling_and_has_transient_summary(client, provider, monkeypatch, slot):
    client.get("/model_builder/")
    client.post("/model_builder/add-model/", {"source": "blank"})
    # A generated System collision must use the same distinctification as ordinary imports.
    sibling = 1 - slot
    seed(client, sibling, system_to_json(build_answer(ANSWER).system, save_computed_state=False),
         {"sankey": {"sibling-setting": True}})
    client.post("/model_builder/switch-model/", {"slot": slot})
    client.post(START)
    before = deepcopy(SessionWorkspaceRepository(client.session).repository_for(sibling).get_system_data())
    original = SessionSystemRepository.save_data
    writes = []

    def save(repo, data, recovery_data=None):
        writes.append(repo.slot)
        return original(repo, data, recovery_data=recovery_data)

    monkeypatch.setattr(SessionSystemRepository, "save_data", save)
    prompt = "  PROMPT_SENTINEL <script>alert('private')</script>  "
    response = client.post(GENERATE, {"description": prompt, "model": "untrusted-selection"})

    assert response.status_code == 200
    assert writes == [slot]
    assert provider.call_count == 1 and provider.call_args.args[1] == prompt.strip()
    assert not is_empty_model(saved(client))
    assert SessionWorkspaceRepository(client.session).repository_for(sibling).get_system_data() == before
    assert system_id_of(saved(client)) != system_id_of(before)
    body = response.content.decode()
    panel = body.split('data-ai-bootstrap-panel="summary"')[1].split("</div>")[0]
    assert "&lt;script&gt;" in panel and "<script>alert" not in panel
    assert "<form" not in panel and 'id="btn-submit-form"' not in body
    assert "<details>" in panel and "USD 0.001000" in panel and "100" in panel and "200" in panel
    assert "Cached-input discounts not accounted for" in panel
    assert "unscaled" in panel and "guaranteed ceiling" in panel
    assert panel.index("Time spent:") < panel.index("Volumes:") < panel.index("Infrastructure:")
    assert "PROMPT_SENTINEL" not in json.dumps(saved(client)) + json.dumps(dict(client.session))
    assert "PROMPT_SENTINEL" not in client.get("/model_builder/download-json/").content.decode()
    reload_body = client.get("/model_builder/").content.decode()
    assert "data-ai-bootstrap-panel" not in reload_body and "PROMPT_SENTINEL" not in reload_body
    assert ModelWeb(repository(client)).usage_patterns


@pytest.mark.parametrize("answer", ["RAW_SENTINEL not JSON", '{"servers": "RAW_SENTINEL"}',
                                    '{"system_name":"Incomplete"}',
                                    '{"system_name":"Bad reference","jobs":['
                                    '{"name":"RAW_SENTINEL","server":"missing"}]}'])
def test_bad_answers_leave_saved_scratch_and_settings_intact(client, provider, answer, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    client.post(START)
    repo = repository(client)
    repo.interface_config = {"sankey": {"keep-setting": True}}
    repo.save_interface_config()
    before = saved(client)
    provider.return_value = Completion(answer)
    save = Mock(side_effect=AssertionError("must not save"))
    monkeypatch.setattr(SessionSystemRepository, "save_data", save)

    response = client.post(GENERATE, {"description": "PROMPT_SENTINEL <b>private</b>"})

    assert response.status_code == 200
    assert saved(client) == before
    assert "PROMPT_SENTINEL &lt;b&gt;private&lt;/b&gt;" in response.content.decode()
    assert "RAW_SENTINEL" not in response.content.decode() + caplog.text
    assert "PROMPT_SENTINEL" not in caplog.text + json.dumps(dict(client.session))
    save.assert_not_called()


@pytest.mark.parametrize("stage", ["provider", "compute", "size", "budget"])
def test_stage_rejections_preserve_saved_scratch_without_sensitive_errors(client, provider, monkeypatch, caplog, stage):
    caplog.set_level(logging.DEBUG)
    client.post(START)
    before = saved(client)
    secret = "ERROR_SENTINEL generated-content PROMPT_SENTINEL"
    if stage == "provider":
        provider.side_effect = views.ProviderError(secret)
    elif stage == "compute":
        monkeypatch.setattr(views, "prepare_system_for_session", Mock(side_effect=ValueError(secret)))
    elif stage == "size":
        monkeypatch.setattr(views, "prepare_system_for_session", Mock(side_effect=PayloadSizeLimitExceeded(100, 30)))
    else:
        monkeypatch.setattr(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 0.00001)

    response = client.post(GENERATE, {"description": "PROMPT_SENTINEL"})

    assert response.status_code == 200
    assert saved(client) == before
    assert 'data-ai-bootstrap-panel="input"' in response.content.decode()
    assert "ERROR_SENTINEL" not in response.content.decode() + caplog.text
    assert "PROMPT_SENTINEL" not in caplog.text


def test_estimator_failure_does_not_reject_saved_model(client, provider, monkeypatch):
    client.post(START)
    monkeypatch.setattr(views, "estimate_call", Mock(side_effect=RuntimeError("private metrics")))
    response = client.post(GENERATE, {"description": "A recipe app"})
    assert response.status_code == 200 and not is_empty_model(saved(client))
    assert "Cost estimate unavailable" in response.content.decode()
    assert "Impact estimate unavailable" in response.content.decode()


@pytest.mark.parametrize("slot", [0, 1])
def test_shared_budget_rejection_at_save_preserves_both_slots_and_settings(client, provider, monkeypatch, slot):
    client.get("/model_builder/")
    client.post("/model_builder/add-model/", {"source": "blank"})
    sibling = 1 - slot
    raw = system_to_json(build_answer(ANSWER).system, save_computed_state=False)
    seed(client, sibling, raw, {"sankey": {"sibling-setting": True}})
    client.post("/model_builder/switch-model/", {"slot": slot})
    client.post(START)
    repo = repository(client)
    repo.interface_config = {"sankey": {"keep-setting": True}}
    repo.save_interface_config()
    repo.session.save()
    workspace = SessionWorkspaceRepository(client.session)
    before = {index: deepcopy(workspace.repository_for(index).get_system_data()) for index in workspace.list_slots()}
    saved_settings = deepcopy(client.session[SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY])

    repo.interface_config = {}
    prepared = views.prepare_system_for_session(repo, raw, workspace=workspace)
    candidate_size = compute_json_size(prepared.to_json()).size_bytes
    sizes = repo._index.slot_sizes()
    combined_size = candidate_size + sizes[sibling]
    # Keep preparation and the saved workspace valid; only the replacement's combined weight must fail.
    budget_bytes = (max(sum(sizes.values()), candidate_size) + combined_size) // 2
    assert candidate_size < budget_bytes < combined_size
    assert sum(sizes.values()) < budget_bytes
    monkeypatch.setattr(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", budget_bytes / (1024 * 1024))
    attempts = []
    original_save = SessionSystemRepository.save_data

    def save(target, data, recovery_data=None):
        attempts.append(target.slot)
        return original_save(target, data, recovery_data=recovery_data)

    monkeypatch.setattr(SessionSystemRepository, "save_data", save)
    writes = Mock(side_effect=AssertionError("rejected graph must not reach either backend"))
    monkeypatch.setattr(CacheBackend, "set", writes)

    response = client.post(GENERATE, {"description": "A recipe app"})

    assert response.status_code == 200
    assert "exceeds this workspace&#x27;s size limit" in response.content.decode()
    assert attempts == [slot]
    writes.assert_not_called()
    workspace = SessionWorkspaceRepository(client.session)
    assert {index: workspace.repository_for(index).get_system_data() for index in workspace.list_slots()} == before
    assert client.session[SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY] == saved_settings


def test_empty_description_and_nonempty_saved_model_do_not_call_provider(client, provider):
    client.post(START)
    before = saved(client)
    response = client.post(GENERATE, {"description": " \n "})
    assert response.status_code == 200 and saved(client) == before
    client.post("/model_builder/load-example/ecommerce/")
    before = saved(client)
    response = client.post(GENERATE, {"description": "Replace silently?"})
    assert "Start with AI again" in response.content.decode() and saved(client) == before
    provider.assert_not_called()


@pytest.mark.parametrize("url", [START, GENERATE])
@pytest.mark.parametrize("enabled,key", [(False, "dummy"), (True, "")])
def test_unavailable_endpoints_are_not_found(client, settings, url, enabled, key):
    settings.AI_BOOTSTRAP_ENABLED, settings.MISTRAL_API_KEY = enabled, key
    assert client.post(url).status_code == 404


@pytest.mark.parametrize("url", [START, GENERATE])
def test_operations_are_post_only(client, url):
    assert client.get(url).status_code == 405


def test_old_editing_endpoint_is_gone(client):
    assert client.post("/model_builder/ai-assistant/").status_code == 404


@pytest.mark.parametrize("stage", ["prepare", "save"])
def test_unexpected_storage_failure_propagates(client, provider, monkeypatch, stage):
    client.post(START)
    if stage == "prepare":
        monkeypatch.setattr(views, "prepare_system_for_session", Mock(side_effect=OSError("cache unavailable")))
    else:
        monkeypatch.setattr(SessionSystemRepository, "save_data", Mock(side_effect=OSError("cache unavailable")))
    with pytest.raises(OSError, match="cache unavailable"):
        client.post(GENERATE, {"description": "A recipe app"})


def test_summary_shows_escaped_substitutions_and_ignored_fields(client, provider, monkeypatch):
    from model_builder.application.ai_bootstrap.catalogs import Resolution
    client.post(START)
    generated = build_answer(ANSWER)
    generated.resolutions = [Resolution("cloud_instance", "<requested>", "<resolved>", "fallback")]
    generated.ignored_fields = ["<ignored>"]
    monkeypatch.setattr(views, "generate", lambda description, complete: (generated, Completion(ANSWER)))
    response = client.post(GENERATE, {"description": "A recipe app"})
    body = response.content.decode()
    assert "&lt;requested&gt; → &lt;resolved&gt;" in body and "&lt;ignored&gt;" in body
    assert "<requested>" not in body


def test_success_logs_no_prompt_raw_answer_or_model_content(client, provider, caplog):
    client.post(START)
    caplog.set_level(logging.DEBUG)
    answer = json.loads(ANSWER)
    answer["system_name"] = "MODEL_CONTENT_SENTINEL"
    provider.return_value = Completion(json.dumps({**answer, "RAW_ANSWER_SENTINEL": "ignored"}), 100, 100)
    response = client.post(GENERATE, {"description": "PROMPT_SENTINEL"})
    assert response.status_code == 200
    for value in ["PROMPT_SENTINEL", "RAW_ANSWER_SENTINEL", "MODEL_CONTENT_SENTINEL"]:
        assert value not in caplog.text
