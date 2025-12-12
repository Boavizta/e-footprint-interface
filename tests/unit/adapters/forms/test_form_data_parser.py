"""Unit tests for form data parser."""
from model_builder.adapters.forms.form_data_parser import parse_form_data


class TestParseFormData:
    """Tests for parse_form_data function."""

    def test_parses_prefixed_simple_fields(self):
        """Should strip prefix and return clean attribute names."""
        form_data = {
            "Server_name": "My Server",
            "Server_cpu_cores": "4",
        }

        result = parse_form_data(form_data, "Server")

        assert result["name"] == "My Server"
        assert result["cpu_cores"] == "4"

    def test_parses_unprefixed_fields(self):
        """Should handle unprefixed keys (from internal calls)."""
        form_data = {
            "name": "My Server",
            "cpu_cores": "4",
        }

        result = parse_form_data(form_data, "Server")

        assert result["name"] == "My Server"
        assert result["cpu_cores"] == "4"

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
        nested = result["hourly_usage_journey_starts"]
        assert nested["start_date"] == "2025-02-01"
        assert nested["modeling_duration_value"] == "5"
        assert nested["modeling_duration_unit"] == "month"

    def test_parses_unit_fields_into_units_dict(self):
        """Should extract _unit suffix fields into _units metadata."""
        form_data = {
            "Server_cpu_cores": "4",
            "Server_cpu_cores_unit": "core",
            "Server_ram": "16",
            "Server_ram_unit": "GB",
        }

        result = parse_form_data(form_data, "Server")

        assert result["cpu_cores"] == "4"
        assert result["ram"] == "16"
        assert "_units" in result
        assert result["_units"]["cpu_cores"] == "core"
        assert result["_units"]["ram"] == "GB"

    def test_handles_mixed_prefixed_and_unprefixed(self):
        """Should handle mix of prefixed and unprefixed keys."""
        form_data = {
            "Server_name": "My Server",
            "type_object_available": "Server",  # unprefixed
        }

        result = parse_form_data(form_data, "Server")

        assert result["name"] == "My Server"
        assert result["type_object_available"] == "Server"

    def test_skips_unrelated_prefixed_fields(self):
        """Should not include fields with different prefix in nested dict."""
        form_data = {
            "Server_name": "My Server",
            "Storage_name": "My Storage",  # Different prefix
        }

        result = parse_form_data(form_data, "Server")

        assert result["name"] == "My Server"
        # Storage_name should be included as "Storage_name" (unprefixed handling)
        # since it doesn't start with "Server_"
        assert "Storage_name" in result

    def test_empty_form_data(self):
        """Should return empty dict for empty input."""
        result = parse_form_data({}, "Server")
        assert result == {}

    def test_no_units_key_when_no_units(self):
        """Should not include _units key when no unit fields present."""
        form_data = {
            "Server_name": "My Server",
        }

        result = parse_form_data(form_data, "Server")

        assert "_units" not in result
