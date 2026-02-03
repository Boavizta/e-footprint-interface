"""Unit tests for EdgeComputerCPUComponentWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from model_builder.domain.entities.web_builders.hardware.edge.edge_computer_cpu_component import (
    EdgeComputerCPUComponentWeb,
)


class TestEdgeComputerCPUComponentWeb:
    """Tests for EdgeComputerCPUComponentWeb-specific behavior."""

    def test_list_containers_and_attr_name_in_list_container(self):
        """Should return edge device container and components attr name."""
        edge_device = SimpleNamespace(id="edge-device")
        modeling_obj = SimpleNamespace(
            id="cpu-1",
            class_as_simple_str="EdgeComputerCPUComponent",
            name="cpu",
            edge_device=edge_device,
        )

        web_obj = EdgeComputerCPUComponentWeb(modeling_obj, MagicMock())

        containers, attr_name = web_obj.list_containers_and_attr_name_in_list_container

        assert containers == [edge_device]
        assert attr_name == "components"

    def test_calculated_attributes_filters_known_fields(self):
        """Calculated attributes should exclude compute-related and power fields."""
        modeling_obj = SimpleNamespace(
            id="cpu-1",
            class_as_simple_str="EdgeComputerCPUComponent",
            name="cpu",
            edge_device=SimpleNamespace(id="edge-device"),
            calculated_attributes=[
                "compute",
                "base_compute_consumption",
                "lifespan",
                "power",
                "idle_power",
                "instances_fabrication_footprint_per_usage_pattern",
                "instances_fabrication_footprint",
                "other",
            ],
        )

        web_obj = EdgeComputerCPUComponentWeb(modeling_obj, MagicMock())

        assert web_obj.calculated_attributes == ["other"]
