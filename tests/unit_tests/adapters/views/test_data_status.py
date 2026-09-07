import re
from unittest.mock import patch

import pytest
from django.test import Client

from model_builder.adapters.repositories.cache_backend import CacheBackend, CacheTouchOutcome
from model_builder.adapters.repositories.recovery_retention import (
    APPROVED_RECOVERY_RETENTION_SECONDS,
    RECOVERY_RETENTION_SESSION_KEY,
)
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex
from model_builder.adapters.views.data_status import build_data_status
from model_builder.domain.entities.web_core.model_web import ModelWeb


class DictSession(dict):
    session_key = "session-key"
    modified = False


def _configure_public_deployment(settings):
    settings.DATA_PRIVACY_OPERATOR_NAME = "Boavizta"
    settings.DATA_PRIVACY_HOSTING_PROVIDER_NAME = "Clever Cloud"
    settings.DATA_PRIVACY_HOSTING_REGION = "Paris"
    settings.DATA_PRIVACY_SECURITY_CONTACT = "security@example.org"
    settings.DATA_PRIVACY_HTTPS_ENABLED = True
    settings.DATA_PRIVACY_POSTGRES_ENCRYPTED_AT_REST = True
    settings.DATA_PRIVACY_POSTGRES_BACKUPS_ENABLED = True
    settings.DATA_PRIVACY_POSTGRES_BACKUP_FREQUENCY = "daily"
    settings.DATA_PRIVACY_POSTGRES_BACKUP_RETENTION_DAYS = 7
    settings.DATA_PRIVACY_POSTGRES_BACKUPS_ENCRYPTED_AT_REST = False
    settings.DATA_PRIVACY_POSTGRES_BACKUP_WINDOW = "overnight"
    settings.DATA_PRIVACY_PUBLIC_SHARED_INSTANCE = True


def test_data_status_uses_integer_workspace_metadata_and_configured_facts(settings):
    _configure_public_deployment(settings)
    session = DictSession()
    WorkspaceIndex(session).set_slot_size(0, 1 * 1024 * 1024)
    WorkspaceIndex(session).set_slot_size(1, 512 * 1024)

    with (
        patch.object(SessionSystemRepository, "REDIS_CACHE_TIMEOUT_SECONDS", 3600),
        patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 50),
        patch.object(SessionSystemRepository, "get_system_data", side_effect=AssertionError("must not hydrate")),
        patch.object(ModelWeb, "to_json", side_effect=AssertionError("must not serialize")),
    ):
        status = build_data_status(session)

    assert status.workspace_size_bytes == 1_572_864
    assert status.workspace_size_display == "1.5 MB"
    assert status.workspace_limit_display == "50 MB"
    assert status.hot_cache_retention_display == "1 hour"
    assert status.recovery_retention_display == "12 hours"
    assert [choice.seconds for choice in status.recovery_retention_choices] == list(APPROVED_RECOVERY_RETENTION_SECONDS)
    assert status.operator_name == "Boavizta"
    assert status.hosting_provider_name == "Clever Cloud"
    assert status.postgres_encrypted_at_rest is True
    assert status.postgres_backups_encrypted_at_rest is False


@pytest.mark.django_db
def test_data_privacy_partial_separates_storage_layers_and_renders_exact_retention_choices(client, settings):
    _configure_public_deployment(settings)
    session = client.session
    WorkspaceIndex(session).set_slot_size(0, 1_024)
    session.save()

    with (
        patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 50),
        patch.object(SessionSystemRepository, "get_system_data", side_effect=AssertionError("must not hydrate")),
        patch.object(ModelWeb, "to_json", side_effect=AssertionError("must not serialize")),
    ):
        response = client.get("/model_builder/data-privacy/", HTTP_HX_REQUEST="true")

    content = response.content.decode()
    option_values = [int(value) for value in re.findall(r'<option value="(\d+)"', content)]

    assert response.status_code == 200
    assert "<html" not in content
    assert 'id="sidePanelContent"' in content
    assert 'id="sidePanelTitle" class="h5 m-0" tabindex="-1"' in content
    assert ".focus({preventScroll: true})" in content
    assert option_values == list(APPROVED_RECOVERY_RETENTION_SECONDS)
    assert re.search(r'<option value="43200"\s+selected>', content)
    assert "opaque session identifier—not your modeling" in content
    assert "Redis hot cache" in content
    assert "Live PostgreSQL recovery storage" in content
    assert "Live PostgreSQL storage is encrypted at rest" in content
    assert "These backups are not encrypted at rest" in content
    assert "all data is encrypted" not in content.lower()
    assert "does not guarantee" in content
    assert "Boavizta" in content
    assert "Clever Cloud" in content
    assert "Paris" in content
    assert 'href="mailto:security@example.org"' in content
    assert "50 MB limit is a capacity policy for this shared public deployment" in content


