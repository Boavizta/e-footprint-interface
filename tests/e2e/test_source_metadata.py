"""E2E tests for source metadata editing and persistence."""
import json
import re

import pytest
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.sources import Sources
from playwright.sync_api import Page, expect

from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx


SERVER_POWER_FIELD = "Server_power"
SERVER_POWER_INPUT = "#Server_power"
SERVER_POWER_SOURCE = "#source-Server_power"
SERVER_POWER_COMMENT = "Long audit note for the server power value, captured from supplier evidence."
EXISTING_SERVER_POWER_COMMENT = "Existing server power source."
CUSTOM_SOURCE_NAME = "Internal lab benchmark"
CUSTOM_SOURCE_LINK = "https://example.com/internal-lab-benchmark"
SOURCE_BLOCK_STABLE_MARKER = "source-table-was-not-replaced"


@pytest.fixture
def source_metadata_model_builder(minimal_system, model_builder_page: ModelBuilderPage) -> ModelBuilderPage:
    """Load a complete model with one existing custom source available in source pickers."""
    server = minimal_system.usage_patterns[0].usage_journey.uj_steps[0].jobs[0].server
    server.power.source = Source(CUSTOM_SOURCE_NAME, CUSTOM_SOURCE_LINK, id="labsrc")
    server.power.comment = EXISTING_SERVER_POWER_COMMENT
    server.power.confidence = "medium"

    system_data = system_to_json(minimal_system, save_calculated_attributes=False)
    return load_system_dict_into_browser(model_builder_page, system_data)


def _open_server_form(model_builder: ModelBuilderPage) -> None:
    model_builder.get_object_card("Server", "Test Server").click_edit_button()
    power_input = model_builder.page.locator(SERVER_POWER_INPUT)
    expect(power_input).to_be_attached()
    if not power_input.is_visible():
        model_builder.page.locator("#display-advanced-Server").click()
    expect(power_input).to_be_visible()


def _set_confidence(page: Page, field_id: str, level: str) -> None:
    wrap = page.locator(f'.confidence-wrap[data-field-id="{field_id}"]')
    wrap.locator(".confidence-badge").click()
    wrap.locator(f'.confidence-menu [data-level="{level}"]').click()


def _confidence_badge(page: Page, field_id: str):
    return page.locator(f'.confidence-wrap[data-field-id="{field_id}"] .confidence-badge')


def _open_source_editor(page: Page, field_id: str):
    page.locator(f"#source-{field_id} .source-line .bi-pencil-fill").click()
    editor = page.locator(f"#editor-{field_id}")
    expect(editor).to_have_class(re.compile(r"\bopen\b"))
    return editor


def _set_custom_source(editor, name: str, link: str) -> None:
    editor.locator(".source-editor-select").select_option("__custom__")
    editor.locator(".source-editor-custom-name").fill(name)
    editor.locator(".source-editor-custom-link").fill(link)


def _apply_source_editor(editor) -> None:
    editor.locator('[data-action="apply-source-editor"]').click()


def _save_reopen_server_form(model_builder: ModelBuilderPage) -> None:
    model_builder.side_panel.submit_and_wait_for_close()
    model_builder.page.reload()
    model_builder.page.locator("#model-canva").wait_for(state="visible")
    _open_server_form(model_builder)


def _open_sources_tab(model_builder: ModelBuilderPage) -> None:
    model_builder.open_result_panel()
    click_and_wait_for_htmx(model_builder.page, model_builder.page.locator(".header-btn-result-sources-desktop"))
    expect(model_builder.page.locator("#source-block")).to_have_class(re.compile(r"\bd-block\b"))


