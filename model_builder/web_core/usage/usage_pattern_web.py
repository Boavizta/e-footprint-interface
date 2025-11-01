from model_builder.web_core.usage.usage_pattern_web_base_class import UsagePatternWebBaseClass


class UsagePatternWeb(UsagePatternWebBaseClass):
    attr_name_in_system = "usage_patterns"

    @property
    def links_to(self):
        return self.usage_journey.web_id
