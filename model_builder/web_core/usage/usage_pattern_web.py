from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.web_core.usage.usage_pattern_web_base_class import (
    UsagePatternFromFormWebBaseClass, generate_attributes_to_skip_in_forms, UsagePatternWebBaseClass)


class UsagePatternWeb(UsagePatternWebBaseClass):
    attr_name_in_system = "usage_patterns"

    @property
    def links_to(self):
        return self.usage_journey.web_id


class UsagePatternFromFormWeb(UsagePatternFromFormWebBaseClass):
    associated_efootprint_class = UsagePatternFromForm
    attr_name_in_system = "usage_patterns"
    object_type_in_volume = "usage_journey"
    attributes_to_skip_in_forms = generate_attributes_to_skip_in_forms(object_type_in_volume)

    @property
    def links_to(self):
        return self.usage_journey.web_id
