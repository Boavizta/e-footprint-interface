import copy
import json

import pytest

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb


@pytest.fixture
def corrupt_system_data(minimal_system_data):
    data = copy.deepcopy(minimal_system_data)
    data.pop("Storage")
    return data


@pytest.fixture(autouse=True)
def fail_if_recovery_hydrates(monkeypatch):
    def reject_hydration(*args, **kwargs):
        raise AssertionError("Recovery must not hydrate a model")

    monkeypatch.setattr(ModelWeb, "__init__", reject_hydration)


@pytest.mark.django_db
def test_recovery_offers_safe_github_email_and_manual_attachment_guidance(client, corrupt_system_data):
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    response = client.get("/model_builder/recover/")
    content = response.content.decode()

    assert response.status_code == 200
    assert "Report this bug on GitHub" in content
    assert "Report this bug by email" in content
    assert "GitHub issues and their attachments are public" in content
    assert "attach it manually" in content


@pytest.mark.django_db
def test_recovery_download_serves_raw_corrupt_data_without_hydration(client, corrupt_system_data):
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    response = client.get("/model_builder/download-raw-json/")

    assert response.status_code == 200
    assert "Storage" not in json.loads(response.content)


@pytest.mark.django_db
def test_recovery_feedback_keeps_the_download_path_hydration_free(client, corrupt_system_data, settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    recovery = client.get("/model_builder/recover/")
    assert 'href="/support/?recovery=1"' in recovery.content.decode()

    support = client.get("/support/?recovery=1")
    assert support.status_code == 200
    assert 'href="/model_builder/download-raw-json/"' in support.content.decode()

    download = client.get("/model_builder/download-raw-json/")
    assert download.status_code == 200
    assert "Storage" not in json.loads(download.content)
