from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_that_can_be_mirrored import \
    ModelingObjectWebThatCanBeMirrored
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.usage.edge_usage_journey_web import EdgeUsageJourneyWeb


class RecurrentEdgeProcessWeb(ModelingObjectWebThatCanBeMirrored):
    @property
    def mirrored_cards(self):
        mirrored_cards = []
        for edge_usage_journey in self.edge_usage_journeys:
            mirrored_cards.append(MirroredRecurrentEdgeProcessWeb(self._modeling_obj, edge_usage_journey))

        return mirrored_cards


class RecurrentEdgeProcessWebFromFormWeb(RecurrentEdgeProcessWeb):
    # This class exists because the default generate_object_creation_context method uses the class name
    pass


class MirroredRecurrentEdgeProcessWeb(ModelingObjectWeb):
    def __init__(self, modeling_obj: ModelingObject, euj: "EdgeUsageJourneyWeb"):
        super().__init__(modeling_obj, euj.model_web)
        self.edge_usage_journey = euj

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["edge_usage_journey"]

    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self.efootprint_id}_in_{self.edge_usage_journey.web_id}"

    @property
    def accordion_parent(self):
        return self.edge_usage_journey

    @property
    def class_title_style(self):
        return "h8"
