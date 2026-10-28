"""The DEBUG-only local dev deep link: GET /dev/load-file/?path=<abs path>.

The AI sandbox report links to it so a generated ``.e-f.json`` lands on the canvas without the
manual upload. These tests pin that it loads the file, refuses paths outside the sandbox runs
folder, and is not routed at all when DEBUG is off.
"""
import json
from importlib import reload

import pytest
from django.conf import settings
from django.urls import clear_url_caches

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views import views_onboarding
from model_builder.domain.services import get_example_system_data


def _system_name(system_data: dict) -> str:
    return next(iter(system_data["System"].values()))["name"]


@pytest.fixture
def sandbox_run_file(tmp_path, monkeypatch):
    runs_dir = tmp_path / "ai_sandbox" / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setattr(views_onboarding, "LOCAL_FILE_ROOTS", (runs_dir,))
    exported = runs_dir / "case__model__r1.e-f.json"
    exported.write_text(json.dumps(get_example_system_data("ecommerce")))
    return exported


@pytest.fixture
def debug_urls(settings):
    """The route is appended only when DEBUG is true at URLconf import; rebuild the URLconf around it."""
    settings.DEBUG = True
    import e_footprint_interface.urls as urls
    reload(urls)
    clear_url_caches()
    yield
    settings.DEBUG = False
    reload(urls)
    clear_url_caches()


@pytest.mark.django_db
def test_loads_the_file_into_the_session_and_redirects_to_the_canvas(client, debug_urls, sandbox_run_file):
    response = client.get("/dev/load-file/", {"path": str(sandbox_run_file)})

    assert response.status_code == 302
    assert response.headers["Location"] == "/model_builder/"
    loaded = SessionSystemRepository(client.session).get_system_data()
    assert loaded is not None and _system_name(loaded) == _system_name(get_example_system_data("ecommerce"))


@pytest.mark.django_db
def test_refuses_files_outside_the_sandbox_runs_folder(client, debug_urls, sandbox_run_file, tmp_path):
    outside = tmp_path / "elsewhere.e-f.json"
    outside.write_text(sandbox_run_file.read_text())
    traversal = sandbox_run_file.parent / ".." / ".." / "elsewhere.e-f.json"

    assert client.get("/dev/load-file/", {"path": str(outside)}).status_code == 404
    assert client.get("/dev/load-file/", {"path": str(traversal)}).status_code == 404
    assert client.get("/dev/load-file/", {"path": str(sandbox_run_file.parent)}).status_code == 404
    assert client.get("/dev/load-file/").status_code == 404
    assert SessionSystemRepository(client.session).get_system_data() is None


@pytest.mark.django_db
def test_route_does_not_exist_when_debug_is_off(client, sandbox_run_file):
    assert settings.DEBUG is False
    assert client.get("/dev/load-file/", {"path": str(sandbox_run_file)}).status_code == 404
