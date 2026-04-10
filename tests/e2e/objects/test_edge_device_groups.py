"""E2E tests for edge device groups."""
from copy import deepcopy

import pytest
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import EMPTY_SYSTEM_DICT, add_only_update


@pytest.fixture
def edge_group_system_in_browser(model_builder_page: ModelBuilderPage):
    device = EdgeDevice.from_defaults("Shared Edge Device", components=[])
    group = EdgeDeviceGroup("Rack A")

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    add_only_update(system_data, system_to_json(device, save_calculated_attributes=False))
    add_only_update(system_data, system_to_json(group, save_calculated_attributes=False))
    load_system_dict_into_browser(model_builder_page, system_data)

    return {
        "model_builder": model_builder_page,
        "device_id": device.id,
        "device_name": device.name,
        "group_id": group.id,
        "group_name": group.name,
    }


@pytest.mark.e2e
class TestEdgeDeviceGroups:
    def test_link_update_and_unlink_edge_device_updates_infrastructure_column(self, edge_group_system_in_browser):
        model_builder = edge_group_system_in_browser["model_builder"]
        device_id = edge_group_system_in_browser["device_id"]
        device_name = edge_group_system_in_browser["device_name"]
        group_id = edge_group_system_in_browser["group_id"]
        group_name = edge_group_system_in_browser["group_name"]

        model_builder.ungrouped_edge_device_should_exist(device_name)
        model_builder.get_edge_device_group_card(group_name).should_exist()

        model_builder.trigger_htmx_post(f"/model_builder/link-dict-entry/{group_id}/{device_id}/")

        model_builder.ungrouped_edge_device_should_not_exist(device_name)
        model_builder.get_edge_device_group_card(group_name).open_accordion()
        model_builder.get_object_card("EdgeDevice", device_name).should_exist()
        model_builder.trigger_htmx_post(
            f"/model_builder/update-dict-count/{group_id}/{device_id}/",
            values={"count": "3"},
            trigger_id="test-htmx-count-trigger",
        )

        model_builder.page.reload()
        model_builder.canvas.wait_for(state="visible")
        model_builder.ungrouped_edge_device_should_not_exist(device_name)
        model_builder.get_edge_device_group_card(group_name).open_accordion()
        model_builder.get_object_card("EdgeDevice", device_name).should_exist().inline_count_should_equal("3")

        model_builder.trigger_htmx_post(
            f"/model_builder/unlink-dict-entry/{group_id}/{device_id}/",
            trigger_id="test-htmx-unlink-trigger",
        )

        model_builder.ungrouped_edge_device_should_exist(device_name)