@pytest.mark.django_db
def test_data_privacy_route_is_standalone_and_self_host_facts_are_not_assumed(client, settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    settings.DATA_PRIVACY_OPERATOR_NAME = ""
    settings.DATA_PRIVACY_HOSTING_PROVIDER_NAME = ""
    settings.DATA_PRIVACY_HOSTING_REGION = ""
    settings.DATA_PRIVACY_SECURITY_CONTACT = ""
    settings.DATA_PRIVACY_HTTPS_ENABLED = None
    settings.DATA_PRIVACY_POSTGRES_ENCRYPTED_AT_REST = None
    settings.DATA_PRIVACY_POSTGRES_BACKUPS_ENABLED = None
    settings.DATA_PRIVACY_POSTGRES_BACKUPS_ENCRYPTED_AT_REST = None
    settings.DATA_PRIVACY_POSTGRES_BACKUP_WINDOW = ""
    settings.DATA_PRIVACY_PUBLIC_SHARED_INSTANCE = False

    with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 8):
        response = client.get("/model_builder/data-privacy/")

    content = response.content.decode()
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in content
    assert "Clever Cloud" not in content
    assert "Boavizta" not in content
    assert "Paris" not in content
    assert "8 MB limit is the capacity policy configured for this deployment" in content
    assert "No at-rest encryption assurance is configured" in content
    assert "No PostgreSQL backup-lifecycle assurance is configured" in content
    assert "PostgreSQL backups are disabled" not in content


@pytest.mark.django_db
def test_retention_update_persists_the_choice_and_reports_each_saved_slot(client, settings):
    _configure_public_deployment(settings)
    session = client.session
    index = WorkspaceIndex(session)
    index.set_slot_size(0, 100)
    index.set_slot_size(1, 200)
    session.save()

    with patch.object(
        CacheBackend,
        "touch_postgres",
        autospec=True,
        side_effect=[CacheTouchOutcome.UPDATED, CacheTouchOutcome.MISSING],
    ) as touch:
        response = client.post(
            "/model_builder/recovery-retention/",
            {"retention_seconds": 6 * 3600},
            HTTP_HX_REQUEST="true",
        )

    content = response.content.decode()
    normalized_content = " ".join(content.split())
    assert response.status_code == 200
    assert client.session[RECOVERY_RETENTION_SESSION_KEY] == 6 * 3600
    assert touch.call_count == 2
    assert "Recovery retention is now 6 hours" in content
    assert "Reference modeling: existing recovery expiry updated" in normalized_content
    assert "Comparison modeling:" in normalized_content
    assert "had already" in normalized_content
    assert "storage was unavailable" not in normalized_content
    assert re.search(r'<option value="21600"\s+selected>', content)

    navigation_response = client.get("/model_builder/data-privacy/", HTTP_HX_REQUEST="true")
    assert re.search(r'<option value="21600"\s+selected>', navigation_response.content.decode())


@pytest.mark.django_db
def test_retention_update_reports_backend_failure_without_claiming_disappearance(client, settings):
    _configure_public_deployment(settings)
    session = client.session
    WorkspaceIndex(session).set_slot_size(0, 100)
    session.save()

    with patch.object(CacheBackend, "touch_postgres", autospec=True, return_value=CacheTouchOutcome.ERROR):
        response = client.post(
            "/model_builder/recovery-retention/",
            {"retention_seconds": 6 * 3600},
            HTTP_HX_REQUEST="true",
        )

    content = " ".join(response.content.decode().split())
    assert response.status_code == 200
    assert "alert-warning" in content
    assert "storage was unavailable" in content
    assert "had already expired" not in content


@pytest.mark.django_db
def test_retention_update_rejects_values_outside_the_allowlist(client):
    response = client.post("/model_builder/recovery-retention/", {"retention_seconds": 2 * 3600})

    assert response.status_code == 400
    assert RECOVERY_RETENTION_SESSION_KEY not in client.session


@pytest.mark.django_db
def test_retention_update_requires_csrf(settings):
    _configure_public_deployment(settings)
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.get("/model_builder/data-privacy/")

    response = csrf_client.post("/model_builder/recovery-retention/", {"retention_seconds": 3600})

    assert response.status_code == 403
