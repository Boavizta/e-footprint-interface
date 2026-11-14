"""The AI-assisted bootstrap, told by its own code (`narrate` and `event` calls) through the real views.

The provider is a local fake: no inference is made. The pages drawn from these tests are
`specs/comprehension-harness/narratives/modeling.html` (`npm run comprehension:render`).
"""
from pathlib import Path
from unittest.mock import Mock

import pytest
from django.conf import settings as django_settings

from model_builder.adapters.repositories import SessionWorkspaceRepository
from model_builder.adapters.views import views_ai_bootstrap as views
from model_builder.application.ai_bootstrap.service import Completion
from model_builder.domain.services import is_empty_model
from tests.declare import narrative

pytestmark = pytest.mark.django_db
START = "/model_builder/start-ai-bootstrap/"
GENERATE = "/model_builder/generate-ai-bootstrap/"
ANSWER = (Path(django_settings.BASE_DIR) / "ai_sandbox/cases/_handwritten_01_recipe_app.json").read_text()
DESCRIPTION = "A recipe app: 200,000 monthly users browse recipes three times a week."


@pytest.fixture(autouse=True)
def configuration(settings, monkeypatch):
    settings.AI_BOOTSTRAP_ENABLED = True
    settings.MISTRAL_API_KEY = "dummy-server-key"
    settings.STORAGES = {**settings.STORAGES, "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")
    monkeypatch.setenv("USE_BOAVIZTAPI_PACKAGE", "1")


@pytest.fixture
def provider(monkeypatch):
    fake = Mock(return_value=Completion(ANSWER, 5000, 800, latency_s=12.5))
    monkeypatch.setattr(views, "complete_mistral", fake)
    return fake


def saved_modeling(client):
    return SessionWorkspaceRepository(client.session).active_repository().get_system_data()


@narrative("The user bootstraps a modeling from a description")
class TestAiBootstrap:
    """Starting with AI empties the active slot and opens a description panel. One provider request is then built
    into a library system, prepared like an import, saved once, and summarized in the response alone."""

    def test_a_description_becomes_a_saved_modeling_summarized_once(self, client, provider):
        started = client.post(START, HTTP_HX_REQUEST="true")
        assert 'data-ai-bootstrap-panel="input"' in started.content.decode()
        assert is_empty_model(saved_modeling(client))

        generated = client.post(GENERATE, {"description": DESCRIPTION})

        assert provider.call_count == 1 and provider.call_args.args[1] == DESCRIPTION
        assert 'data-ai-bootstrap-panel="summary"' in generated.content.decode()
        assert not is_empty_model(saved_modeling(client))
        assert "data-ai-bootstrap-panel" not in client.get("/model_builder/").content.decode()

    def test_a_provider_failure_keeps_the_empty_modeling_and_the_description(self, client, provider):
        provider.side_effect = views.ProviderError("unavailable")
        client.post(START)

        refused = client.post(GENERATE, {"description": DESCRIPTION})

        body = refused.content.decode()
        assert 'data-ai-bootstrap-panel="input"' in body and DESCRIPTION in body
        assert is_empty_model(saved_modeling(client))

    def test_an_answer_outside_the_schema_saves_nothing(self, client, provider):
        provider.return_value = Completion('{"servers": "not a list"}')
        client.post(START)

        refused = client.post(GENERATE, {"description": DESCRIPTION})

        assert 'data-ai-bootstrap-panel="input"' in refused.content.decode()
        assert is_empty_model(saved_modeling(client))
