"""Unit tests for EdgeComputerWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from model_builder.domain.entities.web_builders.hardware.edge.edge_computer_web import EdgeComputerWeb


class TestEdgeComputerWeb:
    """Tests for EdgeComputerWeb-specific behavior."""

    def test_calculated_attributes_values_concatenates_components(self):
        """Calculated attributes values should include CPU and RAM component values first."""
        cpu_component = SimpleNamespace(calculated_attributes_values=["cpu"])
        ram_component = SimpleNamespace(calculated_attributes_values=["ram"])
        modeling_obj = SimpleNamespace(
            id="edge-comp",
            class_as_simple_str="EdgeComputer",
            name="edge",
            cpu_component=cpu_component,
            ram_component=ram_component,
            calculated_attributes=[],
        )

        web_obj = EdgeComputerWeb(modeling_obj, MagicMock())

        assert web_obj.calculated_attributes_values == ["cpu", "ram"]

    def test_pre_create_adds_storage_reference(self):
        """pre_create should create storage and inject its ID without mutating input."""
        form_data = {"_parsed_EdgeStorage": {"name": "Storage"}}
        storage_obj = SimpleNamespace(efootprint_id="storage-id")
        model_web = MagicMock()
        model_web.add_new_efootprint_object_to_system.return_value = storage_obj

        with patch(
            "model_builder.domain.entities.web_builders.hardware.edge.edge_computer_web.create_efootprint_obj_from_parsed_data"
        ) as create_mock:
            create_mock.return_value = storage_obj

            result = EdgeComputerWeb.pre_create(form_data, model_web)

        assert result["storage"] == "storage-id"
        assert "storage" not in form_data
        create_mock.assert_called_once_with({"name": "Storage"}, model_web, "EdgeStorage")

    def test_pre_edit_updates_storage(self):
        """pre_edit should update the nested storage object."""
        modeling_obj = SimpleNamespace(
            id="edge-comp",
            class_as_simple_str="EdgeComputer",
            name="edge",
            storage=MagicMock(),
        )
        web_obj = EdgeComputerWeb(modeling_obj, MagicMock())

        with patch(
            "model_builder.domain.entities.web_builders.hardware.edge.edge_computer_web.edit_object_from_parsed_data"
        ) as edit_mock:
            web_obj.pre_edit({"_parsed_EdgeStorage": {"name": "Storage"}})

        edit_mock.assert_called_once_with({"name": "Storage"}, modeling_obj.storage)
