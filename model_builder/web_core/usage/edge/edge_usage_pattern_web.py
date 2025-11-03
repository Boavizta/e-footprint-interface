from efootprint.constants.sources import Sources

from model_builder.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import \
    ExplainableHourlyQuantitiesFromFormInputs
from model_builder.web_core.usage.usage_pattern_web_base_class import UsagePatternWebBaseClass


class EdgeUsagePatternWeb(UsagePatternWebBaseClass):
    default_values = {"hourly_edge_usage_journey_starts": ExplainableHourlyQuantitiesFromFormInputs(
        {"start_date": "2025-01-01", "modeling_duration_value": 3, "modeling_duration_unit": "year",
         "net_growth_rate_in_percentage": 10, "net_growth_rate_timespan": "year",
         "initial_volume": None, "initial_volume_timespan": "month"}, source=Sources.USER_DATA)
    }
    attr_name_in_system = "edge_usage_patterns"
    object_type_in_volume = "edge_usage_journey"

    @property
    def links_to(self):
        return self.edge_usage_journey.web_id
