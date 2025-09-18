from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm
from model_builder.web_core.usage.usage_pattern_web_base_class import (UsagePatternWebBaseClass,
                                                                       generate_attributes_to_skip_in_forms)


class UsagePatternWeb(UsagePatternWebBaseClass):
    object_type_in_volume = "usage_journey"
    associated_efootprint_class = UsagePatternFromForm
    attributes_to_skip_in_forms = generate_attributes_to_skip_in_forms(object_type_in_volume)

    @property
    def links_to(self):
        return self.usage_journey.web_id
