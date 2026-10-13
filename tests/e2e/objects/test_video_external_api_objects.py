"""E2E flow for the EcoLogits video-generation external API.

Adds an EcoLogitsVideoGenExternalAPI through the model-builder UI — driving the
provider -> model cascade (changing the provider narrows the model select to that
provider's valid models), the boolean with_audio toggle, and the datacenter advanced
parameters — then, with a second API on a different model, drives the Job form's
cross-object resolution cascade (the resolution select offers exactly the selected
API's valid resolutions and repopulates on API change), attaches a job, a usage pattern,
asserts the result chart renders, checks the per-call explainability tree, and finally
deletes the job without error.
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx


@pytest.mark.e2e
class TestVideoExternalAPIObjects:
    """Tests for EcoLogitsVideoGenExternalAPI creation, job linkage, and results."""

    def test_ecologits_video_full_workflow(self, seeded_journey_model_builder: ModelBuilderPage):
        model_builder = seeded_journey_model_builder
        side_panel = model_builder.side_panel
        page = model_builder.page

        api_name = "Test Video API"
        second_api_name = "Second Video API"
        job_name = "Test Video Job"
        usage_pattern_name = "Test Usage Pattern"
        uj_name = "My first usage journey"
        uj_step_name = "My first usage journey step"

        # Step 1: Create EcoLogitsVideoGenExternalAPI (defaults to provider=openai, model=sora-2-pro).
        model_builder.click_add_external_api()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_object_type("EcoLogitsVideoGenExternalAPI")
        side_panel.fill_field("EcoLogitsVideoGenExternalAPI_name", api_name)

        # Provider and model_name render as selects, with the model default restored after dynamic hydration.
        expect(page.locator("#EcoLogitsVideoGenExternalAPI_provider")).to_be_visible()
        expect(page.locator("#EcoLogitsVideoGenExternalAPI_model_name")).to_have_value("sora-2-pro")

        # Drive the provider -> model cascade: switching provider repopulates the model select
        # with only that provider's valid models and clears the now-invalid model selection.
        # Assert the cascade behaviour (the select gets a different, non-empty set), not the exact
        # model names — those come from the upstream EcoLogits catalog and are pinned in unit tests instead.
        model_options = page.locator("#EcoLogitsVideoGenExternalAPI_model_name option")
        # The cascade is wired by HX-Trigger-After-Settle; wait until it has replaced the server-rendered
        # placeholder before reading the options or changing the provider.
        expect(model_options.first).to_have_attribute("value", "sora-2-pro")
        openai_models = set(model_options.evaluate_all("els => els.map(e => e.value)"))
        side_panel.select_option("EcoLogitsVideoGenExternalAPI_provider", "google")
        # The change handler repopulates the select then clears the stale selection synchronously, so an
        # empty model_name is a reliable signal that the select has already been refreshed.
        expect(page.locator("#EcoLogitsVideoGenExternalAPI_model_name")).to_have_value("")
        google_models = set(model_options.evaluate_all("els => els.map(e => e.value)"))
        assert google_models and google_models != openai_models

        # Restore openai/sora-2-pro for the rest of the flow; switching back narrows to openai's set again.
        side_panel.select_option("EcoLogitsVideoGenExternalAPI_provider", "openai")
        expect(page.locator("#EcoLogitsVideoGenExternalAPI_model_name")).to_have_value("")
        assert set(model_options.evaluate_all("els => els.map(e => e.value)")) == openai_models
        side_panel.select_option("EcoLogitsVideoGenExternalAPI_model_name", "sora-2-pro")

        # Datacenter location, PUE and WUE are now inferred from the EcoLogits provider config,
        # so the form exposes no advanced parameters for this object type.
        expect(page.locator("#display-advanced-EcoLogitsVideoGenExternalAPI")).not_to_be_visible()

        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EcoLogitsVideoGenExternalAPI", api_name)

        # Step 2: Create a second video API on a different model (bytedance/seedance-1.0, whose valid
        # resolutions differ from sora-2-pro's) so the Job form's resolution cascade can be exercised.
        model_builder.click_add_external_api()
        page.locator("#sidePanelForm").wait_for(state="visible")
        side_panel.select_object_type("EcoLogitsVideoGenExternalAPI")
        side_panel.fill_field("EcoLogitsVideoGenExternalAPI_name", second_api_name)
        side_panel.select_option("EcoLogitsVideoGenExternalAPI_provider", "bytedance")
        side_panel.select_option("EcoLogitsVideoGenExternalAPI_model_name", "seedance-1.0")
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EcoLogitsVideoGenExternalAPI", second_api_name)

        # Step 3: Create a job; the resolution select must offer exactly the chosen API's valid
        # resolutions and repopulate when a different API is selected.
        uj_step_card = model_builder.get_object_card("UsageJourneyStep", uj_step_name)
        uj_step_card.click_add_job_button()
        page.locator("#server_or_external_api").wait_for(state="attached")
        resolution_options = page.locator("#EcoLogitsVideoGenExternalAPIJob_resolution option")

        # Selecting the sora API offers its two resolutions (720p, 1080p) — never the generic placeholder.
        side_panel.select_option("server_or_external_api", api_name)
        page.locator("#EcoLogitsVideoGenExternalAPIJob_name").wait_for(state="attached")
        expect(resolution_options).to_have_count(2)
        assert set(resolution_options.evaluate_all("els => els.map(e => e.value)")) == {
            "720p (1280 x 720)", "1080p (1920 x 1080)"}

        # Switching to the seedance API (different model) repopulates the select: 1080p drops, 480p appears.
        side_panel.select_option("server_or_external_api", second_api_name)
        expect(resolution_options).to_have_count(2)
        assert set(resolution_options.evaluate_all("els => els.map(e => e.value)")) == {
            "480p (854 x 480)", "720p (1280 x 720)"}

        # Settle on the sora API for the rest of the flow.
        side_panel.select_option("server_or_external_api", api_name)
        expect(resolution_options).to_have_count(2)
        side_panel.fill_field("EcoLogitsVideoGenExternalAPIJob_name", job_name)

        # with_audio renders as a boolean toggle (checkbox), not a text input.
        audio_checkbox = page.locator("#EcoLogitsVideoGenExternalAPIJob_with_audio_checkbox")
        expect(audio_checkbox).to_be_checked()
        audio_checkbox.uncheck()
        expect(page.locator("#EcoLogitsVideoGenExternalAPIJob_with_audio")).to_have_value("false")

        # Selecting an API clears the resolution (cascade); pick a valid one for the chosen API.
        side_panel.select_option("EcoLogitsVideoGenExternalAPIJob_resolution", "1080p (1920 x 1080)")

        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("EcoLogitsVideoGenExternalAPIJob", job_name)

        # Step 4: Create a usage pattern so the system has demand.
        model_builder.click_add_usage_pattern()
        side_panel.fill_field("UsagePattern_name", usage_pattern_name)
        page.locator("#UsagePattern_hourly_occurrences__initial_volume").fill("1000")
        # The only available journey is selected by default.
        side_panel.submit_and_wait_for_close()
        model_builder.object_should_exist("UsagePattern", usage_pattern_name)

        # Step 5: Results compute and the chart renders with data.
        model_builder.open_result_panel()
        model_builder.result_chart_should_be_visible()
        model_builder.close_result_panel()

        # Step 6: per-call quantities carry the EcoLogits explainability tree (spec criterion #2):
        # the generation_latency formula and its input variables render in the calculated-attributes drawer.
        uj_step_card = model_builder.get_object_card("UsageJourneyStep", uj_step_name)
        uj_step_card.open_accordion()
        job_card = model_builder.get_object_card("EcoLogitsVideoGenExternalAPIJob", job_name)
        job_card.click_edit_button()

        calc_attrs_btn = page.locator(
            "[data-bs-target='#collapseCalculatedAttributesEcoLogitsVideoGenExternalAPIJob']")
        calc_attrs_btn.click()
        page.locator("#collapseCalculatedAttributesEcoLogitsVideoGenExternalAPIJob").wait_for(state="visible")

        formula_btn = page.locator("[data-bs-target='#collapse-calculated_attributes-generation_latency']")
        click_and_wait_for_htmx(page, formula_btn)
        explanation = page.locator("#collapse-calculated_attributes-generation_latency")
        expect(explanation.locator(".explainable-formula pre")).not_to_be_empty()
        expect(explanation.locator(".explainable-ancestors li").first).to_be_visible()

        # Step 7: deleting the job (still open in the side panel) raises no error.
        side_panel.click_delete_button()
        side_panel.confirm_delete()
        model_builder.object_should_not_exist("EcoLogitsVideoGenExternalAPIJob", job_name)
        expect(page.locator("#model-builder-modal")).not_to_be_visible()

    def test_normal_api_save_refreshes_shared_jobs_and_reopens_accepted_sources(
        self, minimal_system, model_builder_page: ModelBuilderPage
    ):
        from efootprint.abstract_modeling_classes.source_objects import SourceObject
        from efootprint.abstract_modeling_classes.explainable_object_dict import to_weighted_explainable_object_dict
        from efootprint.api_utils.system_to_json import system_to_json
        from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
            EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)
        from efootprint.core.usage.usage_journey_step import UsageJourneyStep
        from tests.e2e.conftest import load_system_dict_into_browser

        api = EcoLogitsVideoGenExternalAPI.from_defaults("Shared video API")
        jobs = [EcoLogitsVideoGenExternalAPIJob.from_defaults(name, external_api=api,
            resolution=SourceObject(resolution, confidence="high", comment="Prior comment"))
            for name, resolution in [("Retained video job", "720p (1280 x 720)"),
                                     ("Repaired video job A", "1080p (1920 x 1080)"),
                                     ("Repaired video job B", "1080p (1920 x 1080)")]]
        journey = next(iter(minimal_system.usage_patterns[0].usage_journeys))
        step = next(iter(journey.uj_steps))
        step.jobs = to_weighted_explainable_object_dict(jobs)
        mirror_step = UsageJourneyStep.from_defaults("Mirror step", jobs=jobs)
        journey.uj_steps = to_weighted_explainable_object_dict([step, mirror_step])
        model_builder = load_system_dict_into_browser(
            model_builder_page, system_to_json(minimal_system, save_computed_state=False))
        page = model_builder.page
        side_panel = model_builder.side_panel
        model_builder.get_object_card("UsageJourneyStep", step.name).open_accordion()
        model_builder.get_object_card("UsageJourneyStep", mirror_step.name).open_accordion()
        job_buttons = page.locator(f"button[hx-get*='/model_builder/open-edit-object-panel/{jobs[1].id}']")
        expect(job_buttons).to_have_count(2)
        job_buttons.evaluate_all("els => els.forEach(el => el.dataset.beforeRepair = 'true')")

        model_builder.get_object_card("EcoLogitsVideoGenExternalAPI", api.name).click_edit_button()
        side_panel.select_option("EcoLogitsVideoGenExternalAPI_provider", "bytedance")
        side_panel.select_option("EcoLogitsVideoGenExternalAPI_model_name", "seedance-1.0")
        side_panel.submit_and_wait_for_close()
        toast = page.locator("#toast-content")
        for job in jobs[1:]:
            expect(toast).to_contain_text(f"{job.name}: {job.resolution.label} changed to 480p (854 x 480).")
        expect(toast).not_to_contain_text("Retained video job:")
        expect(page.locator("button[data-before-repair='true']")).to_have_count(0)
        expect(job_buttons).to_have_count(2)
        expect(page.locator("#model-builder-modal")).not_to_be_visible()

        for index, job in enumerate(jobs):
            button = page.locator(f"button[hx-get*='/model_builder/open-edit-object-panel/{job.id}']").first
            click_and_wait_for_htmx(page, button)
            expect(page.locator("#EcoLogitsVideoGenExternalAPIJob_resolution")).to_have_value(
                "720p (1280 x 720)" if index == 0 else "480p (854 x 480)")
            assert page.locator("#EcoLogitsVideoGenExternalAPIJob_resolution option").evaluate_all(
                "els => els.map(el => el.value)") == ["480p (854 x 480)", "720p (1280 x 720)"]
            source = page.locator("#source-EcoLogitsVideoGenExternalAPIJob_resolution")
            source.locator(".source-line .bi-pencil-fill").click()
            picker = source.locator(".source-editor-select")
            if index == 0:
                expect(picker.locator("option[value='automatic_replacement']")).to_have_count(0)
            else:
                expect(picker).to_have_value("automatic_replacement")
                expect(source.locator(".source-editor-comment")).to_contain_text("Prior comment")
            side_panel.close()
