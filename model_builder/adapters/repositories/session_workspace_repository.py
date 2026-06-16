"""Session-backed implementation of IWorkspaceRepository.

Owns the workspace slot index in the Django session (which slots exist, which is active, and each
slot's last-saved with-calc byte size) and vends a ``SessionSystemRepository`` bound to a slot. Two
invariants are enforced here as the single point for the whole feature:

  - the *summed* with-calc weight of all slots stays within ``MAX_PAYLOAD_SIZE_MB`` (the per-slot
    repository checks the budget on every save from the index; ``add_slot`` pre-checks it here too);
  - the two slots never hold the same system id — ``add_slot`` mints a fresh system id on any
    cross-slot collision, covering every source (import, workspace import, template, blank, duplicate).
"""
from typing import List

from django.contrib.sessions.backends.base import SessionBase

from model_builder.domain.interfaces import ISystemRepository
from model_builder.adapters.repositories.workspace_base import WorkspaceRepositoryBase
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex


class SessionWorkspaceRepository(WorkspaceRepositoryBase):
    """Django-session-backed workspace repository."""

    def __init__(self, session: SessionBase):
        self._session = session
        self._index = WorkspaceIndex(session)

    def list_slots(self) -> List[int]:
        return self._index.slots()

    def active_slot(self) -> int:
        return self._index.active_slot()

    def set_active_slot(self, slot: int) -> None:
        self._index.set_active_slot(slot)

    def repository_for(self, slot: int) -> ISystemRepository:
        return SessionSystemRepository(self._session, slot=slot)

    def _register_slot(self, slot: int) -> None:
        self._index.add_slot(slot)

    def _deregister_slot(self, slot: int) -> None:
        self._index.remove_slot(slot)
