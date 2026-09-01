"""End-to-end coverage for weekly recurrent-quantity authoring and persistence."""

import json
from copy import deepcopy

import pytest
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.timeseries import ExplainableRecurrentQuantitiesFromConstant
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from playwright.sync_api import expect

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import EMPTY_SYSTEM_DICT


@pytest.fixture
def recurrent_process_model(edge_modeling_enabled: ModelBuilderPage) -> ModelBuilderPage:
    edge_storage = EdgeStorage.from_defaults("Weekly storage")
    edge_device = EdgeComputer.from_defaults("Weekly computer", storage=edge_storage)
    process = RecurrentEdgeProcess(
        "Weekly process",
        edge_device=edge_device,
        recurrent_compute_needed=ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 1, "constant_unit": "cpu_core"}
        ),
        recurrent_ram_needed=ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 1, "constant_unit": "GB_ram"}
        ),
        recurrent_storage_needed=ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 0, "constant_unit": "GB_stored"}
        ),
    )
    function = EdgeFunction("Weekly function", recurrent_edge_device_needs=[process], recurrent_server_needs=[])
    journey = EdgeUsageJourney.from_defaults("Weekly journey", edge_functions=[function])
    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    system_data.update(system_to_json(journey, save_computed_state=False))
    return load_system_dict_into_browser(edge_modeling_enabled, system_data)


def open_process_editor(model_builder: ModelBuilderPage) -> None:
    journey = model_builder.get_object_card("EdgeUsageJourney", "Weekly journey")
    function = model_builder.get_object_card("EdgeFunction", "Weekly function")
    process = model_builder.get_object_card("RecurrentEdgeProcess", "Weekly process")
    if not function.locator.is_visible():
        journey.open_accordion()
    if not process.locator.is_visible():
        function.open_accordion()
    process.click_edit_button()


@pytest.mark.e2e
def test_weekly_pattern_save_reopen_and_download_upload_round_trip(recurrent_process_model: ModelBuilderPage, tmp_path):
    model_builder = recurrent_process_model
    page = model_builder.page
    side_panel = model_builder.side_panel
    field_id = "RecurrentEdgeProcess_recurrent_compute_needed"

    open_process_editor(model_builder)
    selector = page.locator(f"#{field_id}__builder_selector")
    expect(selector).to_have_value("constant")
    selector.select_option("weekly_pattern")

    editor = page.locator(f"#{field_id}__builder [data-weekly-pattern-editor]")
    profile_list = editor.locator("[data-weekly-profile]")
    expect(profile_list).to_have_count(2)
    expect(page.locator(f"#{field_id}")).to_be_disabled()
    expect(editor.locator("[data-weekly-pattern-payload]")).to_be_enabled()

    weekday = profile_list.nth(0)
    weekday.locator("[data-action='add-weekly-range']").click()
    time_range = weekday.locator("[data-weekly-range]")
    time_range.locator("[data-range-end]").fill("18")
    time_range.locator("[data-range-start]").fill("8")
    time_range.locator("[data-range-value]").fill("5")

    editor.locator("[data-action='add-weekly-profile']").click()
    expect(profile_list).to_have_count(3)
    profile_list.nth(2).locator("[data-profile-name]").fill("unused")

    selector.select_option("constant")
    page.locator(f"#{field_id}").fill("11")
    expect(page.locator(f"#{field_id}")).to_have_value("11")
    selector.select_option("weekly_pattern")
    expect(time_range.locator("[data-range-value]")).to_have_value("5")

    monday = weekday.locator("[data-profile-day][value='0']")
    monday.uncheck()
    side_panel.submit_button.click()
    expect(side_panel.form).to_be_visible()
    expect(editor.locator("[data-weekly-error]")).to_contain_text("Mon must be assigned")
    monday.check()

    side_panel.submit_and_wait_for_close()
    open_process_editor(model_builder)
    expect(page.locator(f"#{field_id}__builder_selector")).to_have_value("weekly_pattern")
    editor = page.locator(f"#{field_id}__builder [data-weekly-pattern-editor]")
    expect(editor.locator("[data-weekly-profile]")).to_have_count(3)
    expect(editor.locator("[data-profile-name]").nth(2)).to_have_value("unused")
    expect(editor.locator("[data-weekly-range] [data-range-start]")).to_have_value("8")
    expect(editor.locator("[data-weekly-range] [data-range-end]")).to_have_value("18")
    expect(editor.locator("[data-weekly-range] [data-range-value]")).to_have_value("5")
    side_panel.close()

    download_path = tmp_path / "weekly-pattern.e-f.json"
    model_builder.download_active_model(str(download_path))
    downloaded = json.loads(download_path.read_text())
    process_data = next(iter(downloaded["RecurrentEdgeProcess"].values()))
    profiles = process_data["recurrent_compute_needed"]["form_inputs"]["profiles"]
    assert [profile["name"] for profile in profiles] == ["weekday", "weekend", "unused"]

    model_builder.reset_to_default()
    model_builder.import_json_file(str(download_path))
    open_process_editor(model_builder)
    expect(page.locator(f"#{field_id}__builder_selector")).to_have_value("weekly_pattern")
    expect(page.locator(f"#{field_id}__builder [data-profile-name]").nth(2)).to_have_value("unused")
