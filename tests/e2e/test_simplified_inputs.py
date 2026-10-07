"""Critical configuration, navigation and resident-model flows for focused inputs."""
import json

import pytest
from playwright.sync_api import expect

from tests.e2e.utils import click_and_wait_for_htmx


def open_simplified(page):
    click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
    expect(page.locator('[data-simplified-workspace]:visible')).to_have_attribute("data-mode", "simplified")


def open_configure(page):
    open_simplified(page)
    click_and_wait_for_htmx(page, page.locator('[data-action="simplified-configure"]:visible').first)
    expect(page.locator('[data-simplified-workspace]:visible')).to_have_attribute("data-mode", "configure")
    return page.locator('[data-simplified-workspace]:visible')


def field(workspace, attribute):
    return workspace.locator(f'[data-field-address][data-attribute="{attribute}"]').first


def reject_simplified_edit(route):
    from urllib.parse import parse_qsl, urlencode

    data = dict(parse_qsl(route.request.post_data))
    prefix = next(key for key in data if key not in {"csrfmiddlewaretoken", "timeseries", "recomputation"})
    prefix = prefix.split("__", 1)[0]
    data[prefix] = "invalid"
    data[prefix + "__unit"] = "dimensionless"
    route.fulfill(response=route.fetch(post_data=urlencode(data)))


