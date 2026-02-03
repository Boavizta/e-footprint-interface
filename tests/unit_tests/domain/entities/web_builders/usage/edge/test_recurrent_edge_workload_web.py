"""Unit tests for RecurrentEdgeWorkloadWeb entity."""
from model_builder.domain.entities.web_builders.usage.edge.recurrent_edge_workload_web import RecurrentEdgeWorkloadWeb
from model_builder.domain.entities.efootprint_extensions.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant,
)


class TestRecurrentEdgeWorkloadWeb:
    """Tests for RecurrentEdgeWorkloadWeb-specific behavior."""

    def test_default_values_define_recurrent_workload(self):
        """Default values should include recurrent workload quantity."""
        defaults = RecurrentEdgeWorkloadWeb.default_values

        assert set(defaults.keys()) == {"recurrent_workload"}
        assert isinstance(defaults["recurrent_workload"], ExplainableRecurrentQuantitiesFromConstant)
