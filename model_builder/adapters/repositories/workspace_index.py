"""The tiny workspace index stored in the Django session.

The index is the single source of truth for which slots exist, which is active, and each slot's
last-saved with-calculated-attributes byte size. It is intentionally minimal: the heavy per-slot
payloads live in the cache (Redis/Postgres), keyed by slot; only this small bookkeeping lives in the
session. Both ``SessionSystemRepository`` (a per-slot repo) and ``SessionWorkspaceRepository`` (slot
lifecycle) operate on the same index, so the active slot and the shared budget stay consistent.

A session with no index behaves as a single-model session: one slot ``[0]`` active, which is exactly
today's behaviour.
"""
from typing import Dict, List

from django.contrib.sessions.backends.base import SessionBase

WORKSPACE_INDEX_SESSION_KEY = "workspace_index"


class WorkspaceIndex:
    """Read/write accessor for the workspace bookkeeping in a Django session."""

    def __init__(self, session: SessionBase):
        self._session = session

    def _raw(self) -> dict:
        return self._session.get(WORKSPACE_INDEX_SESSION_KEY) or {}

    def _write(self, index: dict) -> None:
        self._session[WORKSPACE_INDEX_SESSION_KEY] = index
        self._session.modified = True

    def slots(self) -> List[int]:
        """Occupied slots, defaulting to a single-model ``[0]`` when no index exists yet."""
        slots = self._raw().get("slots")
        return list(slots) if slots else [0]

    def active_slot(self) -> int:
        return self._raw().get("active", 0)

    def set_active_slot(self, slot: int) -> None:
        if slot not in self.slots():
            raise ValueError(f"Cannot activate slot {slot}: not an occupied slot ({self.slots()}).")
        index = self._raw()
        index["slots"] = self.slots()
        index["active"] = slot
        self._write(index)

    def add_slot(self, slot: int) -> None:
        index = self._raw()
        slots = self.slots()
        if slot not in slots:
            slots.append(slot)
        index["slots"] = sorted(slots)
        index.setdefault("active", 0)
        index.setdefault("sizes", {})
        self._write(index)

    def remove_slot(self, slot: int) -> None:
        index = self._raw()
        slots = [s for s in self.slots() if s != slot]
        index["slots"] = slots or [0]
        if index.get("active") == slot:
            index["active"] = index["slots"][0]
        self.forget_slot_size(slot)
        self._write(index)

    def slot_sizes(self) -> Dict[int, int]:
        """Per-slot last-saved with-calc byte sizes, keyed by int slot."""
        # Session JSON serialization stringifies dict keys; normalise back to int on read.
        return {int(k): v for k, v in self._raw().get("sizes", {}).items()}

    def set_slot_size(self, slot: int, size_bytes: int) -> None:
        index = self._raw()
        sizes = index.get("sizes", {})
        sizes[str(slot)] = size_bytes
        index["sizes"] = sizes
        if slot not in self.slots():
            index["slots"] = sorted(set(self.slots() + [slot]))
        index.setdefault("active", 0)
        self._write(index)

    def forget_slot_size(self, slot: int) -> None:
        index = self._raw()
        sizes = index.get("sizes", {})
        sizes.pop(str(slot), None)
        index["sizes"] = sizes
        self._write(index)

    def workspace_size_mb_with(self, slot: int, slot_size_bytes: int) -> float:
        """Summed with-calc weight (MB) over all slots, substituting ``slot_size_bytes`` for ``slot``.

        Sibling sizes come from the index, so the untouched slot is never re-serialized.
        """
        sizes = self.slot_sizes()
        sizes[slot] = slot_size_bytes
        return sum(sizes.values()) / (1024 * 1024)
