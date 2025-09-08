from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_builders.services.service_web import ServiceWeb
from model_builder.web_core.hardware.edge_device_web import EdgeDeviceWeb
from model_builder.web_core.hardware.server_web import ServerWeb
from model_builder.web_core.usage.edge_usage_journey_web import EdgeUsageJourneyWeb
from model_builder.web_core.usage.edge_usage_pattern_web import EdgeUsagePatternWeb
from model_builder.web_core.usage.job_web import JobWeb
from model_builder.web_core.usage.recurrent_edge_process_web import RecurrentEdgeProcessFromFormWeb
from model_builder.web_core.usage.usage_journey_step_web import UsageJourneyStepWeb
from model_builder.web_core.usage.usage_journey_web import UsageJourneyWeb
from model_builder.web_core.usage.usage_pattern_web import UsagePatternWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING = {
    "Server": ServerWeb,
    "GPUServer": ServerWeb,
    "BoaviztaCloudServer": ServerWeb,
    "UsageJourneyStep": UsageJourneyStepWeb,
    "UsageJourney": UsageJourneyWeb,
    "UsagePattern": UsagePatternWeb,
    "UsagePatternFromForm": UsagePatternWeb,
    "EdgeUsagePattern": EdgeUsagePatternWeb,
    "EdgeUsagePatternFromForm": EdgeUsagePatternWeb,
    "Job": JobWeb,
    "GPUJob": JobWeb,
    "GenAIJob": JobWeb,
    "VideoStreamingJob": JobWeb,
    "WebApplicationJob": JobWeb,
    "GenAIModel": ServiceWeb,
    "VideoStreaming": ServiceWeb,
    "WebApplication": ServiceWeb,
    "Storage": ModelingObjectWeb,
    "EdgeDevice": EdgeDeviceWeb,
    "EdgeStorage": ModelingObjectWeb,
    "EdgeUsageJourney": EdgeUsageJourneyWeb,
    "RecurrentEdgeProcessFromForm": RecurrentEdgeProcessFromFormWeb,
}

def wrap_efootprint_object(modeling_obj: ModelingObject, model_web: "ModelWeb"):
    if modeling_obj.class_as_simple_str in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING.keys():
        return EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[modeling_obj.class_as_simple_str](modeling_obj, model_web)

    return ModelingObjectWeb(modeling_obj, model_web)
