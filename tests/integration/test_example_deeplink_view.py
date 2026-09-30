"""The docs' "Load this scenario" deep link: GET /example/<id>/.

The how-to pages link to ``{interface_base_url}/example/<example_id>/``; this view
loads that scenario into the session and redirects to the canvas. These tests pin
that the link actually loads the right scenario (not just any 200) and that a bad
id 404s like any other URL.
"""
import pytest

from model_builder.adapters.repositories import SessionSystemRepository, SessionWorkspaceRepository
from model_builder.adapters.repositories.workspace_base import system_id_of
from model_builder.domain.services import get_example_system_data


def _system_name(system_data: dict) -> str:
    return next(iter(system_data["System"].values()))["name"]


@pytest.mark.django_db
def test_deeplink_loads_the_named_scenario_and_redirects_to_the_canvas(client):
    expected_name = _system_name(get_example_system_data("ecommerce"))

    response = client.get("/example/ecommerce/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/model_builder/"
    loaded = SessionSystemRepository(client.session).get_system_data()
    assert loaded is not None and _system_name(loaded) == expected_name


@pytest.mark.django_db
def test_deeplink_resolves_a_how_to_example_too(client):
    """The how-to-only scenario (no introductory card) loads via the same link."""
    expected_name = _system_name(get_example_system_data("machine_learning_workflow"))

    response = client.get("/example/machine_learning_workflow/")

    assert response.status_code == 302
    loaded = SessionSystemRepository(client.session).get_system_data()
    assert loaded is not None and _system_name(loaded) == expected_name


@pytest.mark.django_db
def test_deeplink_lands_on_the_loaded_canvas_without_the_first_run_picker(client):
    response = client.get("/example/ecommerce/", follow=True)

    assert response.status_code == 200
    # A loaded model lands on the canvas, not the empty-model onboarding picker.
    assert b'id="example-picker"' not in response.content


@pytest.mark.django_db
def test_deeplink_replaces_active_slot_without_colliding_with_sibling(client, monkeypatch):
    """Loading the original example over its duplicate preserves distinct canvas namespaces."""
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")
    assert client.get("/example/ecommerce/").status_code == 302
    original = SessionWorkspaceRepository(client.session).repository_for(0).get_system_data()
    assert client.post("/model_builder/add-model/", {"source": "duplicate"}).status_code == 200

    response = client.get("/example/ecommerce/", follow=True)

    assert response.status_code == 200
    workspace = SessionWorkspaceRepository(client.session)
    assert workspace.list_slots() == [0, 1]
    assert workspace.active_slot() == 1
    assert workspace.repository_for(0).get_system_data() == original
    loaded = workspace.repository_for(1).get_system_data()
    assert _system_name(loaded) == _system_name(original)
    assert system_id_of(loaded) != system_id_of(original)


@pytest.mark.django_db
def test_deeplink_unknown_example_404s(client):
    assert client.get("/example/not-an-example/").status_code == 404
