from model_builder.web_core.usage.usage_pattern_web_base_class import UsagePatternWebBaseClass


class EdgeUsagePatternWeb(UsagePatternWebBaseClass):
    attr_name_in_system = "edge_usage_patterns"

    @property
    def links_to(self):
        return self.edge_usage_journey.web_id
