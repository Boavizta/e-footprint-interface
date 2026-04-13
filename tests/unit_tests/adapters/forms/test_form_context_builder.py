"""Unit tests for FormContextBuilder-specific custom context."""

from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup

from model_builder.adapters.forms.form_context_builder import FormContextBuilder
from model_builder.domain.entities.web_core.hardware.edge.edge_device_group_web import EdgeDeviceGroupWeb


class TestFormContextBuilder:
    """Tests for creation context augmentation."""

    def test_build_creation_context_for_edge_device_group_builds_dict_count_fields_from_prerequisites(self, minimal_model_web):
        existing_group = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Existing Group"))
        existing_device = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Existing Device", components=[]))

        context = FormContextBuilder(minimal_model_web).build_creation_context(
            EdgeDeviceGroupWeb, "EdgeDeviceGroup")

        fields_by_attr = {field["attr_name"]: field for field in context["dict_count_fields"]}
        assert fields_by_attr["sub_group_counts"]["options"] == [
            {"value": existing_group.efootprint_id, "label": "Existing Group"}
        ]
        assert fields_by_attr["edge_device_counts"]["options"] == [
            {"value": existing_device.efootprint_id, "label": "Existing Device"}
        ]

    def test_build_edition_context_sorts_dict_count_options(self, minimal_model_web):
        parent = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Parent"))
        zeta = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Zeta"))
        alpha = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Alpha"))
        device_b = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Device B", components=[]))
        device_a = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Device A", components=[]))
        del zeta, alpha, device_b, device_a

        context = FormContextBuilder(minimal_model_web).build_edition_context(parent)

        fields_by_attr = {field["attr_name"]: field for field in context["dict_count_fields"]}
        assert [option["label"] for option in fields_by_attr["sub_group_counts"]["options"]] == [
            "Alpha",
            "Zeta",
        ]
        assert [option["label"] for option in fields_by_attr["edge_device_counts"]["options"]] == [
            "Device A",
            "Device B",
        ]

    def test_build_edition_context_hydrates_dict_count_fields(self, minimal_model_web):
        group = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Group"))

        context = FormContextBuilder(minimal_model_web).build_edition_context(group)

        fields_by_attr = {field["attr_name"]: field for field in context["dict_count_fields"]}
        assert fields_by_attr["sub_group_counts"]["web_id"] == "EdgeDeviceGroup_sub_group_counts"
        assert fields_by_attr["sub_group_counts"]["input_type"] == "dict_count"
        assert fields_by_attr["sub_group_counts"]["label"]
        assert "tooltip" in fields_by_attr["sub_group_counts"]
        assert fields_by_attr["sub_group_counts"]["options_json"].startswith("[")
        assert fields_by_attr["sub_group_counts"]["selected_json"].startswith("{")