@pytest.mark.e2e
class TestSimplifiedInputs:
    def test_optional_count_switch_in_modeling_and_simplified_inputs(self, minimal_complete_model_builder):
        builder = minimal_complete_model_builder
        page = builder.page
        edit = page.locator("#server-list button[hx-get*='open-edit-object-panel']").first
        server_id = edit.get_attribute("hx-get").rstrip("/").split("/")[-1]
        click_and_wait_for_htmx(page, edit)
        toggle = page.locator("#sidePanel #Server_fixed_nb_of_instances__empty")
        number = page.locator("#sidePanel #Server_fixed_nb_of_instances")
        expect(page.locator("#sidePanel").get_by_text("Leave unset", exact=True).first).to_be_visible()
        expect(toggle).to_be_checked()
        expect(toggle).to_be_disabled()
        page.locator("#sidePanel #Server_server_type").select_option("on-premise")
        expect(toggle).to_be_enabled()
        toggle.uncheck()
        expect(number).to_be_visible()
        expect(number).to_have_attribute("required", "")
        number.fill("1000")
        builder.side_panel.submit_and_wait_for_close()

        workspace = open_configure(page)
        workspace.locator(f'[data-navigation-object$="object-{server_id}"]').click()
        count = workspace.locator(f'[data-owner-id="{server_id}"][data-attribute="fixed_nb_of_instances"]')
        count.locator("[data-include-input]").check()
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
        count = workspace.locator(f'[data-owner-id="{server_id}"][data-attribute="fixed_nb_of_instances"]')
        toggle = count.locator('[data-action="optional-quantity-empty"]')
        expect(toggle).not_to_be_checked()
        with page.expect_response("**/edit-simplified-input/**"):
            toggle.check()
        expect(count.locator("[data-simplified-save-status]")).to_have_text("Saved")
        expect(count.locator('input[type="number"]')).to_have_value("")
        toggle.uncheck()
        number = count.locator('input[type="number"]')
        number.fill("2000")
        with page.expect_response("**/edit-simplified-input/**"):
            number.press("Enter")
        expect(count.locator("[data-simplified-save-status]")).to_have_text("Saved")
        click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
        click_and_wait_for_htmx(page, edit)
        expect(page.locator("#sidePanel #Server_fixed_nb_of_instances__empty")).not_to_be_checked()
        expect(page.locator("#sidePanel #Server_fixed_nb_of_instances")).to_have_value("2000")
        page.locator("#sidePanel #Server_fixed_nb_of_instances__empty").check()
        page.locator('[data-action="simplified-mode"]').click()
        expect(page.locator("#unsavedModal")).to_be_visible()
        page.locator("#cancel-unsaved-modal").click()
        expect(page.locator("#sidePanel #Server_fixed_nb_of_instances__empty")).to_be_checked()
        builder.side_panel.submit_and_wait_for_close()
        click_and_wait_for_htmx(page, edit)
        expect(page.locator("#sidePanel #Server_fixed_nb_of_instances__empty")).to_be_checked()
        expect(page.locator("#sidePanel #Server_fixed_nb_of_instances")).to_have_value("")

    def test_provider_save_keeps_accepted_model_and_job_choices_editable(self, minimal_system, model_builder_page):
        from efootprint.api_utils.system_to_json import system_to_json
        from efootprint.abstract_modeling_classes.source_objects import SourceObject
        from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
            EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob,
        )
        from tests.e2e.conftest import load_system_dict_into_browser
        from tests.e2e.utils import add_only_update

        api = EcoLogitsVideoGenExternalAPI.from_defaults("Video API")
        job = EcoLogitsVideoGenExternalAPIJob.from_defaults("Video job", external_api=api)
        data = system_to_json(minimal_system, save_computed_state=False)
        add_only_update(data, system_to_json(job, save_computed_state=False))
        page = load_system_dict_into_browser(model_builder_page, data).page
        workspace = open_configure(page)
        workspace.get_by_role("button", name="Expand all", exact=True).click()
        field(workspace, "provider").locator("[data-include-input]").check()
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return", exact=True))
        workspace.get_by_role("button", name="Expand all", exact=True).click()
        model_select = field(workspace, "model_name").locator("select[name]")
        resolution_select = field(workspace, "resolution").locator("select[name]")
        expect(model_select).to_have_value(api.model_name.value)
        expect(resolution_select).to_have_value(job.resolution.value)
        models = api.conditional_list_values["model_name"]["conditional_list_values"][SourceObject("bytedance")]
        resolutions = job.conditional_list_values["resolution"]["conditional_list_values"][models[0]]
        with page.expect_response("**/edit-simplified-input/**"):
            field(workspace, "provider").locator("select[name]").select_option("bytedance")
        expect(model_select).to_have_value(models[0].value)
        expect(model_select.locator("option")).to_have_text([str(model) for model in models])
        expect(resolution_select.locator("option")).to_have_text([str(value) for value in resolutions])
        expect(resolution_select).to_have_value(job.resolution.value)
        page.wait_for_function("() => document.querySelector('.htmx-request, .htmx-settling, .htmx-added') === null")
        with page.expect_response("**/edit-simplified-input/**"):
            resolution_select.select_option(resolutions[0].value)
        expect(resolution_select).to_have_value(resolutions[0].value)

    def test_repeated_configure_entry_does_not_queue_a_draft_replacement(self, minimal_complete_model_builder):
        page = minimal_complete_model_builder.page
        open_simplified(page)
        pending = []
        page.route("**/simplified-inputs/?configure=1", lambda route: pending.append(route))
        with page.expect_request("**/simplified-inputs/?configure=1"):
            page.get_by_role("button", name="Configure", exact=True).dblclick()
        assert len(pending) == 1
        route = pending.pop()
        route.fulfill(response=route.fetch())
        workspace = page.locator('[data-simplified-workspace]:visible')
        expect(workspace).to_have_attribute("data-mode", "configure")
        workspace.locator('[name="title"]').fill("Preserve this draft")
        expect(workspace.locator("form")).to_have_attribute("data-dirty", "true")
        assert pending == []
        page.unroute("**/simplified-inputs/?configure=1")
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
        expect(workspace.get_by_text("Preserve this draft", exact=True)).to_be_visible()

    @pytest.mark.parametrize("return_before_response", [False, True])
    def test_abandoned_configure_read_cannot_follow_a_model_switch(
            self, minimal_complete_model_builder, return_before_response):
        builder = minimal_complete_model_builder
        page = builder.page
        builder.add_model_by_duplication()
        open_simplified(page)
        system_id = page.locator('[data-simplified-target="1"]').get_attribute("data-system-id")
        pending = []
        page.route("**/simplified-inputs/?configure=1", lambda route: pending.append(route))
        with page.expect_request("**/simplified-inputs/?configure=1"):
            page.get_by_role("button", name="Configure", exact=True).click()
        assert len(pending) == 1
        route = pending.pop()
        response = route.fetch()
        builder.switch_to_model(0)
        if return_before_response:
            builder.switch_to_model(1)
        route.fulfill(response=response)
        expect(page.locator("[data-configure-form]")).to_have_count(0)
        if not return_before_response:
            builder.switch_to_model(1)
        expect(page.locator('[data-simplified-workspace]:visible')).to_have_attribute("data-mode", "simplified")
        page.unroute("**/simplified-inputs/?configure=1")
        click_and_wait_for_htmx(page, page.get_by_role("button", name="Configure", exact=True))
        expect(page.locator('[data-simplified-workspace]:visible')).to_have_attribute("data-slot", "1")
        expect(page.locator('[data-simplified-workspace]:visible')).to_have_attribute("data-system-id", system_id)

    def test_save_clear_cancel_and_fresh_configuration(self, minimal_complete_model_builder):
        page = minimal_complete_model_builder.page
        workspace = open_configure(page)
        lifespan = field(workspace, "lifespan")
        lifespan.locator("[data-include-input]").check()
        lifespan.locator("textarea").fill("Keep My Capitals")
        workspace.locator('[name="title"]').fill("Adapt This Modeling")
        workspace.locator('[name="guidance"]').fill("General Guidance")
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
        expect(workspace).to_have_attribute("data-mode", "simplified")
        expect(workspace.get_by_text("Keep My Capitals", exact=True)).to_be_visible()
        expect(workspace.locator("[data-field-address]")).to_have_count(1)
        expect(page.locator("#edge-modeling-toggle-wrapper")).not_to_be_visible()
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Configure", exact=True))
        expect(workspace).to_have_attribute("data-mode", "configure")
        workspace.locator("[data-selected-object-filter]").check()
        page.once("dialog", lambda dialog: dialog.accept())
        workspace.get_by_role("button", name="Clear all", exact=True).click()
        expect(workspace.locator("[data-filter-empty]")).to_be_visible()
        expect(workspace.locator('[name="title"]')).to_have_value("Adapt This Modeling")
        expect(workspace.locator('[name="guidance"]')).to_have_value("General Guidance")
        workspace.get_by_role("button", name="Cancel", exact=True).click()
        expect(page.locator("#simplified-exit-dialog")).to_be_visible()
        page.get_by_role("button", name="Stay", exact=True).click()
        expect(workspace).to_have_attribute("data-mode", "configure")
        workspace.get_by_role("button", name="Cancel", exact=True).click()
        click_and_wait_for_htmx(page, page.get_by_role("button", name="Discard", exact=True))
        expect(workspace).to_have_attribute("data-mode", "simplified")
        expect(workspace.get_by_text("Keep My Capitals", exact=True)).to_be_visible()
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Configure", exact=True))
        expect(workspace.locator("[data-selected-object-filter]")).not_to_be_checked()
        expect(workspace.locator("[data-simplified-object]").first).to_have_attribute("open", "")
        expect(field(workspace, "lifespan").locator("textarea")).to_have_value("Keep My Capitals")

    def test_configure_save_failure_retains_the_draft_and_exit_guard(self, minimal_complete_model_builder):
        from urllib.parse import parse_qsl, urlencode

        page = minimal_complete_model_builder.page
        workspace = open_configure(page)
        field(workspace, "lifespan").locator("[data-include-input]").check()

        def reject_definition(route):
            data = dict(parse_qsl(route.request.post_data))
            data["definition"] = json.dumps({"fields": {"missing-owner": {"lifespan": {"included": True}}}})
            route.fulfill(response=route.fetch(post_data=urlencode(data)))

        page.route("**/save-simplified-inputs/", reject_definition)
        click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
        with page.expect_response("**/save-simplified-inputs/") as response_info:
            page.get_by_role("button", name="Save", exact=True).click()
        assert response_info.value.status == 422
        expect(page.locator("#model-builder-modal")).to_be_visible()
        expect(page.locator("body")).not_to_have_attribute("data-workspace-mutation", "updating")
        expect(workspace).to_have_attribute("data-mode", "configure")
        expect(workspace.locator("[data-configure-form]")).to_have_attribute("data-dirty", "true")
        expect(field(workspace, "lifespan").locator("[data-include-input]")).to_be_checked()
        page.get_by_role("button", name="Go back", exact=True).click()
        downloads = []
        page.on("download", lambda download: downloads.append(download))
        page.locator("a[href='download-json/']").click()
        expect(page.locator("#simplified-exit-dialog")).to_be_visible()
        page.get_by_role("button", name="Stay", exact=True).click()
        assert downloads == []
        page.unroute("**/save-simplified-inputs/")
        page.locator('[data-action="simplified-mode"]').click()
        click_and_wait_for_htmx(page, page.get_by_role("button", name="Save", exact=True))
        expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
        expect(page.locator("[data-simplified-target]:visible")).to_have_count(0)

    def test_filter_focus_and_required_companions(self, minimal_complete_model_builder):
        page = minimal_complete_model_builder.page
        workspace = open_configure(page)
        workspace.get_by_role("button", name="Expand all").click()
        kind = field(workspace, "server_type")
        kind.locator("[data-include-input]").check()
        count = kind.locator("xpath=..").locator('[data-attribute="fixed_nb_of_instances"] [data-include-input]')
        expect(count).to_be_checked()
        expect(count).to_be_disabled()
        workspace.locator("[data-selected-object-filter]").check()
        expect(workspace.locator("[data-simplified-object]:visible")).to_have_count(1)
        kind.locator("[data-include-input]").uncheck()
        expect(count).to_be_enabled()
        count.uncheck()
        expect(workspace.locator("[data-filter-empty]")).to_be_visible()
        expect(workspace.locator("[data-selected-object-filter]")).to_be_focused()
        workspace.get_by_role("button", name="Show all objects").click()
        expect(workspace.locator("[data-simplified-object]:visible").first).to_be_visible()
        workspace.get_by_role("button", name="Collapse all").click()
        nav = workspace.locator("[data-navigation-object]").last
        nav.click()
        owner_id = nav.get_attribute("data-navigation-object")
        expect(page.locator(f"#{owner_id}")).to_have_attribute("open", "")

    def test_model_base_views_survive_switch_and_compare(self, minimal_complete_model_builder):
        builder = minimal_complete_model_builder
        page = builder.page
        builder.add_model_by_duplication()
        workspace = open_configure(page)
        field(workspace, "lifespan").locator("[data-include-input]").check()
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
        builder.switch_to_model(0)
        expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
        builder.switch_to_model(1)
        expect(page.locator("body")).to_have_attribute("data-base-view", "simplified")
        click_and_wait_for_htmx(page, page.locator("#compare-tab"))
        expect(page.locator("#comparison-view")).to_be_visible()
        builder.dismiss_compare_to_active_model(1)
        expect(page.locator("[data-simplified-workspace]:visible")).to_have_attribute("data-mode", "simplified")

    def test_json_selected_opening_and_fresh_render_after_modeling_edit(self, minimal_complete_model_builder, tmp_path):
        builder = minimal_complete_model_builder
        page = builder.page
        edit = page.locator("#server-list button[hx-get*='open-edit-object-panel']").first
        server_id = edit.get_attribute("hx-get").rstrip("/").split("/")[-1]
        workspace = open_configure(page)
        workspace.locator(f'[data-navigation-object$="object-{server_id}"]').click()
        lifespan = workspace.locator(f'[data-owner-id="{server_id}"][data-attribute="lifespan"]')
        lifespan.locator("[data-include-input]").check()
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
        filename = str(tmp_path / "selected.e-f.json")
        builder.download_active_model(filename)
        click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
        expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
        builder.import_json_file(filename)
        expect(page.locator("body")).to_have_attribute("data-base-view", "simplified")
        click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
        click_and_wait_for_htmx(page, page.locator("#server-list button[hx-get*='open-edit-object-panel']").first)
        page.locator('#sidePanel #Server_lifespan').fill("7")
        builder.side_panel.submit_and_wait_for_close()
        click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
        expect(workspace.locator('input[type="number"]')).to_have_value("7")

    def test_mode_change_uses_existing_unsaved_panel_warning(self, minimal_complete_model_builder):
        builder = minimal_complete_model_builder
        page = builder.page
        click_and_wait_for_htmx(page, page.locator("#server-list button[hx-get*='open-edit-object-panel']").first)
        page.locator('#sidePanel #Server_lifespan').fill("7")
        click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
        expect(page.locator("#unsavedModal")).to_be_visible()
        expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
        page.locator("#cancel-unsaved-modal").click()
        expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
        builder.side_panel.submit_and_wait_for_close()
        expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
        click_and_wait_for_htmx(page, page.locator("#server-list button[hx-get*='open-edit-object-panel']").first)
        page.locator('#sidePanel #Server_lifespan').fill("8")
        click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
        page.locator("#continue-unsaved-modal").click()
        expect(page.locator("[data-simplified-workspace]:visible")).to_have_attribute("data-mode", "simplified")
        expect(page.locator("#sidePanel")).not_to_be_visible()

    @pytest.mark.parametrize("compact", [False, True])
    def test_configuration_save_locks_exits_but_allows_reading_sections(self, minimal_complete_model_builder, compact):
        page = minimal_complete_model_builder.page
        if compact:
            page.set_viewport_size({"width": 700, "height": 1000})
            page.locator("#toolbar-nav .navbar-toggler").click()
        workspace = open_configure(page)
        if compact:
            selector = workspace.locator("[data-object-selector]")
            selector.select_option(index=1)
            expect(workspace.locator("form")).not_to_have_attribute("data-dirty", "true")
            workspace.get_by_role("button", name="Expand all").click()
        field(workspace, "lifespan").locator("[data-include-input]").check()
        pending = []
        page.route("**/save-simplified-inputs/", lambda route: pending.append(route))
        workspace.get_by_role("button", name="Save and return").click()
        expect(page.locator("body")).to_have_attribute("data-workspace-mutation", "updating")
        expect(page.locator('[data-action="simplified-mode"]')).to_be_disabled()
        expect(page.locator("#show-results-toolbar-btn")).to_have_attribute("aria-disabled", "true")
        expect(workspace.locator("[data-field-help]").first).to_be_disabled()
        workspace.get_by_role("button", name="Collapse all").click()
        expect(workspace.locator("[data-simplified-group]").first).not_to_have_attribute("open", "")
        if compact:
            expect(selector).to_be_enabled()
            selector.select_option(index=0)
        else:
            workspace.locator("[data-navigation-object]").first.click()
        expect(workspace.locator("[data-simplified-object]").first).to_have_attribute("open", "")
        assert len(pending) == 1
        pending.pop().continue_()
        expect(page.locator("body")).not_to_have_attribute("data-workspace-mutation", "updating")
        expect(workspace).to_have_attribute("data-mode", "simplified")

    @pytest.mark.parametrize("destination", ["results", "file", "compare", "model"])
    def test_dirty_configure_protects_every_shared_exit(self, minimal_complete_model_builder, destination):
        builder = minimal_complete_model_builder
        page = builder.page
        if destination in ("compare", "model"):
            builder.add_model_by_duplication()
        workspace = open_configure(page)
        field(workspace, "lifespan").locator("[data-include-input]").check()
        triggers = {"results": "#show-results-toolbar-btn", "file": "button[hx-get*='open-import-json-panel']",
                    "compare": "#compare-tab", "model": "#model-tab-0"}
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        page.locator(triggers[destination]).click()
        expect(page.locator("#simplified-exit-dialog")).to_be_visible()
        assert requests == []
        page.get_by_role("button", name="Stay", exact=True).click()
        expect(field(workspace, "lifespan").locator("[data-include-input]")).to_be_checked()
        page.locator(triggers[destination]).click()
        click_and_wait_for_htmx(page, page.get_by_role("button", name="Discard", exact=True))
        if destination == "results":
            expect(page.locator("#result-block")).not_to_be_empty()
            click_and_wait_for_htmx(page, page.locator("button[hx-get*='source-table']:visible"))
            expect(page.locator("#source-block")).not_to_be_empty()
        elif destination == "file":
            expect(page.locator("#sidePanel input[type='file']")).to_be_visible()
        elif destination == "compare":
            expect(page.locator("#comparison-view")).to_be_visible()
        else:
            expect(page.locator("#model-tab-strip")).to_have_attribute("data-active-slot", "0")
        expect(page.locator("[data-configure-form]")).to_have_count(0)

    @pytest.mark.parametrize("width,columns", [(1500, 3), (900, 2), (500, 1)])
    def test_workspace_container_layout(self, minimal_complete_model_builder, width, columns):
        page = minimal_complete_model_builder.page
        page.set_viewport_size({"width": width, "height": 1000})
        if width < 992:
            page.locator("#toolbar-nav .navbar-toggler").click()
        workspace = open_configure(page)
        expect(workspace.locator(".simplified-header-actions").get_by_role("button", name="Clear all")).to_be_visible()
        expect(workspace.locator(".simplified-header-actions").get_by_role("button", name="Save and return")).to_be_visible()
        expect(workspace.locator(".simplified-header-actions").get_by_role("button", name="Cancel")).to_be_visible()
        expect(workspace.locator(".simplified-expand-controls [data-selected-object-filter]")).to_be_visible()
        rendered = workspace.locator(".simplified-fields").first.evaluate(
            "el => getComputedStyle(el).gridTemplateColumns.split(' ').length")
        assert rendered == columns

