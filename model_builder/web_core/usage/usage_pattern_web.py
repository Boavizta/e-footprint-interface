from copy import deepcopy
from typing import TYPE_CHECKING

from model_builder.class_structure import generate_object_creation_structure, generate_dynamic_form
from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class UsagePatternWeb(ModelingObjectWeb):
    add_template = "../usage_pattern/usage_pattern_add.html"
    attributes_to_skip_in_forms = [
        "start_date", "modeling_duration_value", "modeling_duration_unit", "initial_usage_journey_volume",
        "initial_usage_journey_volume_timespan", "net_growth_rate_in_percentage"]

    @property
    def links_to(self):
        return self.usage_journey.web_id

    @property
    def class_title_style(self):
        return "h6"

    @property
    def template_name(self):
        return "usage_pattern"

    @staticmethod
    def turn_net_growth_rate_timespan_dynamic_list_into_dynamic_select(dynamic_form_data: dict):
        dynamic_list_options = dynamic_form_data["dynamic_lists"][0]["list_value"]
        dynamic_select = {
            "input_id": "net_growth_rate_timespan",
            "filter_by": "initial_usage_journey_volume_timespan",
            "list_value": {
                key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in
                      value]
                for key, value in dynamic_list_options.items()
            }
        }

        return {"dynamic_selects": [dynamic_select]}


    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        if len(model_web.usage_journeys) == 0:
            raise PermissionError("You need to have created at least one usage journey to create a usage pattern.")
        form_sections, dynamic_form_data = generate_object_creation_structure(
            "UsagePatternFromForm",
            available_efootprint_classes=[UsagePatternFromForm],
            attributes_to_skip=cls.attributes_to_skip_in_forms,
            model_web=model_web
        )

        usage_pattern_input_values = deepcopy(UsagePatternFromForm.default_values)
        usage_pattern_input_values["initial_usage_journey_volume"] = None
        context_data = {
                "form_fields": form_sections[1]["fields"],
                "usage_pattern_input_values": usage_pattern_input_values,
                "dynamic_form_data": cls.turn_net_growth_rate_timespan_dynamic_list_into_dynamic_select(
                    dynamic_form_data),
                "header_name": "Add new usage pattern",
                "object_type": "UsagePatternFromForm",
                "obj_label": FORM_TYPE_OBJECT["UsagePatternFromForm"]["label"],
            }

        return context_data

    def generate_object_edition_context(self):
        context_data = super().generate_object_edition_context()

        context_data["dynamic_form_data"] = self.turn_net_growth_rate_timespan_dynamic_list_into_dynamic_select(
            context_data["dynamic_form_data"])

        return context_data
