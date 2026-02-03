"""Unit tests for EdgeApplianceComponentWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from model_builder.domain.entities.web_builders.hardware.edge.edge_appliance_component import EdgeApplianceComponentWeb


class TestEdgeApplianceComponentWeb:
    """Tests for EdgeApplianceComponentWeb-specific behavior."""

    def test_list_containers_and_attr_name_in_list_container(self):
        """Should return edge device container and components attr name."""
        edge_device = SimpleNamespace(id="edge-device")
        modeling_obj = SimpleNamespace(
            id="component-1",
            class_as_simple_str="EdgeApplianceComponent",
            name="component",
            edge_device=edge_device,
        )

        web_obj = EdgeApplianceComponentWeb(modeling_obj, MagicMock())

        containers, attr_name = web_obj.list_containers_and_attr_name_in_list_container

        assert containers == [edge_device]
        assert attr_name == "components"

    def test_calculated_attributes_filters_known_fields(self):
        """Calculated attributes should exclude lifespan and power-related fields."""
        modeling_obj = SimpleNamespace(
            id="component-1",
            class_as_simple_str="EdgeApplianceComponent",
            name="component",
            edge_device=SimpleNamespace(id="edge-device"),
            calculated_attributes=["lifespan", "power", "idle_power", "other"],
        )

        web_obj = EdgeApplianceComponentWeb(modeling_obj, MagicMock())

        assert web_obj.calculated_attributes == ["other"]