@pytest.mark.e2e
class TestInlineBookmarks:
    def test_inline_sources_creation_requirements_and_delete(self, minimal_system, model_builder_page, tmp_path):
        from efootprint.api_utils.system_to_json import system_to_json
        from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import EcoLogitsVideoGenExternalAPI
        from tests.e2e.conftest import load_system_dict_into_browser
        from tests.e2e.utils import add_only_update

        api_a = EcoLogitsVideoGenExternalAPI.from_defaults("Video API A")
        api_b = EcoLogitsVideoGenExternalAPI.from_defaults("Video API B")
        data = system_to_json(minimal_system, save_computed_state=False)
        for api in [api_a, api_b]:
            add_only_update(data, system_to_json(api, save_computed_state=False))
        builder = load_system_dict_into_browser(model_builder_page, data)
        page = builder.page
        builder.get_object_card("Server", "Test Server").click_edit_button()
        draft = page.locator("#Storage_storage_capacity")
        expect(draft).to_be_visible()
        draft.fill("1234")
        main_bookmark = page.locator('#field-group-Server_lifespan [data-bookmark]')
        main_bookmark.locator("summary").click()
        expect(main_bookmark).to_have_attribute("open", "")
        storage_bookmark = page.locator('#field-group-Storage_storage_capacity [data-bookmark]')
        storage_bookmark.locator("summary").click()
        expect(main_bookmark).not_to_have_attribute("open", "")
        expect(storage_bookmark.locator("summary")).to_have_attribute("title", "Not included in Simplified inputs. Open settings.")
        expect(storage_bookmark.locator("textarea")).to_be_in_viewport(ratio=1)
        page.screenshot(path="/tmp/task8-panel-bookmark.png")
        with page.expect_response("**/patch-simplified-inputs/"):
            storage_bookmark.locator("[data-include-input]").check()
        expect(storage_bookmark.locator("[data-bookmark-status]")).to_have_text("Saved")
        expect(storage_bookmark.locator("summary")).to_have_attribute("title", "Included in Simplified inputs. Open settings.")
        expect(draft).to_have_value("1234")
        expect(page.locator("#sidePanel")).to_be_visible()
        click_and_wait_for_htmx(page, storage_bookmark.locator('[data-action="bookmark-undo"]'))
        expect(storage_bookmark.locator("[data-include-input]")).not_to_be_checked()
        expect(draft).to_have_value("1234")
        # Close the value draft through the existing discard flow.
        expect(page.locator("body")).not_to_have_attribute("data-workspace-mutation", "updating")
        page.locator("#btn-close-side-panel").click()
        expect(page.locator("#unsavedModal")).to_be_visible()
        page.locator("#continue-unsaved-modal").click()
        expect(page.locator("#sidePanel")).not_to_be_visible()

        builder.open_result_panel()
        click_and_wait_for_htmx(page, page.locator(".header-btn-result-sources-desktop"))
        row = page.locator("#source-block [data-bookmark][data-attribute='storage_capacity']").first
        source_row = row.locator("xpath=ancestor::tr")
        editor_button = source_row.locator(".source-table-edit-btn")
        editor_target = editor_button.get_attribute("data-bs-target")
        click_and_wait_for_htmx(page, editor_button)
        source_draft = page.locator(editor_target).locator(".source-editor-comment")
        source_draft.fill("Unsubmitted provenance draft")
        expect(row.locator("[data-selection-controls]")).to_have_count(0)
        with page.expect_response("**/simplified-input-bookmark/**"):
            row.locator("summary").click()
        expect(row.locator("[data-selection-controls]")).to_be_visible()
        expect(row.locator("textarea")).to_be_in_viewport(ratio=1)
        page.screenshot(path="/tmp/task8-sources-bookmark.png")
        page.set_viewport_size({"width": 1000, "height": 800})
        page.screenshot(path="/tmp/task8-sources-compact-bookmark.png")
        page.set_viewport_size({"width": 1280, "height": 720})
        with page.expect_response("**/patch-simplified-inputs/"):
            row.locator("[data-include-input]").check()
        expect(row.locator("[data-bookmark-status]")).to_have_text("Saved")
        expect(source_draft).to_have_value("Unsubmitted provenance draft")
        expect(source_draft).to_be_visible()
        page.locator(editor_target).locator('[data-action="cancel-source-table-row-editor"]').click()
        builder.close_result_panel()

        builder.get_object_card("EcoLogitsVideoGenExternalAPI", "Video API A").click_edit_button()
        controller = page.locator('#field-group-EcoLogitsVideoGenExternalAPI_model_name [data-bookmark]')
        provider = page.locator('#field-group-EcoLogitsVideoGenExternalAPI_provider [data-bookmark]')
        provider.locator("summary").click()
        with page.expect_response("**/patch-simplified-inputs/"):
            provider.locator("[data-include-input]").check()
        expect(page.locator("body")).not_to_have_attribute("data-workspace-mutation", "updating")
        expect(controller.locator("[data-include-input]")).to_be_disabled()
        with page.expect_response("**/patch-simplified-inputs/"):
            provider.locator("[data-include-input]").uncheck()
        expect(page.locator("body")).not_to_have_attribute("data-workspace-mutation", "updating")
        expect(controller.locator("[data-include-input]")).to_be_enabled()
        for width in [1280, 700]:
            page.set_viewport_size({"width": width, "height": 800})
            expect(provider.locator("textarea")).to_be_in_viewport(ratio=1)
            page.screenshot(path=f"/tmp/run-b-panel-bookmark-{width}.png")
            controller.locator("summary").click()
            expect(provider).not_to_have_attribute("open", "")
            provider.locator("summary").click()
            expect(controller).not_to_have_attribute("open", "")
        page.set_viewport_size({"width": 1280, "height": 720})
        controller.locator("summary").click()
        expect(provider).not_to_have_attribute("open", "")
        expect(controller.locator("[data-include-input]")).to_be_checked()
        page.locator("#btn-close-side-panel").click()
        expect(page.locator("#sidePanel")).not_to_be_visible()
        step = builder.get_object_card("UsageJourney", "Test Journey").get_nested_object_card(
            "UsageJourneyStep", "Test Step")
        step.open_accordion()
        step.accordion_should_be_open()
        add_job = page.locator('[hx-get*="/model_builder/open-create-object-panel/JobBase/"]:visible').first
        click_and_wait_for_htmx(page, add_job)
        page.locator("#server_or_external_api").select_option(api_a.id)
        resolution = page.locator('#field-group-EcoLogitsVideoGenExternalAPIJob_resolution [data-bookmark]')
        resolution.locator("summary").click()
        expect(resolution.locator("[data-include-input]")).to_be_checked()
        expect(resolution.locator("[data-include-input]")).to_be_disabled()
        expect(resolution.locator("[data-required-explanation]")).to_contain_text("Video API A")
        resolution.locator("textarea").fill("Resolution help retained")
        page.locator("#server_or_external_api").select_option(api_b.id)
        expect(resolution.locator("[data-include-input]")).to_be_enabled()
        expect(resolution.locator("[data-include-input]")).not_to_be_checked()
        expect(resolution.locator("textarea")).to_have_value("Resolution help retained")
        page.locator("#server_or_external_api").select_option(api_a.id)
        resolution.locator("summary").click()
        page.locator("#EcoLogitsVideoGenExternalAPIJob_resolution").select_option("720p (1280 x 720)")
        page.locator("#EcoLogitsVideoGenExternalAPIJob_name").fill("New selected video")
        builder.side_panel.submit_and_wait_for_close()
        card = builder.get_object_card("EcoLogitsVideoGenExternalAPIJob", "New selected video")
        card.click_edit_button()
        saved = page.locator('#field-group-EcoLogitsVideoGenExternalAPIJob_resolution [data-bookmark]')
        saved.locator("summary").click()
        expect(saved.locator("[data-include-input]")).to_be_checked()
        expect(saved.locator("textarea")).to_have_value("Resolution help retained")
        builder.side_panel.click_delete_button()
        expect(page.locator("#model-builder-modal")).to_contain_text("New selected video")
        expect(page.locator("#model-builder-modal")).to_contain_text("resolution")
        click_and_wait_for_htmx(page, page.get_by_role("button", name="Yes, delete", exact=True))
        expect(card.locator).to_have_count(0)
        with page.expect_download() as download:
            page.locator('a[href="download-json/"]').click()
        path = tmp_path / "bookmarks.json"
        download.value.save_as(str(path))
        exported = json.loads(path.read_text())
        fields = exported["interface_config"]["simplified_inputs"]["fields"]
        assert api_a.id in fields
        assert not any(setting.get("help") == "Resolution help retained" for attributes in fields.values()
                       for setting in attributes.values())

    def test_nested_creation_settings_and_failed_help_survive_membership_undo(self, minimal_complete_model_builder):
        builder = minimal_complete_model_builder
        page = builder.page
        builder.click_add_server()
        builder.side_panel.select_object_type("Server").fill_field("Server_name", "Bookmarked server")
        bookmark = page.locator('#field-group-Storage_storage_capacity [data-bookmark]')
        bookmark.locator("summary").click()
        bookmark.locator("[data-include-input]").check()
        bookmark.locator("textarea").fill("Nested storage help")
        builder.side_panel.submit_and_wait_for_close()
        card = builder.get_object_card("Server", "Bookmarked server")
        card.click_edit_button()
        bookmark.locator("summary").click()
        expect(bookmark.locator("[data-include-input]")).to_be_checked()
        help_field = bookmark.locator("textarea")
        expect(help_field).to_have_value("Nested storage help")
        page.route("**/patch-simplified-inputs/", lambda route: route.abort("failed"))
        help_field.fill("Failed help draft")
        help_field.press("Tab")
        expect(bookmark.locator("[data-bookmark-status]")).to_have_text("Not saved")
        expect(page.locator("body")).not_to_have_attribute("data-workspace-mutation", "updating")
        page.unroute("**/patch-simplified-inputs/")
        with page.expect_response("**/patch-simplified-inputs/"):
            bookmark.locator("[data-include-input]").uncheck()
        expect(page.locator("body")).not_to_have_attribute("data-workspace-mutation", "updating")
        expect(help_field).to_have_value("Failed help draft")
        expect(bookmark.locator("[data-bookmark-status]")).to_have_text("Not saved")
        click_and_wait_for_htmx(page, bookmark.locator('[data-action="bookmark-undo"]'))
        expect(bookmark.locator("[data-include-input]")).to_be_checked()
        expect(help_field).to_have_value("Failed help draft")
        expect(bookmark.locator("[data-bookmark-status]")).to_have_text("Not saved")
        help_field.fill("Retried storage help")
        with page.expect_response("**/patch-simplified-inputs/"):
            help_field.press("Enter")
        expect(bookmark.locator("[data-bookmark-status]")).to_have_text("Saved")
        builder.side_panel.close()
        card.click_edit_button()
        bookmark.locator("summary").click()
        expect(help_field).to_have_value("Retried storage help")

    def test_cancelled_creation_discards_provisional_bookmarks(self, minimal_complete_model_builder, tmp_path):
        builder = minimal_complete_model_builder
        page = builder.page
        builder.click_add_server()
        bookmark = page.locator('#field-group-Storage_storage_capacity [data-bookmark]')
        bookmark.locator("summary").click()
        bookmark.locator("[data-include-input]").check()
        bookmark.locator("textarea").fill("Cancelled provisional help")
        page.locator("#btn-close-side-panel").click()
        expect(page.locator("#unsavedModal")).to_be_visible()
        page.locator("#continue-unsaved-modal").click()
        expect(page.locator("#sidePanel")).not_to_be_visible()
        with page.expect_download() as download:
            page.locator('a[href="download-json/"]').click()
        path = tmp_path / "cancelled-bookmarks.json"
        download.value.save_as(str(path))
        exported = json.loads(path.read_text())
        assert not exported.get("interface_config", {}).get("simplified_inputs", {}).get("fields", {})

    def test_failed_bookmark_preserves_the_panel_and_unsaved_value(self, minimal_complete_model_builder):
        from urllib.parse import urlencode
        builder = minimal_complete_model_builder
        page = builder.page
        builder.get_object_card("Server", "Test Server").click_edit_button()
        draft = page.locator("#Storage_storage_capacity")
        draft.fill("9876")
        bookmark = page.locator('#field-group-Storage_storage_capacity [data-bookmark]')
        bookmark.locator("summary").click()
        page.route("**/patch-simplified-inputs/", lambda route: route.continue_(post_data=urlencode({
            "patch": json.dumps({"fields": {"missing-owner": {"storage_capacity": {"included": True}}}})})))
        with page.expect_response("**/patch-simplified-inputs/"):
            bookmark.locator("[data-include-input]").check()
        expect(page.locator("#model-builder-modal")).to_be_visible()
        expect(bookmark.locator("[data-bookmark-status]")).to_have_text("Not saved")
        expect(draft).to_have_value("9876")
        expect(page.locator("#sidePanel")).to_be_visible()
        page.locator("#model-builder-modal .btn-close").click()
        page.unroute("**/patch-simplified-inputs/")
        with page.expect_response("**/patch-simplified-inputs/"):
            bookmark.locator("[data-include-input]").uncheck()
        expect(bookmark.locator("[data-bookmark-status]")).to_have_text("Saved")
        expect(draft).to_have_value("9876")

    def test_simple_autosave_deduplicates_restores_rejected_field_and_refreshes_results(self, minimal_complete_model_builder):
        from urllib.parse import parse_qsl, urlencode

        page = minimal_complete_model_builder.page
        page.set_viewport_size({"width": 1440, "height": 900})
        workspace = open_configure(page)
        workspace.get_by_role("button", name="Expand all", exact=True).click()
        field(workspace, "lifespan").locator("[data-include-input]").check()
        field(workspace, "power").locator("[data-include-input]").check()
        click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
        workspace.get_by_role("button", name="Expand all", exact=True).click()
        lifespan = field(workspace, "lifespan")
        value = lifespan.locator('input[type="number"]')
        expect(lifespan.locator("[data-simplified-save-status]")).to_be_empty()
        expect(lifespan.locator(".simplified-input-row .simplified-input-control input[type='number']")).to_be_visible()
        expect(lifespan.locator(".simplified-input-row > .confidence-wrap")).to_be_visible()
        expect(lifespan.locator(".source-comment .source-line")).to_be_visible()
        expect(lifespan.locator(".simplified-provenance")).to_have_count(0)
        power = field(workspace, "power").locator('input[type="number"]')
        power_value = power.input_value()
        pending = []
        page.route("**/edit-simplified-input/**", lambda route: pending.append(route))
        value.fill("8")
        with page.expect_request("**/edit-simplified-input/**"):
            value.press("Enter")
        expect(value).to_be_disabled()
        expect(power).to_be_disabled()
        assert len(pending) == 1
        route = pending.pop()
        route.fulfill(response=route.fetch())
        expect(lifespan.locator("[data-simplified-save-status]")).to_have_text("Saved")
        expect(power).to_have_value(power_value)
        expect(power).to_be_enabled()
        value.focus()
        power.focus()
        expect(power).to_be_enabled()
        assert pending == []
        totals = page.locator("[data-quick-total]")
        assert totals.count() == 2
        assert totals.nth(0).text_content() == totals.nth(1).text_content()
        page.unroute("**/edit-simplified-input/**")
        click_and_wait_for_htmx(page, page.locator("#show-results-toolbar-btn"))
        expect(page.locator("#result-block")).not_to_be_empty()
        page.wait_for_function("() => document.querySelector('.htmx-request, .htmx-settling, .htmx-added') === null")
        panel_height = page.locator("#panel-result-btn").evaluate("el => el.getBoundingClientRect().height")
        canvas_height = page.locator("#model-builder-page").evaluate("el => el.getBoundingClientRect().height")
        assert abs(panel_height - canvas_height) < 1
        saved_results = page.locator("#result-block").inner_html()
        saved_total = totals.nth(0).text_content()

        def reject_value(route):
            data = dict(parse_qsl(route.request.post_data))
            value_key = next(key for key in data if key.endswith("-value"))
            data[value_key] = "invalid"
            route.fulfill(response=route.fetch(post_data=urlencode(data)))

        page.route("**/edit-simplified-input/**", reject_value)
        value.fill("9")
        with page.expect_response("**/edit-simplified-input/**"):
            value.press("Enter")
        expect(lifespan.locator("[data-simplified-save-status]")).to_have_text("Not saved")
        expect(value).to_have_value("8")
        expect(lifespan.locator('[data-action="simplified-retry"], [data-action="simplified-discard"]')).to_have_count(0)
        expect(page.locator("#model-builder-modal")).to_be_visible()
        assert page.locator("#result-block").inner_html() == saved_results
        assert totals.nth(0).text_content() == saved_total
        page.get_by_role("button", name="Go back", exact=True).click()
        minimal_complete_model_builder.close_result_panel()
        page.unroute("**/edit-simplified-input/**")
        value.fill("9")
        with page.expect_response("**/edit-simplified-input/**"):
            value.press("Enter")
        expect(lifespan.locator("[data-simplified-save-status]")).to_have_text("Saved")
        expect(value).to_have_value("9")
        click_and_wait_for_htmx(page, page.locator("#show-results-toolbar-btn"))
        expect(page.locator("#result-block")).not_to_be_empty()
        assert totals.nth(0).text_content() == totals.nth(1).text_content()
        assert totals.nth(0).text_content() != saved_total
        minimal_complete_model_builder.close_result_panel()
        lifespan.locator(".confidence-badge").click()
        with page.expect_response("**/edit-simplified-input/**"):
            lifespan.locator('.confidence-menu [data-level="high"]').click()
        page.wait_for_function("() => document.querySelector('.htmx-request, .htmx-settling, .htmx-added') === null")
        expect(lifespan.locator(".confidence-badge")).to_have_attribute("data-level", "high")
        lifespan.locator('[data-action="open-source-editor"]').click()
        comment = lifespan.locator(".source-editor-comment")
        comment.fill("Reviewed modeling assumption")
        with page.expect_response("**/edit-simplified-input/**"):
            comment.press("Tab")
        expect(lifespan.locator("[data-simplified-save-status]")).to_have_text("Saved")
        expect(lifespan.locator('.source-editor input[name$="__comment"]')).to_have_value("Reviewed modeling assumption")
        lifespan.locator('[data-action="open-source-editor"]').click()
        source_editor = lifespan.locator(".source-editor")
        source_editor.locator(".source-editor-select").select_option("__custom__")
        source_name = source_editor.locator(".source-editor-custom-name")
        source_link = source_editor.locator(".source-editor-custom-link")
        source_name.fill("Reviewed report")
        source_name.press("Tab")
        expect(source_link).to_be_focused()
        expect(source_link).to_be_visible()
        source_link.fill("https://example.com/report")
        with page.expect_response("**/edit-simplified-input/**"):
            source_link.press("Tab")
        expect(lifespan.locator("[data-simplified-save-status]")).to_have_text("Saved")
        expect(lifespan.get_by_role("link", name="Reviewed report", exact=True)).to_have_attribute(
            "href", "https://example.com/report")
        click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
        prior = totals.nth(0).text_content()
        click_and_wait_for_htmx(page, page.locator("#server-list button[hx-get*='open-edit-object-panel']").first)
        page.locator('#sidePanel #Server_lifespan').fill("12")
        minimal_complete_model_builder.side_panel.submit_and_wait_for_close()
        assert totals.nth(0).text_content() == totals.nth(1).text_content()
        assert totals.nth(0).text_content() != prior


