"""Shared lightweight helpers for web_core tests."""
from typing import Dict, Any, Tuple, List


class DummyExplainableWeb:
    """Minimal web explainable wrapper exposing expected interface for chart helpers."""

    def __init__(self, efootprint_obj, literal_formula: str = "x", ancestors: List = None):
        self.efootprint_object = efootprint_obj
        self.start_date = efootprint_obj.start_date
        self.value = efootprint_obj.value
        self.magnitude = efootprint_obj.magnitude
        self.unit = efootprint_obj.unit
        self._literal_formula = literal_formula
        self._ancestors = ancestors or []

    def compute_literal_formula_and_ancestors_mapped_to_symbols_list(self) -> Tuple[str, List[Any]]:
        return self._literal_formula, self._ancestors


class DummyWebObj:
    """Container exposing a single explainable attribute."""

    def __init__(self, attr_name: str, web_explainable):
        setattr(self, attr_name, web_explainable)


class DummyModelWeb:
    """Minimal ModelWeb stand-in for prepare_timeseries_chart_context."""

    def __init__(self, web_obj, efootprint_map: Dict[str, Any] | None = None):
        self._web_obj = web_obj
        self._efootprint_map = efootprint_map or {}

    def get_web_object_from_efootprint_id(self, efootprint_id):
        return self._efootprint_map.get(efootprint_id, self._web_obj)

    def get_efootprint_object_from_efootprint_id(self, efootprint_id, _):
        # Identity passthrough: many tests store real efootprint IDs
        return efootprint_id
