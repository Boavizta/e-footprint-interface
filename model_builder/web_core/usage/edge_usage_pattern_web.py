from copy import deepcopy

from model_builder.class_structure import generate_object_creation_structure
from model_builder.efootprint_extensions.edge_usage_pattern_from_form import EdgeUsagePatternFromForm
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_core.usage.usage_pattern_web import UsagePatternWeb


class EdgeUsagePatternWeb(UsagePatternWeb):
    @property
    def links_to(self):
        return self.edge_usage_journey.web_id

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        if len(model_web.edge_usage_journeys) == 0:
            raise PermissionError(
                "You need to have created at least one edge usage journey to create an edge usage pattern.")
        form_sections, dynamic_form_data = generate_object_creation_structure(
            "EdgeUsagePatternFromForm",
            available_efootprint_classes=[EdgeUsagePatternFromForm],
            attributes_to_skip=cls.attributes_to_skip_in_forms,
            model_web=model_web
        )

        usage_pattern_input_values = deepcopy(EdgeUsagePatternFromForm.default_values)
        usage_pattern_input_values["initial_edge_usage_journey_volume"] = None

        context_data = {
            "form_fields": form_sections[1]["fields"],
            "usage_pattern_input_values": usage_pattern_input_values,
            "dynamic_form_data": cls.turn_net_growth_rate_timespan_dynamic_list_into_dynamic_select(
                dynamic_form_data),
            "header_name": "Add new edge usage pattern",
            "object_type": "EdgeUsagePatternFromForm",
            "obj_label": FORM_TYPE_OBJECT["EdgeUsagePatternFromForm"]["label"],
        }

        return context_data