@pytest.mark.e2e
def test_focused_hourly_panel_save_cancel_failure_and_mobile_preview(minimal_complete_model_builder, tmp_path):
    builder = minimal_complete_model_builder
    page = builder.page
    workspace = open_configure(page)
    workspace.get_by_role("button", name="Expand all", exact=True).click()
    field(workspace, "hourly_occurrences").locator("[data-include-input]").check()
    click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return", exact=True))
    workspace.get_by_role("button", name="Expand all", exact=True).click()
    selected = field(workspace, "hourly_occurrences")
    before = selected.locator("[data-current-value]").text_content()
    click_and_wait_for_htmx(page, selected.get_by_role("button", name="Edit timeseries"))
    panel = page.locator("[data-simplified-timeseries]")
    expect(panel.locator('[data-hourly-preview-input][name$="__initial_volume"]')).to_be_visible()
    volume = panel.locator('[name$="__initial_volume"]')
    accepted_volume = volume.input_value()
    volume.fill("25")
    builder.download_active_model(str(tmp_path / "saved-timeseries.e-f.json"))
    data = json.loads((tmp_path / "saved-timeseries.e-f.json").read_text())
    owner_id = selected.get_attribute("data-owner-id")
    exported_volume = data["UsagePattern"][owner_id]["hourly_occurrences"]["form_inputs"]["initial_volume"]
    assert float(exported_volume) == float(accepted_volume)
    expect(panel).to_be_visible()
    expect(volume).to_have_value("25")
    page.locator('[data-action="simplified-timeseries-cancel"]').click()
    expect(page.locator("#sidePanel")).not_to_be_visible()
    expect(selected.locator("[data-current-value]")).to_have_text(before)
    click_and_wait_for_htmx(page, selected.get_by_role("button", name="Edit timeseries"))
    page.set_viewport_size({"width": 500, "height": 900})
    volume.fill("30")
    preview = panel.locator("[data-hourly-timeseries-preview]")
    expect(preview.locator("canvas")).to_be_visible()
    page.wait_for_function("() => document.querySelector('[data-simplified-timeseries] canvas')._timeseriesPreviewChart")
    page.set_viewport_size({"width": 1440, "height": 1000})
    volume.fill("40")
    page.route("**/edit-simplified-input/**", reject_simplified_edit)
    click_and_wait_for_htmx(page, page.locator("#btn-submit-form"))
    expect(page.locator("#model-builder-modal")).to_be_visible()
    expect(page.locator("#sidePanel")).not_to_be_visible()
    expect(panel).to_have_count(0)
    expect(selected.locator("[data-current-value]")).to_have_text(before)
    expect(selected.locator("[data-simplified-save-status]")).to_have_text("Not saved")
    page.get_by_role("button", name="Go back", exact=True).click()
    page.unroute("**/edit-simplified-input/**")
    click_and_wait_for_htmx(page, selected.get_by_role("button", name="Edit timeseries"))
    expect(volume).to_have_value(accepted_volume)
    volume.fill("40")
    builder.side_panel.submit_and_wait_for_close()
    expect(selected.locator("[data-current-value]")).not_to_have_text(before)
    selected.locator('[data-action="open-source-editor"]').click()
    comment = selected.locator(".source-editor-comment")
    comment.fill("Forecast assumption")
    with page.expect_response("**/edit-simplified-input/**"):
        comment.press("Tab")
    expect(selected.locator("[data-simplified-save-status]")).to_have_text("Saved")
    expect(selected.locator('input[name$="__comment"]')).to_have_value("Forecast assumption")
    expect(page.locator("[data-simplified-timeseries]")).to_have_count(0)


