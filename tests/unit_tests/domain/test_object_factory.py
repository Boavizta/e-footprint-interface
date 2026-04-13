"""Unit tests for object_factory helpers."""
import pytest

from efootprint.abstract_modeling_classes.source_objects import Sources

from model_builder.domain.object_factory import create_efootprint_obj_from_parsed_data


class TestCreateEfootprintObjFromParsedData:
    """Tests for constructor-time dict input support."""

    def test_builds_input_explainable_object_dicts_from_parsed_data(self, minimal_model_web):
        group = minimal_model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Parent"}, minimal_model_web, "EdgeDeviceGroup")
        )
        device = minimal_model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data(
                {"name": "Device", "components": []},
                minimal_model_web,
                "EdgeDevice",
            )
        )

        created_group = create_efootprint_obj_from_parsed_data(
            {
                "name": "Campus",
                "sub_group_counts": {
                    group.efootprint_id: {"value": 2, "unit": "dimensionless", "label": "no label"}
                },
                "edge_device_counts": {
                    device.efootprint_id: {"value": 3, "unit": "dimensionless", "label": "no label"}
                },
            },
            minimal_model_web,
            "EdgeDeviceGroup",
        )

        assert group.modeling_obj in created_group.sub_group_counts
        assert created_group.sub_group_counts[group.modeling_obj].value.magnitude == 2
        assert created_group.sub_group_counts[group.modeling_obj].source == Sources.USER_DATA
        assert device.modeling_obj in created_group.edge_device_counts
        assert created_group.edge_device_counts[device.modeling_obj].value.magnitude == 3
        assert created_group.edge_device_counts[device.modeling_obj].source == Sources.USER_DATA

    def test_rejects_unknown_ids_in_input_explainable_object_dicts(self, minimal_model_web):
        with pytest.raises(ValueError, match="Unknown modeling object id 'missing-id'"):
            create_efootprint_obj_from_parsed_data(
                {
                    "name": "Campus",
                    "sub_group_counts": {
                        "missing-id": {"value": 1, "unit": "dimensionless", "label": "no label"}
                    },
                },
                minimal_model_web,
                "EdgeDeviceGroup",
            )
