"""View-layer integration tests for the combined workspace file.

Exercises the additive ``.e-f.json`` comparison export and the unified "Open file" import (upload-json
content-routes on the ``models`` key) through real Django views + session:

  - comparison export → "Open file" restores both slots + the active pointer in one action;
  - "Open file" fed a comparison file in a single-model session restores both slots (becomes two-model);
  - "Open file" fed a single-model file replaces the active model (single- or two-model session);
  - the combined budget is enforced on workspace import (summed with-calc over both slots);
  - the distinct-system-id invariant holds after importing a workspace whose two models share an id;
  - the single-model file format is byte-for-byte unchanged and round-trips both directions.

RAISE_EXCEPTIONS=1 so a crashing view surfaces as a non-200 instead of being absorbed into a modal —
except where a test deliberately asserts the graceful (modal) failure path, which clears it.
"""
import json
from copy import deepcopy

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from model_builder.version_upgrade_handlers import normalize_interface_config
from model_builder.adapters.repositories import SessionSystemRepository, SessionWorkspaceRepository
from model_builder.adapters.repositories.workspace_base import system_id_of
from model_builder.adapters.repositories.workspace_base import with_fresh_system_id
from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.forms.timeseries_builder_registry import can_edit_timeseries
from model_builder.application.use_cases.simplified_inputs import UpdateSimplifiedDefinitionUseCase
from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.services import SystemImportService
from model_builder.domain.services.simplified_inputs import build_catalog, validate_definition
from model_builder.domain.entities.web_core.model_web import ModelWeb
from efootprint.api_utils.system_to_json import system_to_json
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object


@pytest.fixture(autouse=True)
def raise_view_exceptions(monkeypatch):
    monkeypatch.setenv("RAISE_EXCEPTIONS", "1")


