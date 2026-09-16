"""Sequential browser benchmark for the article's four representative usage journeys."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from .recorder import BenchmarkRecorder
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.pages.components.object_card import ObjectCard
from tests.e2e.pages.model_builder_page import card_id_selector
from tests.e2e.pages.sankey_page import SankeyPage
from tests.e2e.utils import click_and_wait_for_htmx


@pytest.mark.e2e
@pytest.mark.benchmark
def test_sequential_usage_journeys(model_builder_page: ModelBuilderPage, pytestconfig, tmp_path):
    """Explore → enrich → compare → export/import and audit one maintained example."""
    if not pytestconfig.getoption("--run-usage-benchmark"):
        pytest.skip("Pass --run-usage-benchmark to run the stateful browser benchmark")

    model_builder = model_builder_page
    page = model_builder.page
    output_dir = Path(pytestconfig.getoption("--usage-benchmark-output")).expanduser().resolve()
    recorder = BenchmarkRecorder(page.context, pytestconfig.getoption("base_url"))
    first_export = tmp_path / f"{recorder.run_id}-built-model.e-f.json"
    reused_export = tmp_path / f"{recorder.run_id}-reused-model.e-f.json"

    try:
        _explore_example(model_builder, recorder)
        _build_from_example(model_builder, recorder)
        _compare_alternative(model_builder, recorder, tmp_path)
        _audit_and_reuse(model_builder, recorder, first_export, reused_export, tmp_path)
    finally:
        run_dir = recorder.write(output_dir)
        print(f"Usage benchmark data: {run_dir}")


def _explore_example(model_builder: ModelBuilderPage, recorder: BenchmarkRecorder) -> None:
    page = model_builder.page
    page.goto("/")
    page.locator("#btn-start-modeling-my-service").click()
    model_builder.canvas.wait_for(state="visible")
    model_builder.template_picker.wait_for(state="visible")

    with recorder.measure("S1", "B2", "load_ecommerce_template"):
        model_builder.pick_template("ecommerce")
    model_builder.object_should_exist("UsageJourney", "Shopping journey")

    with recorder.measure("S1", "B5", "open_results_and_generate_cold_sankey"):
        model_builder.open_result_panel()
        card = SankeyPage(model_builder).first_card()
        card.wait_for_diagram_update()

    with recorder.measure("S1", "B7", "refine_warm_sankey"):
        card.set_lifecycle_filter("Manufacturing")
        card.wait_for_diagram_update()

    model_builder.close_result_panel()


def _build_from_example(model_builder: ModelBuilderPage, recorder: BenchmarkRecorder) -> None:
    page = model_builder.page
    side_panel = model_builder.side_panel
    step_name = f"Benchmark support request {recorder.run_id[-8:]}"
    job_name = f"Benchmark support job {recorder.run_id[-8:]}"

    journey = model_builder.get_object_card("UsageJourney", "Shopping journey")
    journey.click_add_step_button()
    side_panel.fill_field("UsageJourneyStep_name", step_name)
    side_panel.fill_field("UsageJourneyStep_user_time_spent", "45")
    with recorder.measure("S2", "B3", "add_usage_journey_step"):
        side_panel.submit_and_wait_for_close()
    model_builder.object_should_exist("UsageJourneyStep", step_name)

    step = model_builder.get_object_card("UsageJourneyStep", step_name)
    step.click_add_job_button()
    page.locator("#service_or_external_api").wait_for(state="attached")
    side_panel.select_option("service_or_external_api", "direct_server_call")
    side_panel.fill_field("Job_name", job_name)
    with recorder.measure("S2", "B3", "add_direct_server_job"):
        side_panel.submit_and_wait_for_close()
    model_builder.object_should_exist("Job", job_name)

    usage_pattern = _active_card(model_builder, "UsagePattern", "Daily shoppers")
    usage_pattern.click_edit_button()
    initial_volume = page.locator("#UsagePattern_hourly_occurrences__initial_volume")
    initial_volume.fill("1500")
    initial_volume.dispatch_event("change")
    with recorder.measure("S2", "B3", "increase_usage_volume"):
        side_panel.submit_and_wait_for_close()

    server = model_builder.get_object_card("BoaviztaCloudServer", "Web application server")
    server.click_edit_button()
    page.locator("#display-advanced-BoaviztaCloudServer").click()
    side_panel.fill_field("BoaviztaCloudServer_base_ram_consumption", "6")
    with recorder.measure("S2", "B3", "increase_server_ram"):
        side_panel.submit_and_wait_for_close()

    server = model_builder.get_object_card("BoaviztaCloudServer", "Web application server")
    server.click_edit_button()
    page.locator("#display-advanced-BoaviztaCloudServer").click()
    side_panel.fill_field("BoaviztaCloudServer_base_compute_consumption", "0.3")

    with recorder.measure("S2", "B5", "open_results_for_richer_model"):
        model_builder.open_result_panel()
        SankeyPage(model_builder).first_card().wait_for_diagram_update()

    with recorder.measure("S2", "B4", "update_model_with_results_open"):
        side_panel.submit_and_wait_for_close()
    SankeyPage(model_builder).first_card().wait_for_diagram_update()
    model_builder.close_result_panel()


def _compare_alternative(model_builder: ModelBuilderPage, recorder: BenchmarkRecorder, tmp_path: Path) -> None:
    page = model_builder.page
    side_panel = model_builder.side_panel

    with recorder.measure("S3", "B2", "duplicate_built_model"):
        model_builder.add_model_by_duplication()
    expect(page.locator("#compare-tab")).to_be_enabled()

    click_and_wait_for_htmx(page, page.locator("#btn-change-system-name"))
    page.locator("#sidePanel #name").fill(f"Lower-volume alternative {recorder.run_id[-8:]}")
    with recorder.measure("S3", "B3", "rename_alternative"):
        side_panel.submit_and_wait_for_close()

    usage_pattern = _active_card(model_builder, "UsagePattern", "Daily shoppers")
    usage_pattern.click_edit_button()
    initial_volume = page.locator("#UsagePattern_hourly_occurrences__initial_volume")
    initial_volume.fill("900")
    initial_volume.dispatch_event("change")
    with recorder.measure("S3", "B3", "reduce_alternative_usage_volume"):
        side_panel.submit_and_wait_for_close()

    count_input = page.locator("[data-model-canvas='1'] input.count-inline-edit").first
    count_input.wait_for(state="visible")
    with recorder.measure("S3", "B3", "increase_alternative_step_count"):
        with page.expect_response(lambda response: "update-dict-count" in response.url):
            count_input.fill("2")
            count_input.press("Tab")

    with recorder.measure("S3", "B8", "compare_reference_and_alternative"):
        model_builder.open_compare()
        expect(page.locator("#comparison-dashboard")).to_contain_text("CO2-eq")

    workspace_export = tmp_path / f"{recorder.run_id}-workspace.e-f.json"
    model_builder.dismiss_compare_to_active_model(1)
    page.locator("#download-menu-toggle").click()
    with recorder.measure("S3", "B10", "export_comparison_workspace"):
        with page.expect_download() as download_info:
            page.locator('a[href="download-workspace/"]').click()
        download_info.value.save_as(workspace_export)
    assert workspace_export.stat().st_size > 0


def _audit_and_reuse(
    model_builder: ModelBuilderPage,
    recorder: BenchmarkRecorder,
    first_export: Path,
    reused_export: Path,
    tmp_path: Path,
) -> None:
    page = model_builder.page

    with recorder.measure("S4", "B10", "export_model_for_reuse"):
        model_builder.download_active_model(str(first_export))
    assert first_export.stat().st_size > 0

    with recorder.measure("S4", "setup", "reset_active_model_before_reuse"):
        model_builder.reset_to_default()
    with recorder.measure("S4", "B2", "import_previously_built_model"):
        model_builder.import_json_file(str(first_export))
    expect(model_builder.active_model_name()).to_contain_text("Lower-volume alternative")

    journey = _active_card(model_builder, "UsageJourney", "Shopping journey")
    journey.click_edit_button()
    calc_toggle = page.locator("button[data-bs-target='#collapseCalculatedAttributesUsageJourney']")
    calc_toggle.click()
    duration_button = page.locator("button[hx-get*='duration/']").first
    with recorder.measure("S4", "B9", "open_calculated_value_explanation"):
        click_and_wait_for_htmx(page, duration_button)
        page.locator("div.explainable-ancestors").first.wait_for(state="visible")

    graph_link = page.locator("a[href*='/model_builder/display-calculus-graph/']").first
    with recorder.measure("S4", "B9", "open_calculus_graph"):
        with page.context.expect_page() as graph_page_info:
            graph_link.click()
        graph_page = graph_page_info.value
        graph_page.locator("iframe").wait_for(state="attached")
        frame = graph_page.locator("iframe").content_frame
        frame.locator("#mynetwork").wait_for(state="attached")
        graph_page.close()
    model_builder.close_side_panel()

    with recorder.measure("S4", "B5", "open_reused_model_results"):
        model_builder.open_result_panel()
        SankeyPage(model_builder).first_card().wait_for_diagram_update()
    page.locator(".header-btn-result-sources-desktop").click()

    sources_export = tmp_path / f"{recorder.run_id}-sources.xlsx"
    with recorder.measure("S4", "B10", "export_sources"):
        with page.expect_download() as download_info:
            page.locator("#download-sources").click()
        download_info.value.save_as(sources_export)
    assert sources_export.stat().st_size > 0
    model_builder.close_result_panel()

    with recorder.measure("S4", "B10", "export_reused_model"):
        model_builder.download_active_model(str(reused_export))
    assert reused_export.stat().st_size > 0


def _active_card(model_builder: ModelBuilderPage, object_type: str, name: str) -> ObjectCard:
    """Resolve a card inside the visible resident canvas when two models contain the same object ids."""
    locator = model_builder.canvas.locator(card_id_selector(object_type)).filter(has_text=name)
    return ObjectCard(locator)
