CARD_ORDER_CONTEXT_NAMES = {
    "up-list": "ordered_usage_patterns",
    "uj-list": "ordered_usage_journeys",
    "external-api-list": "ordered_external_apis",
    "server-list": "ordered_servers",
    "edge-device-groups-list": "ordered_root_edge_device_groups",
    "edge-devices-list": "ordered_ungrouped_edge_devices",
}

CARD_ORDER_LIST_IDS = tuple(CARD_ORDER_CONTEXT_NAMES)


def stable_rank_merge(objects, saved_ids):
    """Return current objects in saved order, followed by unranked objects in natural order."""
    objects = list(objects)
    if not isinstance(saved_ids, list):
        return objects

    objects_by_id = {obj.web_id: obj for obj in objects}
    ranked_ids = set()
    ordered = []
    for web_id in saved_ids:
        if web_id in objects_by_id and web_id not in ranked_ids:
            ordered.append(objects_by_id[web_id])
            ranked_ids.add(web_id)
    ordered.extend(obj for obj in objects if obj.web_id not in ranked_ids)
    return ordered


def ordered_card_lists(model_web):
    """Build the six model-canvas lists from repository-owned interface configuration."""
    interface_config = model_web.repository.interface_config
    card_order = interface_config.get("card_order", {}) if isinstance(interface_config, dict) else {}
    if not isinstance(card_order, dict):
        card_order = {}

    current_objects = {
        "up-list": [*model_web.usage_patterns, *model_web.edge_usage_patterns],
        "uj-list": [*model_web.usage_journeys, *model_web.edge_usage_journeys],
        "external-api-list": model_web.external_apis,
        "server-list": model_web.servers,
        "edge-device-groups-list": model_web.root_edge_device_groups,
        "edge-devices-list": model_web.ungrouped_edge_devices,
    }
    return {
        CARD_ORDER_CONTEXT_NAMES[list_id]: stable_rank_merge(current_objects[list_id], card_order.get(list_id, []))
        for list_id in CARD_ORDER_LIST_IDS
    }
