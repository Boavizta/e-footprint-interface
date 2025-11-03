from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_builders.services.external_api_web import ExternalApiWeb
from model_builder.web_builders.services.service_web import ServiceWeb
from model_builder.web_builders.hardware.edge.edge_appliance_web import EdgeApplianceWeb
from model_builder.web_builders.hardware.edge.edge_computer_web import EdgeComputerWeb
from model_builder.web_core.hardware.edge.edge_device_web import EdgeDeviceWeb
from model_builder.web_core.hardware.server_web import ServerWeb
from model_builder.web_core.hardware.storage_web import StorageWeb
from model_builder.web_core.usage.edge.edge_function_web import EdgeFunctionWeb
from model_builder.web_core.usage.edge.edge_usage_journey_web import EdgeUsageJourneyWeb
from model_builder.web_core.usage.edge.edge_usage_pattern_web import EdgeUsagePatternWeb
from model_builder.web_core.usage.job_web import JobWeb
from model_builder.web_core.usage.edge.recurrent_edge_device_need_web import RecurrentEdgeDeviceNeedWeb
from model_builder.web_core.usage.usage_journey_step_web import UsageJourneyStepWeb
from model_builder.web_core.usage.usage_journey_web import UsageJourneyWeb
from model_builder.web_core.usage.usage_pattern_web import UsagePatternWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING = {
    "Server": ServerWeb,
    "ServerBase": ServerWeb,
    "GPUServer": ServerWeb,
    "BoaviztaCloudServer": ServerWeb,
    "UsageJourneyStep": UsageJourneyStepWeb,
    "UsageJourney": UsageJourneyWeb,
    "UsagePattern": UsagePatternWeb,
    "EdgeUsagePattern": EdgeUsagePatternWeb,
    "JobBase": JobWeb,
    "Job": JobWeb,
    "GPUJob": JobWeb,
    "GenAIJob": JobWeb,
    "VideoStreamingJob": JobWeb,
    "WebApplicationJob": JobWeb,
    # Is not an efootprint class but rather a builder that creates efootprint objects
    "ExternalApi": ExternalApiWeb,
    "Service": ServiceWeb,
    "GenAIModel": ServiceWeb,
    "VideoStreaming": ServiceWeb,
    "WebApplication": ServiceWeb,
    "Storage": StorageWeb,
    # Edge hardware classes
    "EdgeDevice": EdgeDeviceWeb,
    "EdgeComputer": EdgeComputerWeb,
    "EdgeAppliance": EdgeApplianceWeb,
    "EdgeStorage": ModelingObjectWeb,
    # Edge usage classes
    "EdgeUsageJourney": EdgeUsageJourneyWeb,
    "EdgeFunction": EdgeFunctionWeb,
    "RecurrentEdgeDeviceNeed": RecurrentEdgeDeviceNeedWeb,
    "RecurrentEdgeProcess": RecurrentEdgeDeviceNeedWeb,
    "RecurrentEdgeWorkload": RecurrentEdgeDeviceNeedWeb,
}

def wrap_efootprint_object(modeling_obj: ModelingObject, model_web: "ModelWeb"):
    if modeling_obj.class_as_simple_str in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING:
        return EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[modeling_obj.class_as_simple_str](modeling_obj, model_web)

    return ModelingObjectWeb(modeling_obj, model_web)