@pytest.mark.e2e
def test_focused_edit_export_waits_for_save_and_rejected_or_invalid_edit_cancels_download(
        minimal_complete_model_builder, tmp_path):
    builder = minimal_complete_model_builder
    page = builder.page
    workspace = open_configure(page)
    field(workspace, "lifespan").locator("[data-include-input]").check()
    click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
    value = field(workspace, "lifespan").locator('input[type="number"]')
    value.fill("8")
    filename = str(tmp_path / "final-field.e-f.json")
    builder.download_active_model(filename)
    data = json.loads((tmp_path / "final-field.e-f.json").read_text())
    owner_id = field(workspace, "lifespan").get_attribute("data-owner-id")
    assert data["Storage"][owner_id]["lifespan"]["value"] == 8
    selected = field(workspace, "lifespan")
    selected.locator('[data-action="open-source-editor"]').click()
    selected.locator(".source-editor-comment").fill("Export the final metadata too")
    builder.download_active_model(filename)
    data = json.loads((tmp_path / "final-field.e-f.json").read_text())
    assert data["Storage"][owner_id]["lifespan"]["comment"] == "Export the final metadata too"
    page.route("**/edit-simplified-input/**", reject_simplified_edit)
    downloads, saves = [], []
    page.on("download", lambda download: downloads.append(download))
    page.on("request", lambda request: saves.append(request) if "/edit-simplified-input/" in request.url else None)
    value.fill("9")
    with page.expect_response("**/edit-simplified-input/**") as response_info:
        page.locator("#download-model").click()
    assert response_info.value.status == 422
    expect(selected.locator("[data-simplified-save-status]")).to_have_text("Not saved")
    expect(value).to_have_value("8")
    expect(selected.locator('input[name$="__comment"]')).to_have_value("Export the final metadata too")
    expect(page.locator("#model-builder-modal")).to_be_visible()
    assert len(saves) == 1 and downloads == []
    page.get_by_role("button", name="Go back", exact=True).click()
    page.unroute("**/edit-simplified-input/**")
    with page.expect_download() as accepted_download:
        page.locator("#download-model").click()
    accepted_download.value.save_as(filename)
    accepted_data = json.loads((tmp_path / "final-field.e-f.json").read_text())
    assert accepted_data["Storage"][owner_id]["lifespan"]["value"] == 8
    assert len(downloads) == 1
    value.fill("")
    page.locator("#download-model").click()
    expect(value).to_be_focused()
    assert not value.evaluate("el => el.checkValidity()")
    assert len(saves) == 1 and len(downloads) == 1
    value.fill("10")
    with page.expect_response("**/edit-simplified-input/**"):
        value.press("Tab")
    expect(field(workspace, "lifespan").locator("[data-simplified-save-status]")).to_have_text("Saved")
    expect(page.locator("body")).not_to_have_attribute("data-workspace-mutation", "updating")
    with page.expect_download() as download:
        page.locator("#download-model").press("Enter")
    download.value.save_as(filename)
    builder.import_json_file(filename)
    expect(page.locator("body")).to_have_attribute("data-base-view", "simplified")
    expect(field(page.locator('[data-simplified-workspace]:visible'), "lifespan").locator('input[type="number"]')).to_have_value("10")


