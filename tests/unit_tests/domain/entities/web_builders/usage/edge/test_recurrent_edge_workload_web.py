"""Unit tests for RecurrentEdgeWorkloadWeb entity."""
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant,
)

from model_builder.domain.entities.web_builders.usage.edge.recurrent_edge_workload_web import RecurrentEdgeWorkloadWeb


class TestRecurrentEdgeWorkloadWeb:
    """Tests for RecurrentEdgeWorkloadWeb-specific behavior."""

    def test_default_values_define_recurrent_workload(self):
        """Default values should include recurrent workload quantity."""
        defaults = RecurrentEdgeWorkloadWeb.default_values

        assert set(defaults.keys()) == {"recurrent_workload"}
        assert isinstance(defaults["recurrent_workload"], ExplainableRecurrentQuantitiesFromConstant)
