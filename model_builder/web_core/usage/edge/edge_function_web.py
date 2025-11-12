from model_builder.web_core.usage.journey_step_base_web import JourneyStepBaseWeb


class EdgeFunctionWeb(JourneyStepBaseWeb):
    """Web wrapper for EdgeFunction (groups RecurrentEdgeDeviceNeeds for an EdgeUsageJourney)."""
    @property
    def child_object_type_str(self) -> str:
        return "RecurrentEdgeDeviceNeedBase"

    @property
    def links_to(self):
        """Links to the edge devices used by this function's resource needs."""
        linked_edge_device_ids = set([rern.edge_device.web_id for rern in self.recurrent_edge_device_needs])
        return "|".join(sorted(linked_edge_device_ids))
