"""Canvas placement shared by initial rendering and mutation responses."""


def canvas_root_lists(model_web):
    """Return the unordered root collections rendered by the model canvas."""
    return {
        "up-list": [*model_web.usage_patterns, *model_web.edge_usage_patterns],
        "uj-list": [*model_web.usage_journeys, *model_web.edge_usage_journeys],
        "external-api-list": model_web.external_apis,
        "server-list": model_web.servers,
        "edge-device-groups-list": model_web.root_edge_device_groups,
        "edge-devices-list": model_web.ungrouped_edge_devices,
    }


def has_canvas_card(obj):
    """Whether an object is a canvas root or a nested child of a rendered parent."""
    root_ids = {root.efootprint_id for roots in canvas_root_lists(obj.model_web).values() for root in roots}

    def is_rendered(candidate):
        if candidate.efootprint_id in root_ids:
            return True
        list_parents, _ = candidate.list_containers_and_attr_name_in_list_container
        dict_parents, _ = candidate.dict_containers_and_attr_name_in_dict_container
        return any(parent.renders_relationship_children_as_nested_cards and is_rendered(parent)
                   for parent in list_parents + dict_parents)

    return is_rendered(obj)
