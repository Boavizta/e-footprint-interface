from model_builder.efootprint_extensions.edge_usage_pattern_from_form import EdgeUsagePatternFromForm
from model_builder.web_core.usage.usage_pattern_web_base_class import (UsagePatternWebBaseClass,
                                                                       generate_attributes_to_skip_in_forms)


class EdgeUsagePatternWeb(UsagePatternWebBaseClass):
    associated_efootprint_class = EdgeUsagePatternFromForm
    attr_name_in_system = "edge_usage_patterns"
    object_type_in_volume = "edge_usage_journey"
    attributes_to_skip_in_forms = generate_attributes_to_skip_in_forms(object_type_in_volume)

    @property
    def links_to(self):
        return self.edge_usage_journey.web_id
