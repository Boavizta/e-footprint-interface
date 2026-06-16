"""Shared workspace-repository logic: the slot lifecycle and the two load-bearing invariants.

``add_slot`` and ``remove_slot`` are identical across the session and in-memory implementations —
only how slots are registered and how a per-slot repository is vended differs. Keeping them here makes
this the *single enforcement point* for:

  - the distinct-system-id invariant (a fresh system id is minted on any cross-slot collision), and
  - the shared payload budget (delegated to the per-slot repository's save, which sums slot sizes).

Subclasses provide ``list_slots``, ``active_slot``, ``set_active_slot``, ``repository_for``, and the
``_register_slot`` / ``_deregister_slot`` hooks.
"""
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from model_builder.domain.interfaces import IWorkspaceRepository, ISystemRepository

MAX_SLOTS = 2


class WorkspaceRepositoryBase(IWorkspaceRepository):
    """Implements the slot lifecycle and the distinct-system-id invariant once for all backends."""

    @abstractmethod
    def _register_slot(self, slot: int) -> None:
        """Record ``slot`` as occupied in the backing index after its payload is saved."""

    @abstractmethod
    def _deregister_slot(self, slot: int) -> None:
        """Drop ``slot`` from the backing index after its payload is cleared."""

    def add_slot(self, system_data: Dict[str, Any]) -> int:
        slots = self.list_slots()
        new_slot = self._next_free_slot(slots)
        if new_slot is None:
            raise ValueError(f"Workspace already holds {MAX_SLOTS} models; remove one before adding another.")

        system_data = self._ensure_distinct_system_id(system_data, sibling_slots=slots)

        # The per-slot save enforces the shared budget (raises PayloadSizeLimitExceeded) before the
        # slot is registered, so a rejected add leaves the index untouched.
        self.repository_for(new_slot).save_data(system_data)
        self._register_slot(new_slot)
        return new_slot

    def remove_slot(self, slot: int) -> None:
        self.repository_for(slot).clear()
        self._deregister_slot(slot)

    def _next_free_slot(self, slots: List[int]) -> Optional[int]:
        for candidate in range(MAX_SLOTS):
            if candidate not in slots:
                return candidate
        return None

    def _ensure_distinct_system_id(self, system_data: Dict[str, Any], sibling_slots: List[int]) -> Dict[str, Any]:
        """Return ``system_data`` with a system id distinct from every sibling slot's.

        The comparison diff matches on *object* ids, so re-id-ing only the System is diff-safe.
        """
        incoming_id = system_id_of(system_data)
        if incoming_id is None:
            return system_data
        sibling_ids = {
            system_id_of(self.repository_for(slot).get_system_data()) for slot in sibling_slots
        }
        if incoming_id in sibling_ids:
            return with_fresh_system_id(system_data)
        return system_data


def system_id_of(system_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """The system id stored in a single-model document (the sole key under ``System``)."""
    if not system_data:
        return None
    return next(iter(system_data.get("System") or {}), None)


def with_fresh_system_id(system_data: Dict[str, Any]) -> Dict[str, Any]:
    """Re-id only the System object via the library helper, preserving every object id.

    Deserialize → ``assign_fresh_system_id`` → reserialize without calculated attributes (they are
    recomputed when the slot is loaded). Routing through the library keeps it the source of truth for
    id semantics and regenerates any reference to the system id from the live object graph.
    """
    from efootprint.api_utils.json_to_system import json_to_system
    from efootprint.api_utils.system_to_json import system_to_json
    from efootprint.comparison.duplication import assign_fresh_system_id
    from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT

    response_objs, _flat, _sd = json_to_system(
        system_data, launch_system_computations=False, efootprint_classes_dict=MODELING_OBJECT_CLASSES_DICT)
    system = next(iter(response_objs["System"].values()))
    assign_fresh_system_id(system)
    return system_to_json(system, save_calculated_attributes=False)