def _seed_active_slot(client, system, interface_config: dict = None) -> None:
    """Persist a built System into the active slot of the client's session (with-calc, recomputed).

    An optional ``interface_config`` (UI-only state, e.g. Sankey settings) is attached to the slot so
    tests can assert it survives an export/import round-trip.
    """
    raw = system_to_json(system, save_computed_state=False)
    import_service = SystemImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB)
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
        if isinstance(objs, dict) and cls not in ("System", "Sources", "calculation_graph", "interface_config")
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
    """Download both models → the envelope: version, active pointer, and two models[] that are
    each a byte-for-byte complete single-model document."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # slot 1 active

    envelope = _download(client, "/model_builder/download-workspace/")
    assert set(envelope) == {"efootprint_workspace_version", "active_slot", "models"}
    assert envelope["active_slot"] == 1  # the duplicate is active
    assert len(envelope["models"]) == 2
    for model in envelope["models"]:
        assert "System" in model and "efootprint_version" in model
        assert "calculation_graph" in model
        assert all("total_footprint" in system for system in model["System"].values())


@pytest.mark.django_db
def test_workspace_round_trip_restores_both_slots_and_active_pointer(client, minimal_system):
    # Slot 0 carries UI-only interface_config (Sankey settings); it must survive the round-trip per
    # slot. Slot 1 is a duplicate, which carries its own interface_config too.
    slot_0_config = {"sankey_diagrams": [{"id": "slot0cfg"}]}
    _seed_active_slot(client, minimal_system, interface_config=slot_0_config)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # slot 1 active = "Copy of …"
    workspace = SessionWorkspaceRepository(client.session)
    ids_before = [system_id_of(workspace.repository_for(s).get_system_data()) for s in workspace.list_slots()]

    envelope = _download(client, "/model_builder/download-workspace/")

    # Import it into a brand-new session.
    fresh = client.__class__()
    response = _upload(fresh, "/model_builder/upload-json/", envelope, "ws.e-f.json")
    assert response.status_code == 302  # redirects to the rebuilt builder

    restored = SessionWorkspaceRepository(fresh.session)
    assert restored.list_slots() == [0, 1]
    assert restored.active_slot() == 1  # the active pointer is restored
    ids_after = [system_id_of(restored.repository_for(s).get_system_data()) for s in restored.list_slots()]
    assert ids_after == ids_before  # both distinct system ids preserved through the round-trip
    names = [ModelWeb(restored.repository_for(s)).system.name for s in restored.list_slots()]
    assert names == ["Test System", "Copy of Test System"]
    # interface_config is restored per slot (it was dropped before the #1 fix).
    assert restored.repository_for(0).interface_config == normalize_interface_config(slot_0_config)


@pytest.mark.django_db
def test_single_model_file_via_open_file_replaces_the_active_model(client, minimal_system):
    """Unified "Open file" (upload-json) fed a single-model file replaces the active model — the single
    model loads into the active slot (content-based detection: no top-level `models` key)."""
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
    slots and becomes a two-model session (content-routed on the `models` key) — closing the gap
    where a single-model session previously had no way to open a workspace file."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    workspace_file = _download(client, "/model_builder/download-workspace/")

    # A plain single-model session opens the workspace file through the same "Open file" entry.
    fresh = client.__class__()
    _seed_active_slot(fresh, minimal_system)
    assert SessionWorkspaceRepository(fresh.session).list_slots() == [0]  # single-model to start
    response = _upload(fresh, "/model_builder/upload-json/", workspace_file, "ws.e-f.json")
    assert response.status_code == 302  # restored, redirects to the rebuilt builder

    restored = SessionWorkspaceRepository(fresh.session)
    assert restored.list_slots() == [0, 1]  # both slots restored
    names = [ModelWeb(restored.repository_for(s)).system.name for s in restored.list_slots()]
    assert names == ["Test System", "Copy of Test System"]


@pytest.mark.django_db
def test_open_workspace_file_after_suppressing_reference_restores_both_slots(client, minimal_system):
    """Regression: opening a workspace file when the sole surviving slot is slot 1 must restore both
    slots. Suppressing the Reference (slot 0 cross) promotes the Comparison into slot 1; _restore_workspace
    used to assume slot 0 existed and called remove_slot on the lone slot 1 → "can't drop the only slot"."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})  # two-model session
    workspace_file = _download(client, "/model_builder/download-workspace/")

    # Suppress the Reference (slot 0): the Comparison is promoted and now lives alone in slot 1.
    client.post("/model_builder/remove-model/", {"slot": "0"})
    assert SessionWorkspaceRepository(client.session).list_slots() == [1]  # the case that used to break

    response = _upload(client, "/model_builder/upload-json/", workspace_file, "ws.e-f.json")
    assert response.status_code == 302  # restored without error (no "can't drop the only slot")

    restored = SessionWorkspaceRepository(client.session)
    assert restored.list_slots() == [0, 1]  # cleanly re-packed to a canonical two-slot workspace
    names = [ModelWeb(restored.repository_for(s)).system.name for s in restored.list_slots()]
    assert names == ["Test System", "Copy of Test System"]


@pytest.mark.django_db
def test_workspace_import_enforces_combined_budget(client, minimal_system, monkeypatch):
    """The shared budget is summed over both slots on workspace import: a file whose two models fit
    individually but not together is rejected (the combined budget is summed over both slots). The over-budget add fails
    gracefully into the error modal while preserving both existing models."""
    _seed_active_slot(client, minimal_system)
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    envelope = _download(client, "/model_builder/download-workspace/")

    # A budget below the summed with-calc weight of both models, but above each one alone.
    with_calc = SystemImportService(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB).import_system(
        SessionSystemRepository.upgrade_system_data(envelope["models"][0]))
    one_model_mb = len(json.dumps(with_calc).encode()) / (1024 * 1024)
    monkeypatch.setattr(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", one_model_mb * 1.5)

    before = deepcopy(client.session)
    old_models = [deepcopy(SessionWorkspaceRepository(client.session).repository_for(slot).get_system_data())
                  for slot in [0, 1]]
    next(iter(envelope["models"][0]["System"].values()))["name"] = "Incoming replacement"
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)  # exercise the graceful modal path
    response = _upload(client, "/model_builder/upload-json/", envelope, "ws.e-f.json")
    assert response.status_code == 200
    assert "too large" in response.content.decode().lower()  # the budget message
    restored = SessionWorkspaceRepository(client.session)
    assert restored.list_slots() == [0, 1]
    assert dict(client.session) == dict(before)
    assert [restored.repository_for(slot).get_system_data() for slot in [0, 1]] == old_models


