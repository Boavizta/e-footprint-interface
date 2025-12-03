from model_builder.domain.entities.web_core.usage.journey_step_base_web import JourneyStepBaseWeb


class EdgeFunctionWeb(JourneyStepBaseWeb):
    """Web wrapper for EdgeFunction (groups RecurrentEdgeDeviceNeeds for an EdgeUsageJourney)."""
    @property
    def child_object_type_str(self) -> str:
        return "RecurrentEdgeDeviceNeedBase"
