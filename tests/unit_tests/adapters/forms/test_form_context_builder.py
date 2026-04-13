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
