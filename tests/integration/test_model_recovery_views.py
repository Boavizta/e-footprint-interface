"""Recovery escape hatch for a corrupt / unloadable session model.

A model that fails to deserialize would otherwise 500 the model-builder entry view, and since
the reset button lives on that very page the user is stuck with no way out (the dead state that
used to be escaped with the now-removed GET /model_builder/reboot). These tests pin the three
layers that replace it:

- model_builder_main falls back to the recovery page instead of 500 (RAISE_EXCEPTIONS still bubbles
  the raw traceback for debugging),
- /model_builder/recover/ is an always-reachable read-only escape hatch,
- /model_builder/download-raw-json/ serves the stored JSON verbatim (no ModelWeb rebuild) so the
  user can save their work, and reset-model recovers the session.
"""
import json
import copy

import pytest

from model_builder.adapters.repositories import SessionSystemRepository, SessionWorkspaceRepository


@pytest.fixture
def corrupt_system_data(minimal_system_data) -> dict:
    """A valid system with one referenced object class dropped -> dangling reference -> KeyError.

    Reproduces the real failure mode (Server references a Storage id that is no longer present),
    matching the user-reported `KeyError` raised deep in `from_json_dict`.
    """
    data = copy.deepcopy(minimal_system_data)
    data.pop("Storage")
    return data


@pytest.fixture(autouse=True)
def do_not_raise_view_exceptions(monkeypatch):
    # The recovery fallback is gated on RAISE_EXCEPTIONS being unset; make that explicit and robust
    # to whatever the ambient environment carries.
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)


@pytest.mark.django_db
def test_entry_view_renders_recovery_page_instead_of_500(client, corrupt_system_data):
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    response = client.get("/model_builder/")

    assert response.status_code == 200
    assert b"Reset to a blank model" in response.content
    assert b"Report this bug on GitHub" in response.content


@pytest.mark.django_db
def test_entry_view_still_raises_with_RAISE_EXCEPTIONS(client, corrupt_system_data, monkeypatch):
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    with pytest.raises(Exception):
        client.get("/model_builder/")


@pytest.mark.django_db
def test_recover_url_is_reachable_without_touching_the_model(client, corrupt_system_data):
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    response = client.get("/model_builder/recover/")

    assert response.status_code == 200
    assert b"Reset to a blank model" in response.content


@pytest.mark.django_db
def test_download_raw_json_serves_corrupt_data_verbatim(client, corrupt_system_data):
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    response = client.get("/model_builder/download-raw-json/")

    assert response.status_code == 200
    served = json.loads(response.content)
    # Served straight from the session: the dropped class is still absent (no ModelWeb rebuild).
    assert "Storage" not in served
    assert "Server" in served


@pytest.mark.django_db
def test_recovery_offers_one_download_link_per_occupied_slot(client, corrupt_system_data, minimal_system_data):
    """Two-model session: recovery must let the user rescue *each* slot's raw model, not just the
    active one, so neither model is lost from a dead state (per-slot raw download, dead-state-safe)."""
    session = client.session
    workspace = SessionWorkspaceRepository(session)
    workspace.active_repository().save_data(corrupt_system_data)  # slot 0 (corrupt)
    workspace.add_slot(minimal_system_data)                        # slot 1 (distinct id, valid)
    session.save()

    response = client.get("/model_builder/recover/")
    assert response.status_code == 200
    content = response.content.decode()
    # One labelled link per slot, each targeting that slot explicitly.
    assert 'href="/model_builder/download-raw-json/?slot=0"' in content
    assert 'href="/model_builder/download-raw-json/?slot=1"' in content
    assert "Download model A" in content
    assert "Download model B" in content


@pytest.mark.django_db
def test_recovery_single_slot_keeps_the_unlabelled_download_link(client, corrupt_system_data):
    """A single-model session keeps the original unlabelled "Download your current model" wording."""
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    content = client.get("/model_builder/recover/").content.decode()
    assert "Download your current model" in content
    assert 'href="/model_builder/download-raw-json/?slot=0"' in content
    assert "Download model A" not in content


@pytest.mark.django_db
def test_reset_recovers_a_corrupt_session(client, corrupt_system_data):
    SessionSystemRepository(client.session).save_data(corrupt_system_data)

    reset = client.post("/model_builder/reset-model/")
    assert reset.status_code == 302

    assert client.get("/model_builder/").status_code == 200
