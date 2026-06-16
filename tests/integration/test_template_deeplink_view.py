"""The docs' "Load this scenario" deep link: GET /template/<id>/.

The how-to pages link to ``{interface_base_url}/template/<template_id>/``; this view
loads that scenario into the session and redirects to the canvas. These tests pin
that the link actually loads the right scenario (not just any 200) and that a bad
id 404s like any other URL.
"""
import pytest

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.domain.services import get_template_system_data


def _system_name(system_data: dict) -> str:
    return next(iter(system_data["System"].values()))["name"]


@pytest.mark.django_db
def test_deeplink_loads_the_named_scenario_and_redirects_to_the_canvas(client):
    expected_name = _system_name(get_template_system_data("ecommerce"))

    response = client.get("/template/ecommerce/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/model_builder/"
    loaded = SessionSystemRepository(client.session).get_system_data()
    assert loaded is not None and _system_name(loaded) == expected_name


@pytest.mark.django_db
def test_deeplink_resolves_a_how_to_template_too(client):
    """The how-to-only scenario (no introductory card) loads via the same link."""
    expected_name = _system_name(get_template_system_data("machine_learning_workflow"))

    response = client.get("/template/machine_learning_workflow/")

    assert response.status_code == 302
    loaded = SessionSystemRepository(client.session).get_system_data()
    assert loaded is not None and _system_name(loaded) == expected_name


@pytest.mark.django_db
def test_deeplink_lands_on_the_loaded_canvas_without_the_first_run_picker(client):
    response = client.get("/template/ecommerce/", follow=True)

    assert response.status_code == 200
    # A loaded model lands on the canvas, not the empty-model onboarding picker.
    assert b'id="template-picker"' not in response.content


@pytest.mark.django_db
def test_deeplink_unknown_template_404s(client):
    assert client.get("/template/not-a-template/").status_code == 404
