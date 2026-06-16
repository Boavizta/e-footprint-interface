"""Integration tests for the workspace persistence layer (model-comparison Task 2).

Runs adapters → domain through the in-memory workspace, with no Django session scaffolding — so it
doubles as the Clean-Architecture no-Django-in-domain guard for ``IWorkspaceRepository`` (the domain
port imports cleanly here, where Django is never set up).
"""
import json

from model_builder.adapters.repositories import InMemoryWorkspaceRepository
from model_builder.adapters.repositories.workspace_base import system_id_of
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.services.template_catalog_service import INTRO_TEMPLATES


def _object_ids(system_data: dict) -> set:
    ids = set()
    for cls, objs in system_data.items():
        if isinstance(objs, dict) and cls not in ("System", "Sources"):
            ids |= set(objs.keys())
    return ids


def test_workspace_add_switch_remove(minimal_system_data):
    ws = InMemoryWorkspaceRepository(initial_data=minimal_system_data)
    assert ws.list_slots() == [0]
    assert ws.active_slot() == 0

    slot1 = ws.add_slot(minimal_system_data)
    assert slot1 == 1
    assert ws.list_slots() == [0, 1]

    ws.set_active_slot(1)
    assert ws.active_slot() == 1
    assert ws.active_repository() is ws.repository_for(1)

    ws.remove_slot(1)
    assert ws.list_slots() == [0]
    assert ws.active_slot() == 0  # active falls back to the surviving slot


def test_importing_same_template_into_both_slots_gets_distinct_system_ids():
    raw = json.loads(open(INTRO_TEMPLATES[0].json_path).read())

    ws = InMemoryWorkspaceRepository(initial_data=raw)
    ws.add_slot(raw)  # same template document into the second slot

    data0 = ws.repository_for(0).get_system_data()
    data1 = ws.repository_for(1).get_system_data()
    assert system_id_of(data0) != system_id_of(data1)        # distinct system ids
    assert _object_ids(data0) == _object_ids(data1)          # object ids preserved (diff pairs by id)

    # Both slots still load into a computable model.
    assert ModelWeb(ws.repository_for(0)).system is not None
    assert ModelWeb(ws.repository_for(1)).system is not None


def test_single_model_session_behaves_as_before(minimal_system_data):
    """A workspace that never adds a second model is indistinguishable from today's single-model flow:
    one slot, active 0, and the model loads, edits-persist, and round-trips through slot 0 unchanged."""
    ws = InMemoryWorkspaceRepository(initial_data=minimal_system_data)
    repo = ws.active_repository()

    assert ws.list_slots() == [0]
    model_web = ModelWeb(repo)
    assert model_web.system is not None
    original_id = system_id_of(repo.get_system_data())

    model_web.persist_to_cache()  # an edit-save cycle
    assert ws.list_slots() == [0]
    assert ws.active_slot() == 0
    assert system_id_of(repo.get_system_data()) == original_id  # no re-id, no second slot


def test_shared_budget_rejects_oversized_second_model(minimal_system_data):
    """The budget is summed over slots: a second model that fits alone but not together is rejected."""
    from model_builder.domain.exceptions import PayloadSizeLimitExceeded

    one_model_mb = len(json.dumps(minimal_system_data).encode()) / (1024 * 1024)
    # Budget just above one model but below two.
    ws = InMemoryWorkspaceRepository(initial_data=minimal_system_data, max_payload_size_mb=one_model_mb * 1.5)
    try:
        ws.add_slot(minimal_system_data)
        assert False, "expected the summed budget to reject the second model"
    except PayloadSizeLimitExceeded:
        assert ws.list_slots() == [0]  # rejected add leaves the workspace single-model
