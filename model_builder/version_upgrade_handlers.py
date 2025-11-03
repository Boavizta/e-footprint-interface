from efootprint.logger import logger
from efootprint.api_utils.version_upgrade_handlers import rename_dict_key


def _merge_or_rename(system_dict, old_key, new_key):
    """Rename dict key or merge into an existing one."""
    if new_key in system_dict:
        system_dict[new_key].update(system_dict.pop(old_key))
    else:
        rename_dict_key(system_dict, old_key, new_key)


def _upgrade_usage_pattern(system_dict, class_name, prefix=""):
    """Upgrade UsagePatternFromForm and EdgeUsagePatternFromForm objects."""
    if class_name not in system_dict:
        return

    base_class = class_name.replace("FromForm", "")
    attr_name = f"hourly_{prefix}usage_journey_starts"

    for obj_dict in system_dict[class_name].values():
        obj_dict[attr_name] = {"form_inputs": {}, "label": f"{attr_name} in {obj_dict['name']}",
                               "source": {"name": "user data", "link": None}}
        for field in [
            "start_date", "modeling_duration_value", "modeling_duration_unit",
            f"initial_{prefix}usage_journey_volume", f"initial_{prefix}usage_journey_volume_timespan",
            "net_growth_rate_in_percentage", "net_growth_rate_timespan",
        ]:
            # remove prefix when copying
            new_field = field.replace(f"{prefix}usage_journey_", "")
            obj_dict[attr_name]["form_inputs"][new_field] = obj_dict[field]["value"]
            del obj_dict[field]

    _merge_or_rename(system_dict, class_name, base_class)


def _upgrade_recurrent_constants(system_dict, class_name, recurrent_fields):
    """Generic upgrader for Recurrent*FromForm objects."""
    if class_name not in system_dict:
        return

    base_class = class_name.replace("FromForm", "")

    for obj_dict in system_dict[class_name].values():
        for field in recurrent_fields:
            constant_field = field.replace("recurrent", "constant")
            obj_dict[field] = {
                "form_inputs": {
                    "constant_value": obj_dict[constant_field]["value"],
                    "constant_unit": obj_dict[constant_field]["unit"],
                },
                "label": obj_dict[constant_field]["label"],
                "source": obj_dict[constant_field].get("source", None)
            }
            del obj_dict[constant_field]

    _merge_or_rename(system_dict, class_name, base_class)


def upgrade_interface_version_pre_14(system_dict):
    """
    Upgrade interface data for systems created with efootprint < v14.
    Transforms:
      - FromForm classes to base classes
      - Old form input fields to new Explainable* formats
    """
    logger.info("Applying interface upgrade handler for version 14 (FromForm -> base classes)")

    # Handle UsagePattern and EdgeUsagePattern
    prefix_mapping = {
        "UsagePatternFromForm": "",
        "EdgeUsagePatternFromForm": "edge_",
    }
    for cls, prefix in prefix_mapping.items():
        _upgrade_usage_pattern(system_dict, cls, prefix)

    # Handle recurrent patterns
    _upgrade_recurrent_constants(
        system_dict,
        "RecurrentEdgeProcessFromForm",
        ["recurrent_compute_needed", "recurrent_ram_needed", "recurrent_storage_needed"],
    )
    _upgrade_recurrent_constants(
        system_dict,
        "RecurrentWorkloadFromForm",
        ["recurrent_workload"],
    )

    return system_dict


INTERFACE_VERSION_UPGRADE_HANDLERS = {
    14: upgrade_interface_version_pre_14,
}