@pytest.mark.e2e
def test_workspace_export_uses_accepted_state_after_other_model_rejection(
        minimal_complete_model_builder, tmp_path):
    builder = minimal_complete_model_builder
    page = builder.page
    builder.add_model_by_duplication()
    builder.switch_to_model(0)
    workspace = open_configure(page)
    field(workspace, "lifespan").locator("[data-include-input]").check()
    click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
    reference_id = field(workspace, "lifespan").get_attribute("data-owner-id")
    value = field(workspace, "lifespan").locator('input[type="number"]')
    accepted_value = value.input_value()
    page.route("**/edit-simplified-input/**", reject_simplified_edit)
    value.fill("9")
    with page.expect_response("**/edit-simplified-input/**") as response_info:
        value.press("Enter")
    assert response_info.value.status == 422
    expect(field(workspace, "lifespan").locator("[data-simplified-save-status]")).to_have_text("Not saved")
    expect(value).to_have_value(accepted_value)
    expect(page.locator("#model-builder-modal")).to_be_visible()
    page.get_by_role("button", name="Go back", exact=True).click()
    page.unroute("**/edit-simplified-input/**")
    builder.switch_to_model(1)
    workspace = open_configure(page)
    field(workspace, "lifespan").locator("[data-include-input]").check()
    click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
    field(workspace, "lifespan").locator('input[type="number"]').fill("7")
    builder.download_active_model(str(tmp_path / "active.e-f.json"))
    expect(page.locator('[data-simplified-target="1"] [data-simplified-save-status]')).to_have_text("Saved")
    page.locator('[data-action="simplified-mode"]').click()
    expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
    filename = str(tmp_path / "both.e-f.json")
    builder.download_workspace(filename)
    data = json.loads((tmp_path / "both.e-f.json").read_text())
    assert data["models"][0]["Storage"][reference_id]["lifespan"]["value"] == float(accepted_value)
    assert data["models"][1]["Storage"][reference_id]["lifespan"]["value"] == 7
    builder.import_json_file(filename)
    expect(page.locator("body")).to_have_attribute("data-base-view", "simplified")
    expect(field(page.locator('[data-simplified-workspace]:visible'), "lifespan").locator('input[type="number"]')).to_have_value("7")