@pytest.mark.django_db
def test_workspace_import_with_shared_system_id_re_mints_a_distinct_one(client, minimal_system):
    """A workspace file whose two embedded models share a system id (e.g. a hand-edited file) must
    still produce two slots with distinct system ids — the add-to-slot path re-mints on collision."""
    shared_config = {"sankey_diagrams": [{"id": "shared"}]}
    _seed_active_slot(client, minimal_system, interface_config=shared_config)
    single_doc = _download(client, "/model_builder/download-json/")
    assert single_doc["interface_config"] == normalize_interface_config(shared_config)  # the export carries it
    # Build a workspace whose two models are the SAME single-model document (same system id).
    envelope = {"efootprint_workspace_version": "x", "active_slot": 0,
                "models": [single_doc, json.loads(json.dumps(single_doc))]}

    fresh = client.__class__()
    response = _upload(fresh, "/model_builder/upload-json/", envelope, "ws.e-f.json")
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
    assert restored.repository_for(0).interface_config == normalize_interface_config(shared_config)
    assert restored.repository_for(1).interface_config == normalize_interface_config(shared_config)


@pytest.mark.django_db
def test_single_model_format_is_unchanged_and_round_trips_both_directions(client, minimal_system):
    """The single-model file format is unchanged and circulates freely between
    single- and two-model sessions, both directions:

      - a per-slot export from a TWO-model session is structurally identical to the same model exported
        from a plain single-model session (no workspace contamination), and
      - that single-model file imports cleanly into a plain single-model session via "Open file".
    """
    # Single-model session export baseline.
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


@pytest.mark.django_db
def test_malformed_second_model_keeps_both_live_models_and_active_slot(client, minimal_system, monkeypatch):
    _seed_active_slot(client, minimal_system, {"simplified_inputs": {"title": "Reference", "fields": {}}})
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    workspace = SessionWorkspaceRepository(client.session)
    before = deepcopy(dict(client.session))
    old_models = [deepcopy(workspace.repository_for(slot).get_system_data()) for slot in workspace.list_slots()]
    envelope = _download(client, "/model_builder/download-workspace/")
    next(iter(envelope["models"][0]["System"].values()))["name"] = "Incoming replacement"
    envelope["models"][1]["Server"].clear()
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    response = _upload(client, "/model_builder/upload-json/", envelope, "ws.e-f.json")
    assert response.status_code == 200
    assert "not a valid e-footprint file" in response.content.decode().lower()
    restored = SessionWorkspaceRepository(client.session)
    assert restored.list_slots() == [0, 1]
    assert restored.active_slot() == 1
    assert dict(client.session) == before
    assert [restored.repository_for(slot).get_system_data() for slot in [0, 1]] == old_models


