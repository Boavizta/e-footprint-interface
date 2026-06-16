"""View-layer integration tests for the combined workspace file (model-comparison Task 5).

Exercises the additive ``.e-fw.json`` workspace export and the unified "Open file" import (upload-json
content-routes on the ``models`` key — §4.1) through real Django views + session:

  - workspace export → "Open file" restores both slots + the active pointer in one action;
  - "Open file" fed a workspace file in a single-model session restores both slots (becomes two-model);
  - "Open file" fed a single-model file replaces the active model (single- or two-model session);
  - the combined budget is enforced on workspace import (summed with-calc over both slots);
  - the distinct-system-id invariant holds after importing a workspace whose two models share an id;
  - the single-model file format is byte-for-byte unchanged and round-trips both directions.

RAISE_EXCEPTIONS=1 so a crashing view surfaces as a non-200 instead of being absorbed into a modal —
except where a test deliberately asserts the graceful (modal) failure path, which clears it.
"""
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from model_builder.adapters.repositories import SessionSystemRepository, SessionWorkspaceRepository
from model_builder.adapters.repositories.workspace_base import system_id_of
from model_builder.domain.services import ProgressiveImportService
from model_builder.domain.entities.web_core.model_web import ModelWeb
from efootprint.api_utils.system_to_json import system_to_json


@pytest.fixture(autouse=True)
def raise_view_exceptions(monkeypatch):
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")


def _seed_active_slot(client, system, interface_config: dict = None) -> None:
    """Persist a built System into the active slot of the client's session (with-calc, recomputed).

    An optional ``interface_config`` (UI-only state, e.g. Sankey settings) is attached to the slot so
    tests can assert it survives an export/import round-trip.
    """
    raw = system_to_json(system, save_calculated_attributes=False)
    import_service = ProgressiveImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
    with_calc = import_service.import_system(SessionSystemRepository.upgrade_system_data(raw))
    session = client.session
    repository = SessionWorkspaceRepository(session).active_repository()
    if interface_config is not None:
        repository.interface_config = interface_config
    repository.save_data(with_calc)
    session.save()


def _object_ids(system_data: dict) -> set:
    return {
        object_id
        for cls, objs in system_data.items()
        if isinstance(objs, dict) and cls not in ("System", "Sources")
        for object_id in objs
    }


def _download(client, url) -> dict:
    response = client.get(url)
    assert response.status_code == 200
    return json.loads(response.content)


def _upload(client, url, payload: dict, filename: str):
    file = SimpleUploadedFile(filename, json.dumps(payload).encode(), content_type="application/json")
    return client.post(url, {"import-json-input": file})


