"""Domain descriptors for out-of-band DOM regions to re-render after a use-case execution.

Domain hooks return `OobRegion` values as side-effect descriptors. The presenter renders
them via a registry (see `model_builder.adapters.presenters.oob_regions`) so it stays free
of type-specific branching.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class OobRegion:
    key: str
    params: Tuple[Tuple[str, Any], ...] = ()

    @classmethod
    def make(cls, key: str, **params) -> "OobRegion":
        return cls(key=key, params=tuple(sorted(params.items())))

    @property
    def params_dict(self) -> Dict[str, Any]:
        return dict(self.params)


@dataclass
class CreateSideEffects:
    oob_regions: List[OobRegion] = field(default_factory=list)
    replaces_primary_render: bool = False
