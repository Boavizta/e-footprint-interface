"""Unit tests for EdgeComputerRAMComponentWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from model_builder.domain.entities.web_builders.hardware.edge.edge_computer_ram_component import (
    EdgeComputerRAMComponentWeb,
)


class TestEdgeComputerRAMComponentWeb:
    """Tests for EdgeComputerRAMComponentWeb-specific behavior."""

    def test_list_containers_and_attr_name_in_list_container(self):
        """Should return edge device container and components attr name."""
        edge_device = SimpleNamespace(id="edge-device")
        modeling_obj = SimpleNamespace(
            id="ram-1",
            class_as_simple_str="EdgeComputerRAMComponent",
            name="ram",
            edge_device=edge_device,
        )

        web_obj = EdgeComputerRAMComponentWeb(modeling_obj, MagicMock())

        containers, attr_name = web_obj.list_containers_and_attr_name_in_list_container

        assert containers == [edge_device]
        assert attr_name == "components"

    def test_calculated_attributes_filters_known_fields(self):
        """Calculated attributes should exclude RAM-related fields."""
        modeling_obj = SimpleNamespace(
            id="ram-1",
            class_as_simple_str="EdgeComputerRAMComponent",
            name="ram",
            edge_device=SimpleNamespace(id="edge-device"),
            calculated_attributes=[
                "ram",
                "base_ram_consumption",
                "lifespan",
                "instances_fabrication_footprint_per_usage_pattern",
                "instances_fabrication_footprint",
                "other",
            ],
        )

        web_obj = EdgeComputerRAMComponentWeb(modeling_obj, MagicMock())

        assert web_obj.calculated_attributes == ["other"]
