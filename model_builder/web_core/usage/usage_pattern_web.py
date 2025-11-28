from efootprint.constants.sources import Sources

from model_builder.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import \
    ExplainableHourlyQuantitiesFromFormInputs
from model_builder.web_core.usage.usage_pattern_web_base_class import UsagePatternWebBaseClass


class UsagePatternWeb(UsagePatternWebBaseClass):
    default_values = {"hourly_usage_journey_starts": ExplainableHourlyQuantitiesFromFormInputs(
        {"start_date": "2025-01-01", "modeling_duration_value": 3, "modeling_duration_unit": "year",
         "net_growth_rate_in_percentage": 10, "net_growth_rate_timespan": "year",
         "initial_volume": None, "initial_volume_timespan": "month"}, source=Sources.USER_DATA)
    }
    attr_name_in_system = "usage_patterns"
    object_type_in_volume = "usage_journey"

    @classmethod
    def generate_object_creation_context(
    cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None, object_type: str=None):
        creation_context = super().generate_object_creation_context(
            model_web, efootprint_id_of_parent_to_link_to, object_type)

        attributes_section = creation_context["form_sections"][1]
        for structure_field in attributes_section["fields"]:
            if structure_field["attr_name"] == "devices":
                structure_field.update({
                    "input_type": "select_object",
                    "options": structure_field["unselected"],
                    "selected": structure_field["unselected"][0]["value"]
                })
                structure_field.pop("unselected")

        return creation_context

