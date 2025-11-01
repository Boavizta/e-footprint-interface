from sys import prefix

from efootprint.logger import logger
from efootprint.api_utils.version_upgrade_handlers import rename_dict_key


def upgrade_interface_version_pre_14(system_dict):
    """
    Upgrade interface data for systems created with efootprint < v14.

    This handler transforms FromForm class references to base class references:
    - UsagePatternFromForm -> UsagePattern
    - EdgeUsagePatternFromForm -> EdgeUsagePattern
    - RecurrentEdgeProcessFromForm -> RecurrentEdgeProcess
    - RecurrentEdgeWorkloadFromForm -> RecurrentEdgeWorkload

    It also transforms the stored form data structure to match the new
    ExplainableHourlyQuantitiesFromFormInputs and ExplainableRecurrentQuantitiesFromConstant
    formats.
    """
    logger.info("Applying interface upgrade handler for version 14 (FromForm -> base classes)")
    prefix_mapping = {"UsagePatternFromForm": "", "EdgeUsagePatternFromForm": "edge_"}

    for efootprint_class_str in ["UsagePatternFromForm", "EdgeUsagePatternFromForm"]:
        if efootprint_class_str in system_dict:
            base_class_str = efootprint_class_str.replace("FromForm", "")
            prefix = prefix_mapping[efootprint_class_str]
            attr_name = f"hourly_{prefix}usage_journey_starts"
            rename_dict_key(system_dict, efootprint_class_str, base_class_str)
            logger.info(f"Renamed class key '{efootprint_class_str}' to '{base_class_str}'")
            for obj_key, obj_dict in system_dict[base_class_str].items():
                obj_dict[attr_name] = {}
                for form_field in [
                    "start_date", "modeling_duration_value", "modeling_duration_unit",
                    f"initial_{prefix}usage_journey_volume", f"initial_{prefix}usage_journey_volume_timespan",
                    "net_growth_rate_in_percentage", "net_growth_rate_timespan"]:
                    obj_dict[attr_name][form_field.replace(f"{prefix}usage_journey_", "")] = obj_dict[form_field]["value"]
                    del obj_dict[form_field]
                obj_dict[attr_name]["label"] = f"{attr_name} in {obj_dict['name']}"

    if "RecurrentEdgeProcessFromForm" in system_dict:
        rename_dict_key(system_dict, "RecurrentEdgeProcessFromForm", "RecurrentEdgeProcess")
        logger.info("Renamed class key 'RecurrentEdgeProcessFromForm' to 'RecurrentEdgeProcess'")
        for obj_key, obj_dict in system_dict["RecurrentEdgeProcess"].items():
            for field in ["recurrent_compute_needed", "recurrent_ram_needed", "recurrent_storage_needed"]:
                constant_field = field.replace("recurrent", "constant")
                obj_dict[field] = {"constant_value": obj_dict[constant_field]["value"],
                                   "constant_unit": obj_dict[constant_field]["unit"]}
                del obj_dict[constant_field]
                obj_dict[field]["label"] = f"{field} in {obj_dict['name']}"

    if "RecurrentWorkloadFromForm" in system_dict:
        rename_dict_key(system_dict, "RecurrentWorkloadFromForm", "RecurrentWorkload")
        logger.info("Renamed class key 'RecurrentWorkloadFromForm' to 'RecurrentWorkload'")
        for obj_key, obj_dict in system_dict["RecurrentWorkload"].items():
            for field in ["recurrent_workload"]:
                constant_field = field.replace("recurrent", "constant")
                obj_dict[field] = {"constant_value": obj_dict[constant_field]["value"],
                                   "constant_unit": obj_dict[constant_field]["unit"]}
                del obj_dict[constant_field]
                obj_dict[field]["label"] = f"{field} in {obj_dict['name']}"

    return system_dict


INTERFACE_VERSION_UPGRADE_HANDLERS = {
    14: upgrade_interface_version_pre_14,
}
