"""E2E tests for edge device groups."""
from copy import deepcopy

import pytest
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from playwright.sync_api import expect

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
        "device_name": device.name,
        "group_name": group.name,
    }


@pytest.fixture
def group_edit_system_in_browser(model_builder_page: ModelBuilderPage):
    device = EdgeDevice.from_defaults("Lobby Sensor", components=[])
    building = EdgeDeviceGroup("Building")
    floor = EdgeDeviceGroup("Floor")
    annex = EdgeDeviceGroup("Annex")

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    for obj in (device, building, floor, annex):
        add_only_update(system_data, system_to_json(obj, save_calculated_attributes=False))
    load_system_dict_into_browser(model_builder_page, system_data)

    return {
        "model_builder": model_builder_page,
        "device_name": device.name,
        "group_name": building.name,
        "sub_group_name": floor.name,
    }


@pytest.fixture
def grouped_device_system_in_browser(model_builder_page: ModelBuilderPage):
    device = EdgeDevice.from_defaults("Grouped Sensor", components=[])
    rack = EdgeDeviceGroup(
        "Rack A",
        edge_device_counts={device: SourceValue(2 * u.dimensionless)},
    )

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    add_only_update(system_data, system_to_json(rack, save_calculated_attributes=False))
    load_system_dict_into_browser(model_builder_page, system_data)

    return {
        "model_builder": model_builder_page,
        "device_name": device.name,
        "group_name": rack.name,
    }