@pytest.mark.e2e
@pytest.mark.parametrize("two_models", [False, True])
def test_export_waits_for_activation_and_runs_once(minimal_complete_model_builder, two_models):
    builder = minimal_complete_model_builder
    page = builder.page
    if two_models:
        builder.add_model_by_duplication()
    workspace = open_configure(page)
    field(workspace, "lifespan").locator("[data-include-input]").check()
    click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
    value = field(workspace, "lifespan").locator('input[type="number"]')
    value.fill("8")
    saves, downloads = [], []
    page.on("request", lambda request: saves.append(request) if "/edit-simplified-input/" in request.url else None)
    page.on("download", lambda download: downloads.append(download))
    control = builder.press_export_control()
    expect(value).to_be_focused()
    assert saves == [] and downloads == []
    builder.release_export_control(activate=False)
    assert saves == [] and downloads == []

    builder.press_export_control()
    expect(value).to_be_focused()
    assert saves == [] and downloads == []
    if two_models:
        builder.release_export_control()
        expect(control).to_have_attribute("aria-expanded", "true")
        with page.expect_download():
            page.locator("#download-workspace").click()
    else:
        with page.expect_download():
            builder.release_export_control()
    expect(field(workspace, "lifespan").locator("[data-simplified-save-status]")).to_have_text("Saved")
    assert len(saves) == 1 and len(downloads) == 1