@pytest.mark.django_db
def test_workspace_export_is_an_envelope_of_two_single_model_documents(client, minimal_system):
    """Download Both models → the §2.7 envelope: version, active pointer, and two models[] that are
    each a byte-for-byte single-model document (no calculated attributes)."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # slot 1 active

    envelope = _download(client, "/model_builder/download-workspace/")
    assert set(envelope) == {"efootprint_workspace_version", "active_slot", "models"}
    assert envelope["active_slot"] == 1  # the duplicate is active
    assert len(envelope["models"]) == 2
    for model in envelope["models"]:
        assert "System" in model and "efootprint_version" in model
        # No calculated attributes are stored in the file (recomputed on import).
        assert all("calculated_attributes" not in obj for objs in model.values()
                   if isinstance(objs, dict) for obj in objs.values() if isinstance(obj, dict))


@pytest.mark.django_db
def test_workspace_round_trip_restores_both_slots_and_active_pointer(client, minimal_system):
    # Slot 0 carries UI-only interface_config (Sankey settings); it must survive the round-trip per
    # slot (plan §2.7). Slot 1 is a duplicate, which carries its own interface_config too.
    slot_0_config = {"sankey_diagrams": [{"id": "slot0cfg"}]}
    _seed_active_slot(client, minimal_system, interface_config=slot_0_config)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # slot 1 active = "Copy of …"
    workspace = SessionWorkspaceRepository(client.session)
    ids_before = [system_id_of(workspace.repository_for(s).get_system_data()) for s in workspace.list_slots()]

    envelope = _download(client, "/model_builder/download-workspace/")

    # Import it into a brand-new session.
    fresh = client.__class__()
    response = _upload(fresh, "/model_builder/upload-json/", envelope, "ws.e-fw.json")
    assert response.status_code == 302  # redirects to the rebuilt builder

    restored = SessionWorkspaceRepository(fresh.session)
    assert restored.list_slots() == [0, 1]
    assert restored.active_slot() == 1  # the active pointer is restored
    ids_after = [system_id_of(restored.repository_for(s).get_system_data()) for s in restored.list_slots()]
    assert ids_after == ids_before  # both distinct system ids preserved through the round-trip
    names = [ModelWeb(restored.repository_for(s)).system.name for s in restored.list_slots()]
    assert names == ["Test System", "Copy of Test System"]
    # interface_config is restored per slot (it was dropped before the #1 fix).
    assert restored.repository_for(0).interface_config == slot_0_config


@pytest.mark.django_db
def test_single_model_file_via_open_file_replaces_the_active_model(client, minimal_system):
    """Unified "Open file" (upload-json) fed a single-model file replaces the active model — the single
    model loads into the active slot (content-based detection: no top-level `models` key, §4.1)."""
    _seed_active_slot(client, minimal_system)
    single_doc = _download(client, "/model_builder/download-json/")
    assert "models" not in single_doc  # it is a single-model file

    fresh = client.__class__()
    response = _upload(fresh, "/model_builder/upload-json/", single_doc, "model.e-f.json")
    assert response.status_code == 302

    restored = SessionWorkspaceRepository(fresh.session)
    assert restored.list_slots() == [0]  # one model loaded into the active slot, no second slot
    assert ModelWeb(restored.active_repository()).system.name == "Test System"


@pytest.mark.django_db
def test_workspace_file_via_open_file_in_single_model_session_restores_both_slots(client, minimal_system):
    """Unified "Open file" (upload-json) fed a workspace file in a single-model session restores both
    slots and becomes a two-model session (content-routed on the `models` key, §4.1) — closing the gap
    where a single-model session previously had no way to open a workspace file."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    workspace_file = _download(client, "/model_builder/download-workspace/")

    # A plain single-model session opens the workspace file through the same "Open file" entry.
    fresh = client.__class__()
    _seed_active_slot(fresh, minimal_system)
    assert SessionWorkspaceRepository(fresh.session).list_slots() == [0]  # single-model to start
    response = _upload(fresh, "/model_builder/upload-json/", workspace_file, "ws.e-fw.json")
    assert response.status_code == 302  # restored, redirects to the rebuilt builder

    restored = SessionWorkspaceRepository(fresh.session)
    assert restored.list_slots() == [0, 1]  # both slots restored
    names = [ModelWeb(restored.repository_for(s)).system.name for s in restored.list_slots()]
    assert names == ["Test System", "Copy of Test System"]