@pytest.mark.django_db
def test_duplicate_independent_definitions_remap_system_addresses_and_export(client, minimal_system):
    system_id = minimal_system.id
    journey = next(iter(minimal_system.usage_patterns[0].usage_journeys))
    step = next(iter(journey.uj_steps))
    server_id = next(iter(step.jobs)).server.id
    config = {"simplified_inputs": {"title": "Starter", "guidance": "Adapt", "fields": {
        system_id: {"name": {"included": False, "help": "System guidance"}},
        server_id: {"lifespan": {"included": True, "help": "Expected lifetime"}}}}}
    _seed_active_slot(client, minimal_system, config)
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    workspace = SessionWorkspaceRepository(client.session)
    duplicate_id = system_id_of(workspace.repository_for(1).get_system_data())
    copied_config = workspace.repository_for(1).interface_config
    copied_fields = copied_config["simplified_inputs"]["fields"]
    assert system_id not in copied_fields
    assert copied_fields[duplicate_id] == config["simplified_inputs"]["fields"][system_id]
    copied_fields[server_id]["lifespan"]["help"] = "Independent help"
    copied_repository = workspace.repository_for(1)
    copied_repository.interface_config = copied_config
    copied_repository.save_interface_config()
    assert workspace.repository_for(0).interface_config["simplified_inputs"] == config["simplified_inputs"]
    envelope = _download(client, "/model_builder/download-workspace/")
    assert envelope["models"][0]["interface_config"]["simplified_inputs"] == config["simplified_inputs"]
    assert envelope["models"][1]["interface_config"]["simplified_inputs"] == copied_config["simplified_inputs"]
    fresh = client.__class__()
    assert _upload(fresh, "/model_builder/upload-json/", envelope, "ws.e-f.json").status_code == 302
    restored = SessionWorkspaceRepository(fresh.session)
    for slot in [0, 1]:
        assert (restored.repository_for(slot).interface_config["simplified_inputs"]
                == envelope["models"][slot]["interface_config"]["simplified_inputs"])


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["duplicate", "add_import", "replace_import"])
def test_copy_preserves_disconnected_objects_and_their_selected_inputs(client, minimal_system, action):
    _seed_active_slot(client, minimal_system)
    session = client.session
    repository = SessionSystemRepository(session)
    server_id = create_object(repository, create_post_data_from_class_default_values(
        "Unused server", "Server",
        Storage_form_data=create_post_data_from_class_default_values("Unused storage", "Storage")))
    model = ModelWeb(repository)
    UpdateSimplifiedDefinitionUseCase(repository, build_catalog(
        model, can_edit_timeseries=can_edit_timeseries)).execute({"fields": {
            server_id: {"lifespan": {"included": True, "help": "Expected lifetime"}}}}, replace=True)
    session.save()
    document = _download(client, "/model_builder/download-json/")

    if action == "duplicate":
        response = client.post("/model_builder/add-model/", {"source": "duplicate"})
    else:
        file = SimpleUploadedFile("model.e-f.json", json.dumps(document).encode(), content_type="application/json")
        if action == "add_import":
            response = client.post("/model_builder/add-model/", {"source": "import", "import-json-input": file})
        else:
            client.post("/model_builder/add-model/", {"source": "blank"})
            response = client.post("/model_builder/upload-json/", {"import-json-input": file})
    assert response.status_code == (302 if action == "replace_import" else 200)

    copied_document = _download(client, "/model_builder/download-json/")
    assert system_id_of(copied_document) != system_id_of(document)
    assert _object_ids(copied_document) == _object_ids(document)
    assert copied_document["Server"][server_id] == document["Server"][server_id]
    assert copied_document["interface_config"] == document["interface_config"]
    copied_repository = SessionWorkspaceRepository(client.session).active_repository()
    copied_catalog = build_catalog(ModelWeb(copied_repository), can_edit_timeseries=can_edit_timeseries)
    assert validate_definition(copied_catalog, copied_repository.interface_config["simplified_inputs"]) == (
        document["interface_config"]["simplified_inputs"])


