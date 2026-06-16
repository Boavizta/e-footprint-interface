"""Unit tests for the workspace persistence layer (model-comparison Task 2).

Covers the slot-aware cache key + one-release legacy read-fallback, the workspace index lifecycle
(add / switch / remove), the shared payload budget (summed over slots, not per slot), and the
distinct-system-id invariant (an incoming id colliding with another slot is re-minted).
"""
from unittest.mock import patch

import pytest

from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository
from model_builder.adapters.repositories.session_workspace_repository import SessionWorkspaceRepository
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex
from model_builder.domain.exceptions import PayloadSizeLimitExceeded


class DictSession(dict):
    """Dict-backed session stand-in: real .get()/__contains__ plus session_key and a no-op save()."""

    def __init__(self):
        super().__init__()
        self.session_key = "session-key"
        self.modified = False

    def save(self):
        pass


def _data(system_id: str, payload: str = "x") -> dict:
    return {"efootprint_version": "22.1.0", "System": {system_id: {"id": system_id, "name": system_id}},
            "payload": payload}


# --------------------------------------------------------------------------- #
# Slot-aware cache key + legacy read-fallback
# --------------------------------------------------------------------------- #
class TestSlotAwareCacheKey:
    def test_default_slot_is_zero_and_key_is_suffixed(self):
        repo = SessionSystemRepository(DictSession())
        assert repo.slot == 0
        assert repo._cache_key() == "system_data:session-key:0"

    def test_explicit_slot_one_is_symmetric(self):
        repo = SessionSystemRepository(DictSession(), slot=1)
        assert repo.slot == 1
        assert repo._cache_key() == "system_data:session-key:1"

    def test_active_slot_followed_when_index_present(self):
        session = DictSession()
        WorkspaceIndex(session).add_slot(1)
        WorkspaceIndex(session).set_active_slot(1)
        assert SessionSystemRepository(session).slot == 1

    def test_legacy_unsuffixed_key_read_through_for_slot_zero(self):
        session = DictSession()
        repo = SessionSystemRepository(session)
        legacy_payload = _data("sys-legacy")

        reads = {}

        def fake_get_with_source(_self, cache_key):
            reads.setdefault("first", cache_key)
            if cache_key == "system_data:session-key":  # legacy unsuffixed
                return legacy_payload, "redis"
            return None, None

        sets, deletes = [], []
        with patch.object(CacheBackend, "get_with_source", autospec=True, side_effect=fake_get_with_source), \
             patch.object(CacheBackend, "set", autospec=True, side_effect=lambda _s, k, v, **kw: sets.append(k)), \
             patch.object(CacheBackend, "delete", autospec=True, side_effect=lambda _s, k: deletes.append(k)):
            data = repo.get_system_data()

        assert data == legacy_payload
        # Written through to the suffixed key and the legacy key is deleted (read at most once).
        assert "system_data:session-key:0" in sets
        assert deletes == ["system_data:session-key"]

    def test_no_legacy_fallback_for_slot_one(self):
        repo = SessionSystemRepository(DictSession(), slot=1)
        assert repo._legacy_cache_key() is None


# --------------------------------------------------------------------------- #
# Workspace index lifecycle
# --------------------------------------------------------------------------- #
class TestWorkspaceIndexLifecycle:
    def test_empty_index_is_single_model_slot_zero(self):
        index = WorkspaceIndex(DictSession())
        assert index.slots() == [0]
        assert index.active_slot() == 0

    def test_add_switch_remove(self):
        index = WorkspaceIndex(DictSession())
        index.add_slot(0)
        index.add_slot(1)
        assert index.slots() == [0, 1]

        index.set_active_slot(1)
        assert index.active_slot() == 1

        index.remove_slot(1)
        assert index.slots() == [0]
        assert index.active_slot() == 0  # active falls back to a surviving slot

    def test_cannot_activate_unoccupied_slot(self):
        index = WorkspaceIndex(DictSession())
        with pytest.raises(ValueError):
            index.set_active_slot(1)

    def test_workspace_repository_vends_slot_bound_repo(self):
        ws = SessionWorkspaceRepository(DictSession())
        assert ws.active_slot() == 0
        assert ws.repository_for(1).slot == 1
        assert ws.active_repository().slot == 0