@pytest.mark.django_db
def test_workspace_import_enforces_combined_budget(client, minimal_system, monkeypatch):
    """The shared budget is summed over both slots on workspace import: a file whose two models fit
    individually but not together is rejected (constitution / plan §4). The over-budget add fails
    gracefully into the error modal (not a 500), leaving the session a clean single-model workspace."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    envelope = _download(client, "/model_builder/download-workspace/")

    # A budget below the summed with-calc weight of both models, but above each one alone.
    with_calc = ProgressiveImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB).import_system(
        SessionSystemRepository.upgrade_system_data(envelope["models"][0]))
    one_model_mb = len(json.dumps(with_calc).encode()) / (1024 * 1024)
    monkeypatch.setattr(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", one_model_mb * 1.5)

    fresh = client.__class__()
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)  # exercise the graceful modal path
    response = _upload(fresh, "/model_builder/upload-json/", envelope, "ws.e-fw.json")
    assert response.status_code == 200
    assert "too large" in response.content.decode().lower()  # the budget message
    # The first model loaded into slot 0 but the second was rejected before changing the slot index.
    restored = SessionWorkspaceRepository(fresh.session)
    assert restored.list_slots() == [0]


@pytest.mark.django_db
def test_workspace_import_with_shared_system_id_re_mints_a_distinct_one(client, minimal_system):
    """A workspace file whose two embedded models share a system id (e.g. a hand-edited file) must
    still produce two slots with distinct system ids — the add-to-slot path re-mints on collision."""
    shared_config = {"sankey_diagrams": [{"id": "shared"}]}
    _seed_active_slot(client, minimal_system, interface_config=shared_config)
    single_doc = _download(client, "/model_builder/download-json/")
    assert single_doc["interface_config"] == shared_config  # the export carries it
    # Build a workspace whose two models are the SAME single-model document (same system id).
    envelope = {"efootprint_workspace_version": "x", "active_slot": 0,
                "models": [single_doc, json.loads(json.dumps(single_doc))]}

    fresh = client.__class__()
    response = _upload(fresh, "/model_builder/upload-json/", envelope, "ws.e-fw.json")
    assert response.status_code == 302

    restored = SessionWorkspaceRepository(fresh.session)
    assert restored.list_slots() == [0, 1]
    id0 = system_id_of(restored.repository_for(0).get_system_data())
    id1 = system_id_of(restored.repository_for(1).get_system_data())
    assert id0 != id1  # re-minted (web_id DOM-prefix invariant)
    # Object ids are preserved, so the comparison diff still pairs by identity.
    assert _object_ids(restored.repository_for(0).get_system_data()) == \
           _object_ids(restored.repository_for(1).get_system_data())
    # interface_config survives the re-mint on the collision slot (with_fresh_system_id preserves it).
    assert restored.repository_for(0).interface_config == shared_config
    assert restored.repository_for(1).interface_config == shared_config


@pytest.mark.django_db
def test_single_model_format_is_unchanged_and_round_trips_both_directions(client, minimal_system):
    """The single-model file format is byte-for-byte unchanged by Task 5 and circulates freely between
    single- and two-model sessions, both directions:

      - a per-slot export from a TWO-model session is structurally identical to the same model exported
        from a plain single-model session (no workspace contamination), and
      - that single-model file imports cleanly into a plain single-model session via "Open file".
    """
    # Single-model session export = the pre-Task-5 baseline.
    _seed_active_slot(client, minimal_system)
    single_session_doc = _download(client, "/model_builder/download-json/")

    # Two-model session: export slot 0 explicitly — must equal the single-session export of that model.
    two_model = client.__class__()
    _seed_active_slot(two_model, minimal_system)
    two_model.post("/model_builder/add-model/", {"source": "blank"})  # now a two-model session
    slot0_doc = _download(two_model, "/model_builder/download-json/?slot=0")
    assert slot0_doc == single_session_doc  # byte-for-byte identical; workspace never alters the format

    # Direction 2: the single-model file imports into a plain single-model session unchanged.
    fresh = client.__class__()
    file = SimpleUploadedFile("model.e-f.json", json.dumps(single_session_doc).encode(),
                              content_type="application/json")
    response = fresh.post("/model_builder/upload-json/", {"import-json-input": file})
    assert response.status_code == 302
    restored = SessionWorkspaceRepository(fresh.session)
    assert restored.list_slots() == [0]
    assert ModelWeb(restored.active_repository()).system.name == "Test System"


@pytest.mark.django_db
def test_single_model_file_via_open_file_in_two_model_session_replaces_active_slot(client, minimal_system):
    """Unified "Open file" fed a single-model file in a TWO-model session replaces the ACTIVE slot (and
    only that slot) — "Open file" is open-into-here; adding a second model is the tab strip's job."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "blank"})  # slot 1 active, two-model session
    workspace = SessionWorkspaceRepository(client.session)
    assert workspace.list_slots() == [0, 1] and workspace.active_slot() == 1
    slot_0_id_before = system_id_of(workspace.repository_for(0).get_system_data())

    # A distinct single-model file (renamed) opened while slot 1 is active replaces slot 1 only.
    single_doc = _download(client, "/model_builder/download-json/?slot=0")
    single_doc["System"][next(iter(single_doc["System"]))]["name"] = "Opened Into Active"
    response = _upload(client, "/model_builder/upload-json/", single_doc, "model.e-f.json")
    assert response.status_code == 302

    after = SessionWorkspaceRepository(client.session)
    assert after.list_slots() == [0, 1]  # still two models, no third slot added
    assert ModelWeb(after.repository_for(1)).system.name == "Opened Into Active"  # active slot replaced
    assert system_id_of(after.repository_for(0).get_system_data()) == slot_0_id_before  # slot 0 untouched