@pytest.mark.django_db
def test_rejected_single_import_cannot_publish_config_while_recovering_saved_model(client, minimal_system, monkeypatch):
    from django.core.cache import caches

    saved_config = {"simplified_inputs": {"title": "Saved", "guidance": "Saved guidance", "fields": {}}}
    _seed_active_slot(client, minimal_system, saved_config)
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    session = client.session
    workspace = SessionWorkspaceRepository(session)
    repository = workspace.active_repository()
    # Produce the normal compact Postgres recovery copy before expiring Redis.
    ModelWeb(repository).persist_to_cache()
    session.save()
    cache_key = repository._cache_key(create_if_missing=False)
    saved_recovery = deepcopy(caches[CacheBackend.POSTGRES_CACHE_ALIAS].get(cache_key))
    saved_fallback = deepcopy(session[SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY])
    incoming = _download(client, "/model_builder/download-json/")
    incoming["System"][system_id_of(incoming)]["name"] = "Incoming model"
    incoming["interface_config"]["simplified_inputs"] = {
        "title": "Incoming", "guidance": "New guidance " * 1000, "fields": {}}
    incoming_size = compute_json_size(SystemImportService(30).import_system(incoming)).size_bytes
    sizes = repository._index.slot_sizes()
    # Both existing models fit, and the incoming model fits alone, but replacing this slot exceeds the sum.
    budget_bytes = sum(sizes.values()) + (incoming_size - sizes[repository.slot]) // 2
    assert incoming_size < budget_bytes
    monkeypatch.setattr(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", budget_bytes / (1024 * 1024))
    caches[CacheBackend.REDIS_CACHE_ALIAS].delete(cache_key)
    writes, rejected = [], []
    real_set, real_save = CacheBackend.set, SessionSystemRepository.save_data

    def record_set(backend, key, value, **kwargs):
        if key == cache_key:
            writes.append(deepcopy(value))
        return real_set(backend, key, value, **kwargs)

    def record_save(repo, data, recovery_data=None):
        try:
            return real_save(repo, data, recovery_data)
        except PayloadSizeLimitExceeded:
            rejected.append((deepcopy(data["interface_config"]), len(writes)))
            raise

    monkeypatch.setattr(CacheBackend, "set", record_set)
    monkeypatch.setattr(SessionSystemRepository, "save_data", record_save)
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    response = _upload(client, "/model_builder/upload-json/", incoming, "incoming.e-f.json")
    assert response.status_code == 200
    assert "too large" in response.content.decode().lower()
    assert rejected == [(incoming["interface_config"], 0)]
    assert len(writes) == 2  # Only the ordinary old-model recovery publication occurred.
    for payload in writes:
        assert payload["interface_config"] == saved_config
        assert system_id_of(payload) == system_id_of(saved_recovery)
        assert (payload["System"][system_id_of(payload)]["name"]
                == saved_recovery["System"][system_id_of(saved_recovery)]["name"])
    assert writes[1] == saved_recovery
    assert caches[CacheBackend.POSTGRES_CACHE_ALIAS].get(cache_key) == saved_recovery
    assert client.session[SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY] == saved_fallback


@pytest.mark.django_db
@pytest.mark.parametrize("budget_margin", [-1, 1])
def test_workspace_preflight_measures_final_metadata_and_remapped_payload(
        client, minimal_system, monkeypatch, budget_margin):
    config = {"simplified_inputs": {"title": "Starter", "guidance": "Guide" * 100, "fields": {
        minimal_system.id: {"name": {"included": False, "help": "Authored System help"}}}}}
    _seed_active_slot(client, minimal_system, config)
    client.post("/model_builder/add-model/", {"source": "duplicate"})
    document = _download(client, "/model_builder/download-json/?slot=0")
    envelope = {"models": [deepcopy(document), deepcopy(document)], "active_slot": 0}
    imported_models = []
    real_import = SystemImportService.import_system

    def record_import(service, model):
        imported = real_import(service, model)
        imported_models.append(deepcopy(imported))
        return imported

    def measure_remapped_model(model):
        remapped = with_fresh_system_id(model)
        exact_size = compute_json_size(imported_models[0]).size_bytes + compute_json_size(remapped).size_bytes
        monkeypatch.setattr(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB",
                            (exact_size + budget_margin) / (1024 * 1024))
        return remapped

    monkeypatch.setattr(SystemImportService, "import_system", record_import)
    monkeypatch.setattr("model_builder.adapters.views.views_workspace.with_fresh_system_id", measure_remapped_model)
    old_models = [deepcopy(SessionWorkspaceRepository(client.session).repository_for(slot).get_system_data())
                  for slot in [0, 1]]
    before = deepcopy(dict(client.session))
    monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
    response = _upload(client, "/model_builder/upload-json/", envelope, "ws.e-f.json")
    restored = SessionWorkspaceRepository(client.session)
    if budget_margin < 0:
        assert response.status_code == 200
        assert "too large" in response.content.decode().lower()
        assert dict(client.session) == before
        assert [restored.repository_for(slot).get_system_data() for slot in [0, 1]] == old_models
    else:
        assert response.status_code == 302
        assert restored.active_slot() == 0
        ids = [system_id_of(restored.repository_for(slot).get_system_data()) for slot in [0, 1]]
        assert ids[0] != ids[1]
        for slot in [0, 1]:
            fields = restored.repository_for(slot).interface_config["simplified_inputs"]["fields"]
            assert fields[ids[slot]]["name"]["help"] == "Authored System help"