@pytest.mark.e2e
class TestEdgeDeviceGroups:
    def test_link_update_and_unlink_edge_device_updates_infrastructure_column(self, edge_group_system_in_browser):
        model_builder = edge_group_system_in_browser["model_builder"]
        device_name = edge_group_system_in_browser["device_name"]
        group_name = edge_group_system_in_browser["group_name"]

        model_builder.ungrouped_edge_device_should_exist(device_name)
        group_card = model_builder.get_edge_device_group_card(group_name)
        group_card.should_exist()

        group_card.click_edit_button()
        model_builder.side_panel.should_be_visible()
        model_builder.side_panel.add_to_dict_count("EdgeDeviceGroup_edge_device_counts", device_name)
        model_builder.side_panel.submit_and_wait_for_close()

        model_builder.ungrouped_edge_device_should_not_exist(device_name)
        group_card.open_accordion()
        device_card = group_card.get_nested_object_card("EdgeDevice", device_name)
        device_card.should_exist().set_inline_count("3")

        model_builder.page.reload()
        model_builder.canvas.wait_for(state="visible")
        model_builder.ungrouped_edge_device_should_not_exist(device_name)
        group_card.open_accordion()
        group_card.get_nested_object_card("EdgeDevice", device_name).should_exist().inline_count_should_equal("3")

        group_card.get_nested_object_card("EdgeDevice", device_name).click_unlink_button()

        model_builder.ungrouped_edge_device_should_exist(device_name)

    def test_create_group_with_initial_members_renders_nested_content_immediately(self, edge_group_system_in_browser):
        model_builder = edge_group_system_in_browser["model_builder"]
        existing_device_name = edge_group_system_in_browser["device_name"]
        existing_group_name = edge_group_system_in_browser["group_name"]

        side_panel = model_builder.click_add_edge_device_group()
        side_panel.fill_field("EdgeDeviceGroup_name", "Building")
        side_panel.add_to_dict_count("EdgeDeviceGroup_sub_group_counts", existing_group_name, count="2")
        side_panel.add_to_dict_count("EdgeDeviceGroup_edge_device_counts", existing_device_name, count="3")
        side_panel.submit_and_wait_for_close()

        building_card = model_builder.get_edge_device_group_card("Building")
        building_card.should_exist()
        building_card.open_accordion()
        building_card.locator.locator("div[id^='EdgeDeviceGroup-']").filter(has_text=existing_group_name).first.wait_for()
        building_card.locator.locator("div[id^='EdgeDevice-']").filter(has_text=existing_device_name).first.wait_for()
        expect(building_card.locator.locator("input[name='count']").nth(0)).to_have_value("2")
        expect(building_card.locator.locator("input[name='count']").nth(1)).to_have_value("3")

        # Creating the group should immediately remove Rack A from the root list and the device from
        # the ungrouped list — no page reload required.
        expect(model_builder.page.locator("#edge-device-groups-list > div[id^='EdgeDeviceGroup-']")).to_have_count(1)
        model_builder.ungrouped_edge_device_should_not_exist(existing_device_name)

        # Create a new edge device from the add panel and attach it to Building via
        # parent_group_memberships. The new device should land inside Building, not in the ungrouped
        # list.
        new_device_name = "Rooftop Sensor"
        side_panel = model_builder.click_add_edge_device()
        model_builder.page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_object_type("EdgeDevice")
        side_panel.fill_field("EdgeDevice_name", new_device_name)
        side_panel.add_to_dict_count("parent_group_memberships", "Building", count="2")
        side_panel.submit_and_wait_for_close()

        building_card.open_accordion()
        building_card.get_nested_object_card("EdgeDevice", new_device_name).should_exist(
            ).inline_count_should_equal("2")
        model_builder.ungrouped_edge_device_should_not_exist(new_device_name)

        # Create a new child group from the add panel and attach it to Building via
        # parent_group_memberships. The new group should land inside Building, not at the root.
        new_sub_group_name = "Mezzanine"
        side_panel = model_builder.click_add_edge_device_group()
        side_panel.fill_field("EdgeDeviceGroup_name", new_sub_group_name)
        side_panel.add_to_dict_count("parent_group_memberships", "Building", count="1")
        side_panel.submit_and_wait_for_close()

        building_card.open_accordion()
        building_card.get_nested_object_card("EdgeDeviceGroup", new_sub_group_name).should_exist()
        expect(model_builder.page.locator("#edge-device-groups-list > div[id^='EdgeDeviceGroup-']")).to_have_count(1)

        # Deleting Building should promote Rack A back to the root list and restore the device to the
        # ungrouped list without a page reload.
        building_card.click_edit_button()
        model_builder.side_panel.click_delete_button()
        model_builder.side_panel.confirm_delete()

        expect(model_builder.page.locator("#edge-device-groups-list").locator(
            "div[id^='EdgeDeviceGroup-']").filter(has_text="Building")).to_have_count(0)
        model_builder.get_edge_device_group_card(existing_group_name).should_exist()
        model_builder.ungrouped_edge_device_should_exist(existing_device_name)

    def test_group_edit_panel_links_and_unlinks_members_live(self, group_edit_system_in_browser):
        model_builder = group_edit_system_in_browser["model_builder"]
        device_name = group_edit_system_in_browser["device_name"]
        group_name = group_edit_system_in_browser["group_name"]
        sub_group_name = group_edit_system_in_browser["sub_group_name"]

        building_card = model_builder.get_edge_device_group_card(group_name)
        building_card.should_exist().click_edit_button()
        side_panel = model_builder.side_panel.should_be_visible()

        side_panel.add_to_dict_count("EdgeDeviceGroup_sub_group_counts", sub_group_name, count="2")
        side_panel.add_to_dict_count("EdgeDeviceGroup_edge_device_counts", device_name, count="4")
        side_panel.submit_and_wait_for_close()

        building_card.open_accordion()
        nested_group_card = building_card.get_nested_object_card("EdgeDeviceGroup", sub_group_name)
        nested_group_card.should_exist()
        model_builder.ungrouped_edge_device_should_not_exist(device_name)
        nested_device_card = building_card.get_nested_object_card("EdgeDevice", device_name)
        nested_device_card.should_exist()
        nested_device_card.inline_count_should_equal("4")

        nested_group_card.open_accordion()
        nested_group_card.accordion_should_be_open()

        building_card.click_edit_button()
        side_panel = model_builder.side_panel.should_be_visible()
        side_panel.remove_from_dict_count("EdgeDeviceGroup_edge_device_counts", device_name)
        side_panel.remove_from_dict_count("EdgeDeviceGroup_sub_group_counts", sub_group_name)
        side_panel.submit_and_wait_for_close()

        model_builder.ungrouped_edge_device_should_exist(device_name)
        model_builder.get_edge_device_group_card(sub_group_name).should_exist()

    def test_device_edit_panel_updates_and_removes_group_membership(self, grouped_device_system_in_browser):
        model_builder = grouped_device_system_in_browser["model_builder"]
        device_name = grouped_device_system_in_browser["device_name"]
        group_name = grouped_device_system_in_browser["group_name"]

        rack_card = model_builder.get_edge_device_group_card(group_name)
        rack_card.open_accordion()
        grouped_device_card = rack_card.get_nested_object_card("EdgeDevice", device_name)
        grouped_device_card.should_exist().click_edit_button()

        side_panel = model_builder.side_panel.should_be_visible().should_contain_text("Group membership")
        side_panel.should_contain_text(group_name)

        side_panel.set_group_membership_count(group_name, "6")
        rack_card.get_nested_object_card("EdgeDevice", device_name).inline_count_should_equal("6")

        side_panel.remove_group_membership(group_name)
        model_builder.ungrouped_edge_device_should_exist(device_name)
        expect(rack_card.locator.locator("div[id^='EdgeDevice-']").filter(has_text=device_name)).to_have_count(0)
