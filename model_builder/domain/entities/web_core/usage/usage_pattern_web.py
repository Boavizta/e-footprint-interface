from efootprint.constants.sources import Sources

from model_builder.domain.entities.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import \
    ExplainableHourlyQuantitiesFromFormInputs
from model_builder.domain.entities.web_core.usage.usage_pattern_web_base_class import UsagePatternWebBaseClass


class UsagePatternWeb(UsagePatternWebBaseClass):
    default_values = {"hourly_usage_journey_starts": ExplainableHourlyQuantitiesFromFormInputs(
        {"start_date": "2025-01-01", "modeling_duration_value": 3, "modeling_duration_unit": "year",
         "net_growth_rate_in_percentage": 10, "net_growth_rate_timespan": "year",
         "initial_volume": None, "initial_volume_timespan": "month"}, source=Sources.USER_DATA)
    }
    attr_name_in_system = "usage_patterns"
    object_type_in_volume = "usage_journey"

    # Declarative form configuration - extends parent's config
    form_creation_config = {
        'strategy': 'simple',
        'field_defaults': {
            'country': {'default_by_label': 'France'},
        },
        'field_transforms': {
            # Convert devices from multiselect to single select
            'devices': {'multiselect_to_single': True},
        },
    }

    # Edition also needs the same transform
    form_edition_config = {
        'strategy': 'simple',
        'field_transforms': {
            'devices': {'multiselect_to_single': True},
        },
    }

