"""Unit tests for form data parser."""
import pytest

from model_builder.adapters.forms.form_data_parser import parse_form_data
from tests.utils import assert_dicts_equal


class TestParseFormData:
    """Tests for parse_form_data function."""

    def test_parses_prefixed_simple_fields(self):
        """Should strip prefix and return clean attribute names."""
        form_data = {
            "Server_name": "My Server",
            "Server_compute": "4",
        }

        result = parse_form_data(form_data, "Server")

        assert result["name"] == "My Server"
        assert result["compute"] == {"value": "4", "label": "no label"} # Not treated as quantity without unit field

    def test_parses_unprefixed_fields(self):
        """Should handle unprefixed keys (from internal calls)."""
        form_data = {
            "name": "My Server",
            "compute": "4",
        }

        result = parse_form_data(form_data, "Server")

        assert result["name"] == "My Server"
        assert result["compute"] == {"value": "4", "label": "no label"}

    def test_parses_nested_fields_with_double_underscore(self):
        """Should group nested fields (attr__field) into dicts."""
        form_data = {
            "UsagePattern_hourly_usage_journey_starts__start_date": "2025-02-01",
            "UsagePattern_hourly_usage_journey_starts__modeling_duration_value": "5",
            "UsagePattern_hourly_usage_journey_starts__modeling_duration_unit": "month",
            "UsagePattern_name": "Test Pattern",
        }

        result = parse_form_data(form_data, "UsagePattern")

        assert result["name"] == "Test Pattern"
        assert "hourly_usage_journey_starts" in result
        nested = result["hourly_usage_journey_starts"]["form_inputs"]
        assert nested["start_date"] == "2025-02-01"
        assert nested["modeling_duration_value"] == "5"
        assert nested["modeling_duration_unit"] == "month"

    def test_parses_scalar_quantity_unit_fields(self):
        """Should extract __unit suffix fields into quantity metadata."""
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_ram": "16",
            "Server_ram__unit": "GB",
        }

        result = parse_form_data(form_data, "Server")

        assert result["compute"] == {"value": 4, "unit": "core", "label": "no label"}
        assert result["ram"] == {"value": 16, "unit": "GB", "label": "no label"}

    def test_keeps_real_fields_ending_with_unit_as_regular_fields(self, monkeypatch):
        """Should not confuse real *_unit attributes with quantity helper fields."""

        class FakeModel:
            pass

        monkeypatch.setitem(
            parse_form_data.__globals__["MODELING_OBJECT_CLASSES_DICT"],
            "FakeModel",
            FakeModel,
        )
        monkeypatch.setitem(
            parse_form_data.__globals__,
            "get_init_signature_params",
            lambda _: {"storage_duration_unit": type("Param", (), {"annotation": None})()},
        )

        form_data = {
            "FakeModel_name": "Test",
            "FakeModel_storage_duration_unit": "month",
        }

        result = parse_form_data(form_data, "FakeModel")

        assert result == {"name": "Test", "storage_duration_unit": "month"}

    def test_handles_mixed_prefixed_and_unprefixed(self):
        """Should handle mix of prefixed and unprefixed keys."""
        form_data = {
            "Server_name": "My Server",
            "type_object_available": "Server",  # unprefixed
        }

        result = parse_form_data(form_data, "Server")

        assert result["name"] == "My Server"
        assert result["type_object_available"] == "Server"

    def test_empty_form_data(self):
        """Should return empty dict for empty input."""
        result = parse_form_data({}, "Server")
        assert result == {}

    def test_parse_inline_form_data(self):
        value = '{"type_object_available":"Storage","Storage_name":"Storage 3","Storage_storage_capacity":"1","Storage_storage_capacity__unit":"TB","Storage_data_replication_factor":"3", "Storage_data_replication_factor__unit":"dimensionless"}'
        from model_builder.adapters.forms.form_data_parser import _parse_inline_form_data
        parsed_key, parsed_form = _parse_inline_form_data("Storage_form_data", value)

        expected = {
            "name": "Storage 3",
            "type_object_available": "Storage",
            "storage_capacity": {"value": 1.0, "unit": "TB", "label": "no label"},
            "data_replication_factor": {"value": 3.0, "unit": "dimensionless", "label": "no label"}}

        assert parsed_key == "_parsed_Storage"

        assert_dicts_equal(parsed_form, expected)

    def test_parses_explainable_object_dict_widget_payload(self):
        form_data = {
            "type_object_available": "EdgeDeviceGroup",
            "EdgeDeviceGroup_name": "Campus",
            "EdgeDeviceGroup_sub_group_counts": '{"group-1": 2}',
            "EdgeDeviceGroup_edge_device_counts": '{"device-1": 3}',
        }

        result = parse_form_data(form_data, "EdgeDeviceGroup")

        assert result["sub_group_counts"] == {
            "group-1": {"value": 2, "unit": "dimensionless", "label": "no label"}
        }
        assert result["edge_device_counts"] == {
            "device-1": {"value": 3, "unit": "dimensionless", "label": "no label"}
        }

    def test_parses_empty_explainable_object_dict_widget_payload(self):
        form_data = {
            "type_object_available": "EdgeDeviceGroup",
            "EdgeDeviceGroup_name": "Campus",
            "EdgeDeviceGroup_sub_group_counts": "",
        }

        result = parse_form_data(form_data, "EdgeDeviceGroup")

        assert result["sub_group_counts"] == {}

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            ('{"group-1": "abc"}', "must be a number"),
            ('{"group-1": -1}', "must be positive"),
            ('["group-1"]', "must be a JSON object"),
            ('{bad json}', "must be valid JSON"),
        ],
    )
    def test_rejects_invalid_explainable_object_dict_widget_payload(self, payload, message):
        form_data = {
            "type_object_available": "EdgeDeviceGroup",
            "EdgeDeviceGroup_name": "Campus",
            "EdgeDeviceGroup_sub_group_counts": payload,
        }

        with pytest.raises(ValueError, match=message):
            parse_form_data(form_data, "EdgeDeviceGroup")


