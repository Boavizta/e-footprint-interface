from model_builder.web_core.usage.journey_step_base_web import JourneyStepBaseWeb, MirroredJourneyStepBaseWeb


class EdgeFunctionWeb(JourneyStepBaseWeb):
    """Web wrapper for EdgeFunction (groups RecurrentEdgeResourceNeeds for an EdgeUsageJourney)."""

    @property
    def mirrored_cards(self):
        """Create mirrored cards for each edge usage journey this function is linked to."""
        mirrored_cards = []
        for edge_usage_journey in self.edge_usage_journeys:
            mirrored_cards.append(MirroredEdgeFunctionWeb(self._modeling_obj, edge_usage_journey))

        return mirrored_cards


class MirroredEdgeFunctionWeb(MirroredJourneyStepBaseWeb):
    """Mirrored version of EdgeFunction shown within a specific EdgeUsageJourney context."""

    @property
    def child_object_type_str(self):
        return "RecurrentEdgeResourceNeed"

    @property
    def child_template_name(self):
        return "resource_need"

    @property
    def add_child_label(self):
        return "Add recurrent edge resource need"

    @property
    def children_property_name(self):
        return "recurrent_edge_resource_needs"

    @property
    def links_to(self):
        """Links to the edge devices used by this function's resource needs."""
        linked_edge_device_ids = set([rern.edge_device.web_id for rern in self.recurrent_edge_resource_needs])
        return "|".join(sorted(linked_edge_device_ids))

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