def _cell_text(text: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*{re.escape(text)}\s*$")


def _source_row(page: Page, item_name: str = "Power", object_name: str = "Test Server"):
    rows = (
        page.locator("#source-block tr[id^='source-row-display-']")
        .filter(has=page.locator(".source-col-name", has_text=_cell_text(item_name)))
        .filter(has=page.locator(".source-col-attr", has_text=_cell_text(object_name)))
    )
    expect(rows).to_have_count(1)
    return rows.first


def _mark_source_block_stable(page: Page):
    source_block = page.locator("#source-block")
    source_block.evaluate("(element, marker) => element.dataset.e2eStable = marker", SOURCE_BLOCK_STABLE_MARKER)
    return source_block


def _expect_source_block_not_reloaded(source_block) -> None:
    expect(source_block).to_have_attribute("data-e2e-stable", SOURCE_BLOCK_STABLE_MARKER)


def _row_editor(page: Page, row):
    button = row.locator(".source-table-edit-btn")
    target = button.get_attribute("data-bs-target")
    assert target
    click_and_wait_for_htmx(page, button)
    collapse = page.locator(target)
    expect(collapse.locator("form[data-action='source-table-row-edit']")).to_be_visible()
    return collapse


def _download_model_json(page: Page, path) -> dict:
    with page.expect_download() as download_info:
        page.locator('a[href="download-json/"]').click()
    download_info.value.save_as(str(path))
    return json.loads(path.read_text())


def _count_source_options(page: Page, field_id: str, source_name: str) -> int:
    return page.locator(f"#editor-{field_id} .source-editor-select option").evaluate_all(
        "(options, name) => options.filter(option => option.dataset.name === name || option.textContent.trim() === name).length",
        source_name,
    )


def _downloaded_sources_by_name(data: dict, source_name: str) -> list[dict]:
    return [source for source in data["Sources"].values() if source["name"] == source_name]


@pytest.mark.e2e
class TestSourceMetadataSidePanel:
    """Source metadata behavior in object edit forms."""

    def test_confidence_badge_persists_after_reload(self, minimal_complete_model_builder: ModelBuilderPage):
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        _open_server_form(model_builder)
        _set_confidence(page, SERVER_POWER_FIELD, "high")
        _save_reopen_server_form(model_builder)

        expect(_confidence_badge(page, SERVER_POWER_FIELD)).to_have_attribute("data-level", "high")

    def test_comment_renders_and_expands_after_reload(self, minimal_complete_model_builder: ModelBuilderPage):
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        _open_server_form(model_builder)
        editor = _open_source_editor(page, SERVER_POWER_FIELD)
        editor.locator(".source-editor-comment").fill(SERVER_POWER_COMMENT)
        _apply_source_editor(editor)
        _save_reopen_server_form(model_builder)

        comment_line = page.locator(f"{SERVER_POWER_SOURCE} .comment-line")
        expect(comment_line).not_to_have_class(re.compile(r"\bd-none\b"))
        expect(comment_line.locator(".comment-text")).to_contain_text(SERVER_POWER_COMMENT)
        comment_line.click()
        expect(comment_line).to_have_class(re.compile(r"\bexpanded\b"))

    def test_listed_source_can_be_replaced_by_custom_source(
        self,
        source_metadata_model_builder: ModelBuilderPage,
    ):
        model_builder = source_metadata_model_builder
        page = model_builder.page

        _open_server_form(model_builder)
        editor = _open_source_editor(page, SERVER_POWER_FIELD)
        editor.locator(".source-editor-select").select_option("hypothesis")
        _apply_source_editor(editor)
        model_builder.side_panel.submit_and_wait_for_close()

        _open_sources_tab(model_builder)
        row = _source_row(page)
        expect(row.locator(".source-col-source")).to_contain_text(Sources.HYPOTHESIS.name)

        model_builder.close_result_panel()
        _open_server_form(model_builder)
        editor = _open_source_editor(page, SERVER_POWER_FIELD)
        _set_custom_source(editor, CUSTOM_SOURCE_NAME, CUSTOM_SOURCE_LINK)
        _apply_source_editor(editor)
        model_builder.side_panel.submit_and_wait_for_close()

        _open_sources_tab(model_builder)
        row = _source_row(page)
        expect(row.locator(".source-col-source")).to_contain_text(CUSTOM_SOURCE_NAME)

    def test_custom_source_name_collision_keeps_distinct_source_identity(
        self,
        source_metadata_model_builder: ModelBuilderPage,
        tmp_path,
    ):
        model_builder = source_metadata_model_builder
        page = model_builder.page

        _open_server_form(model_builder)
        editor = _open_source_editor(page, SERVER_POWER_FIELD)
        _set_custom_source(editor, Sources.USER_DATA.name, "https://example.com/colliding-user-data")
        expect(editor.locator(".collision-notice")).to_be_visible()
        _apply_source_editor(editor)
        model_builder.side_panel.submit_and_wait_for_close()

        data = _download_model_json(page, tmp_path / "collision.e-f.json")
        colliding_sources = [
            source for sid, source in data["Sources"].items()
            if sid != Sources.USER_DATA.id
            and source["name"] == Sources.USER_DATA.name
            and source.get("link") == "https://example.com/colliding-user-data"
        ]
        assert len(colliding_sources) == 1

    def test_value_change_resets_confidence_and_preserves_comment(
        self,
        minimal_complete_model_builder: ModelBuilderPage,
    ):
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        _open_server_form(model_builder)
        _set_confidence(page, SERVER_POWER_FIELD, "high")
        editor = _open_source_editor(page, SERVER_POWER_FIELD)
        editor.locator(".source-editor-comment").fill(SERVER_POWER_COMMENT)
        _apply_source_editor(editor)
        model_builder.side_panel.submit_and_wait_for_close()

        _open_server_form(model_builder)
        page.locator(SERVER_POWER_INPUT).fill("246")
        expect(_confidence_badge(page, SERVER_POWER_FIELD)).to_have_class(re.compile(r"\bconfidence-just-reset\b"))
        expect(_confidence_badge(page, SERVER_POWER_FIELD)).to_have_attribute("data-level", "none")
        _save_reopen_server_form(model_builder)

        expect(_confidence_badge(page, SERVER_POWER_FIELD)).to_have_attribute("data-level", "none")
        expect(page.locator(f"{SERVER_POWER_SOURCE} .comment-text")).to_contain_text(SERVER_POWER_COMMENT)

    def test_source_editor_cancel_does_not_save_comment(
        self,
        source_metadata_model_builder: ModelBuilderPage,
    ):
        model_builder = source_metadata_model_builder
        page = model_builder.page

        _open_server_form(model_builder)
        editor = _open_source_editor(page, SERVER_POWER_FIELD)
        editor.locator(".source-editor-comment").fill("This draft should be discarded")
        editor.locator('[data-action="cancel-source-editor"]').click()
        model_builder.side_panel.submit_and_wait_for_close()

        _open_server_form(model_builder)
        expect(page.locator(f"{SERVER_POWER_SOURCE} .comment-text")).to_contain_text(EXISTING_SERVER_POWER_COMMENT)
        expect(page.locator(f"{SERVER_POWER_SOURCE} .comment-text")).not_to_contain_text("discarded")

    def test_download_upload_round_trip_preserves_metadata_and_source_identity(
        self,
        source_metadata_model_builder: ModelBuilderPage,
        tmp_path,
    ):
        model_builder = source_metadata_model_builder
        page = model_builder.page

        _open_server_form(model_builder)
        _set_confidence(page, SERVER_POWER_FIELD, "high")
        editor = _open_source_editor(page, SERVER_POWER_FIELD)
        editor.locator(".source-editor-comment").fill(SERVER_POWER_COMMENT)
        _apply_source_editor(editor)
        model_builder.side_panel.submit_and_wait_for_close()

        download_path = tmp_path / "source-metadata.e-f.json"
        data = _download_model_json(page, download_path)
        assert len(_downloaded_sources_by_name(data, CUSTOM_SOURCE_NAME)) == 1

        page.goto("/model_builder/reboot")
        page.locator("#model-canva").wait_for(state="visible")
        model_builder.import_json_file(str(download_path))

        _open_server_form(model_builder)
        expect(_confidence_badge(page, SERVER_POWER_FIELD)).to_have_attribute("data-level", "high")
        expect(page.locator(f"{SERVER_POWER_SOURCE} .comment-text")).to_contain_text(SERVER_POWER_COMMENT)
        editor = _open_source_editor(page, SERVER_POWER_FIELD)
        assert _count_source_options(page, SERVER_POWER_FIELD, CUSTOM_SOURCE_NAME) == 1


@pytest.mark.e2e
class TestSourceMetadataSourceTable:
    """Source metadata behavior in the result-panel source table."""

    def test_inline_confidence_autosaves_without_table_reload(
        self,
        minimal_complete_model_builder: ModelBuilderPage,
    ):
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        _open_sources_tab(model_builder)
        source_block = _mark_source_block_stable(page)
        row = _source_row(page)
        badge = row.locator(".confidence-badge")

        badge.click()
        with page.expect_response(lambda response: "/model_builder/edit-object/" in response.url):
            row.locator('.confidence-menu [data-level="medium"]').click()

        expect(badge).to_have_attribute("data-level", "medium")
        _expect_source_block_not_reloaded(source_block)

        page.reload()
        page.locator("#model-canva").wait_for(state="visible")
        _open_sources_tab(model_builder)
        expect(_source_row(page).locator(".confidence-badge")).to_have_attribute("data-level", "medium")

    def test_pencil_editor_apply_updates_row_without_table_reload(
        self,
        source_metadata_model_builder: ModelBuilderPage,
    ):
        model_builder = source_metadata_model_builder
        page = model_builder.page

        _open_sources_tab(model_builder)
        source_block = _mark_source_block_stable(page)
        row = _source_row(page)
        collapse = _row_editor(page, row)
        editor = collapse.locator(".source-editor")
        editor.locator(".source-editor-select").select_option("hypothesis")
        editor.locator(".source-editor-comment").fill("Changed from the source table.")

        with page.expect_response(lambda response: "/model_builder/edit-object/" in response.url):
            editor.locator('[data-action="apply-source-editor"]').click()

        _expect_source_block_not_reloaded(source_block)
        expect(collapse).not_to_have_class(re.compile(r"\bshow\b"))
        row = _source_row(page)
        expect(row.locator(".source-col-source")).to_contain_text(Sources.HYPOTHESIS.name)
        expect(row.locator(".source-col-comment")).to_contain_text("Changed from the source table.")

    def test_pencil_editor_cancel_collapses_without_saving(
        self,
        source_metadata_model_builder: ModelBuilderPage,
    ):
        model_builder = source_metadata_model_builder
        page = model_builder.page

        _open_sources_tab(model_builder)
        row = _source_row(page)
        expect(row.locator(".source-col-comment")).to_contain_text(EXISTING_SERVER_POWER_COMMENT)
        collapse = _row_editor(page, row)
        editor = collapse.locator(".source-editor")
        editor.locator(".source-editor-comment").fill("Discard this source-table draft")

        editor.locator('[data-action="cancel-source-table-row-editor"]').click()

        expect(collapse).not_to_have_class(re.compile(r"\bshow\b"))
        row = _source_row(page)
        expect(row.locator(".source-col-comment")).to_contain_text(EXISTING_SERVER_POWER_COMMENT)
        expect(row.locator(".source-col-comment")).not_to_contain_text("Discard")
