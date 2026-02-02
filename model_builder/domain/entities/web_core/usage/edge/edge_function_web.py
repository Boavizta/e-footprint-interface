from model_builder.domain.entities.web_core.usage.journey_step_base_web import JourneyStepBaseWeb


class EdgeFunctionWeb(JourneyStepBaseWeb):
    """Web wrapper for EdgeFunction (groups RecurrentEdgeDeviceNeeds for an EdgeUsageJourney)."""
    @property
    def child_object_types_str(self):
        # EdgeFunction can host both edge device and server recurrent needs
        return ["RecurrentEdgeDeviceNeedBase", "RecurrentServerNeed"]
