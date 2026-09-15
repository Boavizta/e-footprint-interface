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


def test_data_status_uses_integer_workspace_metadata():
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


@pytest.mark.parametrize(
    ("workspace_limit_mb", "workspace_size_bytes", "expected_warning"),
    [
        (5, 4 * 1024 * 1024 - 1, False),
        (5, 4 * 1024 * 1024, True),
        (5, 5 * 1024 * 1024, True),
        (0.001, 838, False),
        (0.001, 839, True),
    ],
)
def test_workspace_storage_warning_uses_the_exact_eighty_percent_boundary(
    workspace_limit_mb, workspace_size_bytes, expected_warning
):
    session = DictSession()
    WorkspaceIndex(session).set_slot_size(0, workspace_size_bytes)

    with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", workspace_limit_mb):
        status = build_data_status(session)

    assert status.show_workspace_storage_warning is expected_warning


@pytest.mark.django_db
def test_workspace_storage_status_is_metadata_only_and_keeps_one_accessible_oob_region(client):
    session = client.session
    WorkspaceIndex(session).set_slot_size(0, 4 * 1024 * 1024)
    session.save()

    with (
        patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 5),
        patch.object(SessionSystemRepository, "get_system_data", side_effect=AssertionError("must not hydrate")),
        patch.object(ModelWeb, "to_json", side_effect=AssertionError("must not serialize")),
    ):
        response = client.get("/model_builder/workspace-storage-status/", HTTP_HX_REQUEST="true")

    content = response.content.decode()
    assert response.status_code == 200
    assert content.count('id="workspace-storage-status"') == 1
    assert 'hx-swap-oob="innerHTML:#workspace-storage-status"' in content
    assert content.count('aria-live="polite"') == 1
    assert 'role="status"' not in content
    assert "4 MB of 5 MB" in content
    assert 'href="/model_builder/data-privacy/"' in content
    assert "Workspace storage is nearly full" in content


@pytest.mark.django_db
def test_workspace_storage_status_is_visually_empty_below_the_warning_threshold(client):
    session = client.session
    WorkspaceIndex(session).set_slot_size(0, 4 * 1024 * 1024 - 1)
    session.save()

    with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 5):
        response = client.get("/model_builder/workspace-storage-status/")

    content = response.content.decode()
    assert 'id="workspace-storage-status"' in content
    assert "Workspace storage is nearly full" not in content
    assert "MB of 5 MB" not in content


@pytest.mark.django_db
def test_full_builder_render_contains_one_stable_storage_status_region(client, minimal_system_data, settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    SessionSystemRepository(client.session).save_data(minimal_system_data)

    response = client.get("/model_builder/")

    content = response.content.decode()
    assert response.status_code == 200
    assert content.count('id="workspace-storage-status"') == 1
    assert 'aria-live="polite"' in content
    assert "Workspace storage is nearly full" not in content


@pytest.mark.django_db
def test_result_materialization_response_refreshes_workspace_storage_status(client, minimal_system_data):
    SessionSystemRepository(client.session).save_data(minimal_system_data)

    response = client.get("/model_builder/result-chart/", HTTP_HX_REQUEST="true")

    content = response.content.decode()
    assert response.status_code == 200
    assert content.count('id="workspace-storage-status"') == 1
    assert 'hx-swap-oob="innerHTML:#workspace-storage-status"' in content


@pytest.mark.django_db
def test_data_privacy_partial_separates_storage_layers_and_renders_exact_retention_choices(client):
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
    normalized_content = " ".join(content.split())
    option_values = [int(value) for value in re.findall(r'<option value="(\d+)"', content)]

    assert response.status_code == 200
    assert "<html" not in content
    assert 'id="sidePanelContent"' in content
    assert 'id="sidePanelTitle" class="h5 m-0" tabindex="-1"' in content
    assert ".focus({preventScroll: true})" in content
    assert option_values == list(APPROVED_RECOVERY_RETENTION_SECONDS)
    assert re.search(r'<option value="43200"\s+selected>', content)
    assert "opaque session identifier—not your modeling" in content
    assert "How your modeling is stored" in content
    assert "In your browser" in content
    assert "For fast access" in content
    assert "For recovery" in content
    assert ">Browser session</h2>" not in content
    assert ">Redis hot cache</h2>" not in content
    assert ">Live PostgreSQL recovery storage</h2>" not in content
    assert "Live PostgreSQL storage and the Redis hot cache are encrypted at rest" in content
    assert "are not encrypted at rest" in normalized_content
    assert "Redis backups are being disabled" in content
    assert "TLS protection for the connection between the application and Redis is being set up" in normalized_content
    assert "Backup encryption is being set up" in content
    assert '<h2 id="security-heading" class="h6 fw-semibold">Security</h2>' in content
    assert ">Protection</h2>" not in content
    assert ">PostgreSQL backups</h2>" not in content
    assert ">Operation, hosting &amp; security</h2>" not in content
    assert "all data is encrypted" not in content.lower()
    assert "does not guarantee" in content
    assert "Boavizta" in content
    assert "Clever Cloud" in content
    assert "Paris" in content
    assert 'href="mailto:vincent.villet@publicissapient.com"' in content
    assert "50 MB limit is a capacity policy for this shared public deployment" in content
    assert content.index("How your modeling is stored") < content.index("Workspace storage")
    assert content.index("Workspace storage") < content.index("Recovery retention")
    assert content.index("Recovery retention") < content.index("Security")


@pytest.mark.django_db
def test_data_privacy_route_is_standalone(client, settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 8):
        response = client.get("/model_builder/data-privacy/")

    content = response.content.decode()
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in content
    assert "Operated by Boavizta" in content
    assert "Clever Cloud" in content
    assert "hosted in Paris" in content
    assert "8 MB limit is a capacity policy for this shared public deployment" in content
    assert "Redis backups are being disabled" in content
    assert "TLS protection" in content
    assert "Backup encryption is being set up" in content


@pytest.mark.django_db
def test_retention_update_persists_the_choice_and_reports_each_saved_slot(client):
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
def test_retention_update_reports_backend_failure_without_claiming_disappearance(client):
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
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.get("/model_builder/data-privacy/")

    response = csrf_client.post("/model_builder/recovery-retention/", {"retention_seconds": 3600})

    assert response.status_code == 403