class TestMetadataSuffixes:
    """Tests for the five reserved metadata suffixes."""

    def test_parses_confidence_suffix(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__confidence": "medium",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["confidence"] == "medium"

    def test_empty_confidence_becomes_none(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__confidence": "",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["confidence"] is None

    def test_parses_comment_suffix(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__comment": "cross-checked with audit",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["comment"] == "cross-checked with audit"

    def test_empty_comment_becomes_none(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__comment": "",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["comment"] is None

    def test_parses_source_id_suffix(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__source_id": "abc123",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["source"]["id"] == "abc123"

    def test_parses_source_name_suffix(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__source_name": "My Source",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["source"]["name"] == "My Source"

    def test_parses_source_link_suffix(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__source_link": "https://example.com",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["source"]["link"] == "https://example.com"

    def test_empty_source_link_becomes_none(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__source_link": "",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["source"]["link"] is None

    def test_all_five_metadata_suffixes_together(self):
        form_data = {
            "Server_compute": "4",
            "Server_compute__unit": "core",
            "Server_compute__confidence": "high",
            "Server_compute__comment": "verified",
            "Server_compute__source_id": "src1",
            "Server_compute__source_name": "ADEME 2024",
            "Server_compute__source_link": "https://ademe.fr",
        }
        result = parse_form_data(form_data, "Server")
        assert result["compute"]["value"] == 4.0
        assert result["compute"]["unit"] == "core"
        assert result["compute"]["confidence"] == "high"
        assert result["compute"]["comment"] == "verified"
        assert result["compute"]["source"] == {"id": "src1", "name": "ADEME 2024", "link": "https://ademe.fr"}

    def test_metadata_suffixes_do_not_go_into_form_inputs(self):
        """Metadata suffixes must not fall through to the generic __ → form_inputs branch."""
        form_data = {
            "UsagePattern_hourly_usage_journey_starts__start_date": "2025-01-01",
            "UsagePattern_hourly_usage_journey_starts__confidence": "low",
            "UsagePattern_name": "test",
        }
        result = parse_form_data(form_data, "UsagePattern")
        assert "confidence" not in result["hourly_usage_journey_starts"].get("form_inputs", {})
        assert result["hourly_usage_journey_starts"]["confidence"] == "low"
