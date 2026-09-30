import pytest

from model_builder.adapters.repositories import SessionSystemRepository


@pytest.mark.django_db
def test_object_deletion_requires_post_and_confirmation_uses_it(client, minimal_system_data):
    repository = SessionSystemRepository(client.session)
    repository.save_data(minimal_system_data)
    object_id = next(iter(minimal_system_data["UsagePattern"]))
    url = f"/model_builder/delete-object/{object_id}/"
    saved_before = repository.get_system_data()

    confirmation = client.get(f"/model_builder/ask-delete-object/{object_id}/")
    assert f'hx-post="{url}"' in confirmation.content.decode()
    assert 'hx-target="#modal-container"' in confirmation.content.decode()
    assert 'hx-swap="none"' in confirmation.content.decode()
    assert client.get(url).status_code == 405
    assert repository.get_system_data() == saved_before

    response = client.post(url)
    assert response.status_code == 200
    assert "openModalDialog" not in response.headers.get("HX-Trigger-After-Settle", "")
    assert object_id not in SessionSystemRepository(client.session).get_system_data().get("UsagePattern", {})
