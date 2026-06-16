"""Interface for the model-comparison workspace.

A workspace holds up to two model *slots* plus an active-slot pointer. Each slot is persisted as
its own single-model payload (today's exact format) through an ``ISystemRepository``, so editing one
model never deserializes or recomputes the other.

This module has NO Django dependencies, keeping the domain layer framework-agnostic.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from model_builder.domain.interfaces.system_repository import ISystemRepository


class IWorkspaceRepository(ABC):
    """Interface for the slot index of a comparison workspace.

    The workspace owns the slot index and vends an ordinary per-slot ``ISystemRepository`` (which
    stays a single-model abstraction). Because ``active_repository`` defaults to the active slot, the
    existing single-model call sites resolve their repository through the workspace unchanged.

    Two invariants live here as the single enforcement point (see the session implementation):
      - the summed with-calculated-attributes weight of all slots stays within the shared payload budget;
      - the two slots never hold the same system id (a fresh system id is minted on any cross-slot
        collision, whatever the source: import, workspace import, template, blank, duplicate).

    Implementations:
        - SessionWorkspaceRepository: Django-session-backed (production).
        - InMemoryWorkspaceRepository: in-memory dict (integration harness).
    """

    @abstractmethod
    def list_slots(self) -> List[int]:
        """Return the ordered list of occupied slot indices (e.g. ``[0]`` or ``[0, 1]``)."""

    @abstractmethod
    def active_slot(self) -> int:
        """Return the index of the active slot."""

    @abstractmethod
    def set_active_slot(self, slot: int) -> None:
        """Make ``slot`` the active slot. ``slot`` must be occupied."""

    @abstractmethod
    def add_slot(self, system_data: Dict[str, Any]) -> int:
        """Persist ``system_data`` into a new slot and return its index.

        Enforces the shared payload budget and the distinct-system-id invariant: if the incoming
        model's system id already exists in another slot, a fresh system id is minted before saving.
        """

    @abstractmethod
    def remove_slot(self, slot: int) -> None:
        """Drop ``slot`` and its payload, returning the workspace toward single-model state."""

    @abstractmethod
    def repository_for(self, slot: int) -> ISystemRepository:
        """Return an ``ISystemRepository`` bound to ``slot``."""

    def active_repository(self) -> ISystemRepository:
        """Return an ``ISystemRepository`` bound to the active slot."""
        return self.repository_for(self.active_slot())
