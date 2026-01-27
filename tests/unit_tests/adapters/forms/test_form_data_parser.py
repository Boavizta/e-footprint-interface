"""Unit tests for form data parser."""
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

    def test_parses_unit_fields(self):
        """Should extract _unit suffix fields into _units metadata."""
        form_data = {
            "Server_compute": "4",
            "Server_compute_unit": "core",
            "Server_ram": "16",
            "Server_ram_unit": "GB",
        }

        result = parse_form_data(form_data, "Server")

        assert result["compute"] == {"value": 4, "unit": "core", "label": "no label"}
        assert result["ram"] == {"value": 16, "unit": "GB", "label": "no label"}

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
        value = '{"type_object_available":"Storage","Storage_name":"Storage 3","Storage_storage_capacity":"1","Storage_storage_capacity_unit":"TB","Storage_data_replication_factor":"3", "Storage_data_replication_factor_unit":"dimensionless"}'
        from model_builder.adapters.forms.form_data_parser import _parse_inline_form_data
        parsed_key, parsed_form = _parse_inline_form_data("Storage_form_data", value)

        expected = {
            'name': 'Storage 3',
            'type_object_available': 'Storage',
            'storage_capacity': {'value': 1.0, 'unit': 'TB', "label": "no label"},
            'data_replication_factor': {'value': 3.0, 'unit': 'dimensionless', "label": "no label"}}

        assert parsed_key == "_parsed_Storage"

        assert_dicts_equal(parsed_form, expected)
