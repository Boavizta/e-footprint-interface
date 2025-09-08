from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.usage.usage_journey_step_web import UsageJourneyStepWeb


class JobWeb(ModelingObjectWeb):
    @property
    def web_id(self):
        raise PermissionError(f"JobWeb objects don’t have a web_id attribute because their html "
                             f"representation should be managed by the MirroredJobWeb object")

    @property
    def mirrored_cards(self):
        mirrored_cards = []
        for usage_journey_step in self.usage_journey_steps:
            for mirrored_usage_journey_card in usage_journey_step.mirrored_cards:
                mirrored_cards.append(MirroredJobWeb(self._modeling_obj, mirrored_usage_journey_card))

        return mirrored_cards


class MirroredJobWeb(ModelingObjectWeb):
    def __init__(self, modeling_obj: ModelingObject, uj_step: "UsageJourneyStepWeb"):
        super().__init__(modeling_obj, uj_step.model_web)
        self.usage_journey_step = uj_step

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["usage_journey_step"]

    @property
    def template_name(self):
        return "job"

    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self.efootprint_id}_in_{self.usage_journey_step.web_id}"

    @property
    def links_to(self):
        return self.server.web_id

    @property
    def accordion_parent(self):
        return self.usage_journey_step

    @property
    def class_title_style(self):
        return "h8"
