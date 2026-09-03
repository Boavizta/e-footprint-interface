from typing import TYPE_CHECKING

from efootprint.constants.sources import Sources
from efootprint.builders.timeseries.explainable_hourly_quantities_from_form_inputs import \
    ExplainableHourlyQuantitiesFromFormInputs

from model_builder.domain.entities.web_core.usage.usage_pattern_web_base_class import (
    UsagePatternWebBaseClass, default_modeling_start_date)

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class EdgeUsagePatternWeb(UsagePatternWebBaseClass):
    required_non_empty_relationships = frozenset({"edge_usage_journeys"})
    default_values = {"hourly_deployment_starts": ExplainableHourlyQuantitiesFromFormInputs(
        {"start_date": default_modeling_start_date(), "modeling_duration_value": 3, "modeling_duration_unit": "year",
         "net_growth_rate_in_percentage": 10, "net_growth_rate_timespan": "year",
         "initial_volume": None, "initial_volume_timespan": "month"}, source=Sources.USER_DATA)
    }
    attr_name_in_system = "edge_usage_patterns"
    journey_relationship_attr = "edge_usage_journeys"

    hourly_quantities_from_growth_ui_config = {
        "initial_volume": {
            "label": "Initial number of edge devices put in service",
            "tooltip": (
                "The number of edge deployments put in service in the chosen period. Every selected edge usage "
                "journey applies throughout the deployment usage span."
            ),
        },
    }

    @classmethod
    def can_create(cls, model_web: "ModelWeb") -> bool:
        return bool(model_web.edge_usage_journeys)
