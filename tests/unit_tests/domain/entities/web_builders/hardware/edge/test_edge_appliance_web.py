"""Unit tests for EdgeApplianceWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from model_builder.domain.entities.web_builders.hardware.edge.edge_appliance_web import EdgeApplianceWeb


class TestEdgeApplianceWeb:
    """Tests for EdgeApplianceWeb-specific behavior."""

    def test_calculated_attributes_values_filters_component_and_appends_super(self):
        """Calculated attributes should filter appliance component values and append base values."""
        appliance_component = SimpleNamespace(
            calculated_attributes_values=[
                SimpleNamespace(attr_name_in_mod_obj_container="instances_fabrication_footprint"),
                SimpleNamespace(attr_name_in_mod_obj_container="power"),
            ]
        )
        modeling_obj = SimpleNamespace(
            id="appliance-1",
            class_as_simple_str="EdgeAppliance",
            name="appliance",
            appliance_component=appliance_component,
            instances_fabrication_footprint_per_usage_pattern="per-usage",
            instances_fabrication_footprint="fabrication",
        )

        web_obj = EdgeApplianceWeb(modeling_obj, MagicMock())

        values = web_obj.calculated_attributes_values

        assert values == [
            appliance_component.calculated_attributes_values[1],
            "per-usage",
            "fabrication",
        ]
