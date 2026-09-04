from typing import TYPE_CHECKING

from efootprint.constants.sources import Sources
from efootprint.builders.timeseries.explainable_hourly_quantities_from_form_inputs import \
    ExplainableHourlyQuantitiesFromFormInputs

from model_builder.domain.entities.web_core.usage.usage_pattern_web_base_class import (
    UsagePatternWebBaseClass, default_modeling_start_date)

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class UsagePatternWeb(UsagePatternWebBaseClass):
    required_non_empty_relationships = frozenset({"usage_journeys"})
    default_values = {"hourly_occurrences": ExplainableHourlyQuantitiesFromFormInputs(
        {"start_date": default_modeling_start_date(), "modeling_duration_value": 3, "modeling_duration_unit": "year",
         "net_growth_rate_in_percentage": 10, "net_growth_rate_timespan": "year",
         "initial_volume": None, "initial_volume_timespan": "month"}, source=Sources.USER_DATA)
    }
    attr_name_in_system = "usage_patterns"
    journey_relationship_attr = "usage_journeys"

    hourly_quantities_from_growth_ui_config = {
        "initial_volume": {
            "label": "Initial number of pattern occurrences",
            "tooltip": (
                "The number of usage-pattern occurrences in the chosen period at the beginning of the projection. "
                "Each journey's weight is applied to this shared volume."
            ),
        },
    }

    # Declarative form configuration - extends parent's config
    form_creation_config = {
        "strategy": "simple",
        "field_defaults": {
            "country": {"default_by_label": "France"},
        },
        "field_transforms": {
            # Convert devices from multiselect to single select
            "devices": {"multiselect_to_single": True},
        },
    }

    # Edition also needs the same transform
    form_edition_config = {
        "strategy": "simple",
        "field_transforms": {
            "devices": {"multiselect_to_single": True},
        },
    }

    @classmethod
    def can_create(cls, model_web: "ModelWeb") -> bool:
        return bool(model_web.usage_journeys)