# --------------------------------------------------------------------------- #
# Shared payload budget (summed over slots, not per slot)
# --------------------------------------------------------------------------- #
class TestSharedBudget:
    def test_summed_size_exceeds_budget_even_when_each_slot_fits(self):
        session = DictSession()
        ws = SessionWorkspaceRepository(session)
        # Record slot 0 as already weighing ~0.6 MB in the index.
        WorkspaceIndex(session).add_slot(0)
        WorkspaceIndex(session).set_slot_size(0, int(0.6 * 1024 * 1024))

        repo1 = ws.repository_for(1)
        # A ~0.6 MB slot-1 payload fits per slot but together exceeds a 1 MB shared budget.
        big = _data("sys-1", payload="x" * int(0.6 * 1024 * 1024))
        with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 1.0), \
             patch.object(CacheBackend, "set", autospec=True):
            with pytest.raises(PayloadSizeLimitExceeded):
                repo1.save_data(big)

    def test_single_slot_within_budget_saves(self):
        session = DictSession()
        repo = SessionSystemRepository(session)
        with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 1.0), \
             patch.object(CacheBackend, "set", autospec=True):
            repo.save_data(_data("sys-0"))
        assert WorkspaceIndex(session).slot_sizes()[0] > 0


# --------------------------------------------------------------------------- #
# Distinct-system-id invariant (verified on the in-memory workspace, where saves persist —
# the minting logic is shared with the session workspace via WorkspaceRepositoryBase)
# --------------------------------------------------------------------------- #
class TestDistinctSystemIdInvariant:
    def test_colliding_incoming_id_is_reminted_on_add(self, minimal_system_data):
        from model_builder.adapters.repositories import InMemoryWorkspaceRepository

        # Slot 0 is the primary model (seeded via initial_data); add_slot fills the next free slot.
        ws = InMemoryWorkspaceRepository(initial_data=minimal_system_data)
        slot1 = ws.add_slot(minimal_system_data)  # same document, colliding system id

        id0 = _system_id_from(ws.repository_for(0).get_system_data())
        id1 = _system_id_from(ws.repository_for(slot1).get_system_data())
        assert slot1 == 1
        assert id0 == _system_id_from(minimal_system_data)  # slot 0 keeps its id
        assert id1 != id0                                   # the colliding add re-minted to stay distinct

    def test_object_ids_preserved_when_system_id_reminted(self, minimal_system_data):
        from model_builder.adapters.repositories import InMemoryWorkspaceRepository

        ws = InMemoryWorkspaceRepository(initial_data=minimal_system_data)
        ws.add_slot(minimal_system_data)

        def object_ids(data):
            ids = set()
            for cls, objs in data.items():
                if isinstance(objs, dict) and cls not in ("System", "Sources"):
                    ids |= set(objs.keys())
            return ids

        # The comparison diff pairs objects by id, so re-id-ing only the System must leave object ids
        # shared between the two slots.
        assert object_ids(ws.repository_for(0).get_system_data()) == \
               object_ids(ws.repository_for(1).get_system_data())

    def test_distinct_incoming_id_is_left_unchanged(self, minimal_system_data):
        from model_builder.adapters.repositories import InMemoryWorkspaceRepository
        from model_builder.adapters.repositories.workspace_base import with_fresh_system_id

        # A second model whose id differs from slot 0's is stored unchanged.
        ws = InMemoryWorkspaceRepository(initial_data=minimal_system_data)
        distinct = with_fresh_system_id(minimal_system_data)
        distinct_id = _system_id_from(distinct)
        slot1 = ws.add_slot(distinct)
        assert _system_id_from(ws.repository_for(slot1).get_system_data()) == distinct_id


def _system_id_from(system_data):
    if not system_data:
        return None
    return next(iter(system_data.get("System") or {}), None)
