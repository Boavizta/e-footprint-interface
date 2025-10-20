from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_that_can_be_mirrored import \
    ModelingObjectWebThatCanBeMirrored

if TYPE_CHECKING:
    from model_builder.web_core.usage.edge_usage_journey_web import EdgeUsageJourneyWeb


class EdgeFunctionWeb(ModelingObjectWebThatCanBeMirrored):
    """Web wrapper for EdgeFunction (groups RecurrentEdgeResourceNeeds for an EdgeUsageJourney)."""

    @property
    def mirrored_cards(self):
        """Create mirrored cards for each edge usage journey this function is linked to."""
        mirrored_cards = []
        for edge_usage_journey in self.edge_usage_journeys:
            mirrored_cards.append(MirroredEdgeFunctionWeb(self._modeling_obj, edge_usage_journey))

        return mirrored_cards


class MirroredEdgeFunctionWeb(EdgeFunctionWeb):
    """Mirrored version of EdgeFunction shown within a specific EdgeUsageJourney context."""

    def __init__(self, modeling_obj: ModelingObject, edge_usage_journey: "EdgeUsageJourneyWeb"):
        super().__init__(modeling_obj, edge_usage_journey.model_web)
        self.edge_usage_journey = edge_usage_journey

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["edge_usage_journey"]

    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self.efootprint_id}_in_{self.edge_usage_journey.web_id}"

    @property
    def links_to(self):
        """Links to the edge devices used by this function's resource needs."""
        linked_edge_device_ids = set([rern.edge_device.web_id for rern in self.recurrent_edge_resource_needs])
        return "|".join(sorted(linked_edge_device_ids))

    @property
    def accordion_parent(self):
        return self.edge_usage_journey

    @property
    def accordion_children(self):
        return self.recurrent_edge_resource_needs

    @property
    def recurrent_edge_resource_needs(self):
        """Returns web-wrapped recurrent edge resource needs with mirrored context."""
        from model_builder.web_core.usage.recurrent_edge_resource_need_web import MirroredRecurrentEdgeResourceNeedWeb

        web_resource_needs = []
        for rern in self._modeling_obj.recurrent_edge_resource_needs:
            web_resource_needs.append(MirroredRecurrentEdgeResourceNeedWeb(rern, self))

        return web_resource_needs

    @property
    def class_title_style(self):
        return "h7"