def reject_lifespan_edit(builder):
    page = builder.page
    workspace = open_configure(page)
    field(workspace, "lifespan").locator("[data-include-input]").check()
    click_and_wait_for_htmx(page, workspace.get_by_role("button", name="Save and return"))
    page.route("**/edit-simplified-input/**", reject_simplified_edit)
    value = field(workspace, "lifespan").locator('input[type="number"]')
    accepted_value = value.input_value()
    value.fill("9")
    with page.expect_response("**/edit-simplified-input/**") as response_info:
        value.press("Enter")
    assert response_info.value.status == 422
    expect(field(workspace, "lifespan").locator("[data-simplified-save-status]")).to_have_text("Not saved")
    expect(value).to_have_value(accepted_value)
    expect(page.locator("#model-builder-modal")).to_be_visible()
    page.get_by_role("button", name="Go back", exact=True).click()
    page.unroute("**/edit-simplified-input/**")
    return workspace


@pytest.mark.e2e
def test_rejected_edit_allows_view_model_and_example_navigation(minimal_complete_model_builder):
    builder = minimal_complete_model_builder
    page = builder.page
    workspace = reject_lifespan_edit(builder)
    accepted_value = field(workspace, "lifespan").locator('input[type="number"]').input_value()
    click_and_wait_for_htmx(page, page.locator('[data-action="simplified-mode"]'))
    expect(page.locator("body")).to_have_attribute("data-base-view", "modeling")
    open_simplified(page)
    click_and_wait_for_htmx(page, page.locator('[data-action="simplified-configure"]:visible').first)
    expect(page.locator('[data-simplified-workspace]:visible')).to_have_attribute("data-mode", "configure")
    configured = page.locator('[data-simplified-workspace]:visible')
    expect(field(configured, "lifespan").locator("[data-current-value]")).to_contain_text(accepted_value)
    configured.get_by_role("button", name="Cancel", exact=True).click()
    expect(page.locator('[data-simplified-workspace]:visible')).to_have_attribute("data-mode", "simplified")
    page.on("dialog", lambda dialog: dialog.accept())
    builder.add_model_by_duplication()
    expect(page.locator("[data-model-tab]")).to_have_count(2)
    page.locator("#help-menu-toggle").click()
    page.locator(".dropdown-item[hx-get]").click()
    expect(builder.example_picker).to_be_visible()


@pytest.mark.e2e
def test_model_removal_confirmation_ignores_rejected_inline_edit(minimal_complete_model_builder):
    builder = minimal_complete_model_builder
    page = builder.page
    builder.add_model_by_duplication()
    builder.switch_to_model(0)
    reject_lifespan_edit(builder)
    builder.switch_to_model(1)
    dialogs = []
    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
    click_and_wait_for_htmx(page, page.locator("#remove-model-tab-0"))
    expect(page.locator("[data-model-tab]")).to_have_count(1)
    assert len(dialogs) == 1
    assert dialogs[0] == "Remove this modeling and return to a single-modeling session?"
    assert "Simplified input" not in dialogs[0]
    expect(page.locator('[data-simplified-target="0"]')).to_have_count(0)
    expect(page.locator('[data-simplified-target="1"]')).to_have_count(1)


@pytest.mark.e2e
def test_reset_uses_ordinary_destructive_confirmation_after_rejected_edit(minimal_complete_model_builder):
    builder = minimal_complete_model_builder
    page = builder.page
    workspace = reject_lifespan_edit(builder)
    accepted_value = field(workspace, "lifespan").locator('input[type="number"]').input_value()
    dialogs = []
    page.once("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
    page.locator("#btn-reboot-modeling").click()
    expect(field(workspace, "lifespan").locator('input[type="number"]')).to_have_value(accepted_value)
    assert "unsaved Simplified input edits" not in dialogs[0]
    builder.reset_to_default()
