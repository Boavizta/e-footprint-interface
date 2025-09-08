from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class UsagePatternWeb(ModelingObjectWeb):
    @property
    def links_to(self):
        return self.usage_journey.web_id

    @property
    def class_title_style(self):
        return "h6"

    @property
    def template_name(self):
        return "usage_pattern"
