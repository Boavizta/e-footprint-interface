from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_builders.services.external_api_web import ExternalApiWeb
from model_builder.web_builders.services.service_web import ServiceWeb
from model_builder.web_builders.hardware.edge.edge_appliance_web import EdgeApplianceWeb
from model_builder.web_builders.hardware.edge.edge_computer_web import EdgeComputerWeb
from model_builder.web_builders.usage.edge.recurrent_edge_process_web import RecurrentEdgeProcessWeb
from model_builder.web_builders.usage.edge.recurrent_edge_workload_web import RecurrentEdgeWorkloadWeb
from model_builder.web_core.hardware.edge.edge_component_base_web import EdgeComponentWeb
from model_builder.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb
from model_builder.web_core.hardware.edge.edge_device_web import EdgeDeviceWeb
from model_builder.web_core.hardware.server_web import ServerWeb
from model_builder.web_core.hardware.storage_web import StorageWeb
from model_builder.web_core.usage.edge.edge_function_web import EdgeFunctionWeb
from model_builder.web_core.usage.edge.edge_usage_pattern_web import EdgeUsagePatternWeb
from model_builder.web_core.usage.edge.recurrent_edge_component_need_web import RecurrentEdgeComponentNeedWeb
from model_builder.web_core.usage.edge.recurrent_edge_device_need_web import RecurrentEdgeDeviceNeedWeb
from model_builder.web_core.usage.job_web import JobWeb
from model_builder.web_core.usage.edge.recurrent_edge_device_need_base_web import RecurrentEdgeDeviceNeedBaseWeb
from model_builder.web_core.usage.journey_base_web import JourneyBaseWeb
from model_builder.web_core.usage.journey_step_base_web import JourneyStepBaseWeb
from model_builder.web_core.usage.usage_pattern_web import UsagePatternWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING = {
    "Server": ServerWeb,
    "ServerBase": ServerWeb,
    "GPUServer": ServerWeb,
    "BoaviztaCloudServer": ServerWeb,
    "UsageJourneyStep": JourneyStepBaseWeb,
    "UsageJourney": JourneyBaseWeb,
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
    "EdgeDeviceBase": EdgeDeviceBaseWeb,
    "EdgeDevice": EdgeDeviceWeb,
    "EdgeComputer": EdgeComputerWeb,
    "EdgeAppliance": EdgeApplianceWeb,
    "EdgeComponent": EdgeComponentWeb,
    "EdgeCPUComponent": EdgeComponentWeb,
    "EdgeRAMComponent": EdgeComponentWeb,
    "EdgeStorage": EdgeComponentWeb,
    "EdgeWorkloadComponent": EdgeComponentWeb,
    # Edge usage classes
    "EdgeUsageJourney": JourneyBaseWeb,
    "EdgeFunction": EdgeFunctionWeb,
    "RecurrentEdgeDeviceNeedBase": RecurrentEdgeDeviceNeedBaseWeb,
    "RecurrentEdgeProcess": RecurrentEdgeProcessWeb,
    "RecurrentEdgeWorkload": RecurrentEdgeWorkloadWeb,
    "RecurrentEdgeDeviceNeed": RecurrentEdgeDeviceNeedWeb,
    "RecurrentEdgeComponentNeed": RecurrentEdgeComponentNeedWeb,
}

def wrap_efootprint_object(modeling_obj: ModelingObject, model_web: "ModelWeb", list_container=None):
    if modeling_obj.class_as_simple_str in EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING:
        return EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[modeling_obj.class_as_simple_str](modeling_obj, model_web, list_container)

    return ModelingObjectWeb(modeling_obj, model_web, list_container)
