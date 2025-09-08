from model_builder.web_core.usage.usage_pattern_web import UsagePatternWeb


class EdgeUsagePatternWeb(UsagePatternWeb):
    @property
    def links_to(self):
        return self.edge_usage_journey.web_id
