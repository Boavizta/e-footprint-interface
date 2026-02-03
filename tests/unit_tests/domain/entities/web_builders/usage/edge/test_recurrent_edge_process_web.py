"""Unit tests for RecurrentEdgeProcessWeb entity."""
from model_builder.domain.entities.web_builders.usage.edge.recurrent_edge_process_web import RecurrentEdgeProcessWeb
from model_builder.domain.entities.efootprint_extensions.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant,
)


class TestRecurrentEdgeProcessWeb:
    """Tests for RecurrentEdgeProcessWeb-specific behavior."""

    def test_default_values_define_recurrent_needs(self):
        """Default values should include compute, RAM, and storage recurrent quantities."""
        defaults = RecurrentEdgeProcessWeb.default_values

        assert set(defaults.keys()) == {
            "recurrent_compute_needed",
            "recurrent_ram_needed",
            "recurrent_storage_needed",
        }
        assert all(isinstance(value, ExplainableRecurrentQuantitiesFromConstant) for value in defaults.values())
