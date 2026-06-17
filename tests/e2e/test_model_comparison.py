"""E2E for the two-model comparison builder (model-comparison Task 3).

The critical flow reserved for Playwright: duplicate the working model, edit the copy, refresh and
see both models + the active selection survive, then remove the copy to return to single-model mode.
This is the headline user-visible milestone, and it exercises the resident-canvas DOM in a real browser
(where a duplicate id would actually break HTMX/leaderlines, unlike a server-render assertion).
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.utils import click_and_wait_for_htmx


@pytest.mark.e2e
class TestModelComparisonWorkspace:

    def test_duplicate_edit_refresh_and_remove(self, minimal_complete_model_builder):
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Single-model session: one tab, the +Add affordance, Compare disabled.
        expect(page.locator("#model-tab-strip")).to_be_visible()
        assert model_builder.active_model_tab_count() == 1
        expect(page.locator("#compare-tab")).to_be_disabled()

        # Add the second model by duplication — it becomes active (slot 1).
        model_builder.add_model_by_duplication()
        assert model_builder.active_model_tab_count() == 2
        assert model_builder.active_slot() == "1"
        expect(page.locator("[data-model-canvas='1']")).to_be_visible()
        expect(page.locator("[data-model-canvas='0']")).to_be_hidden()

        # Edit the copy independently: rename its system.
        new_name = "Edge caching variant"
        click_and_wait_for_htmx(page, page.locator("#btn-change-system-name"))
        page.locator("#sidePanel").wait_for(state="attached")
        page.locator("#name").clear()
        page.locator("#name").fill(new_name)
        model_builder.side_panel.submit_and_wait_for_close()
        expect(page.locator("#system-name")).to_contain_text(new_name)

        # Refresh: both models, their names, and the active selection survive the reload.
        page.reload()
        model_builder.canvas.wait_for(state="visible")
        assert model_builder.active_model_tab_count() == 2
        assert model_builder.active_slot() == "1"
        expect(page.locator("#system-name")).to_contain_text(new_name)
        expect(page.locator("[data-model-tab='1']")).to_contain_text(new_name)

        # Switch back to model A with no full reload (client-side canvas toggle).
        model_builder.switch_to_model(0)
        assert model_builder.active_slot() == "0"
        expect(page.locator("[data-model-canvas='0']")).to_be_visible()
        expect(page.locator("[data-model-canvas='1']")).to_be_hidden()

        # Each model tab carries its own browser-tab-style ✕ (one per model); removing the active model
        # (slot 1) returns to a single-model session with the +Add affordance restored and no ✕ left.
        model_builder.switch_to_model(1)
        expect(page.locator(".model-tab__close")).to_have_count(2)
        model_builder.remove_model(1)
        assert model_builder.active_model_tab_count() == 1
        expect(page.locator("#add-model-toggle")).to_be_visible()
        expect(page.locator(".model-tab__close")).to_have_count(0)

    def test_compare_shows_the_headline_delta_and_reflects_edits(self, minimal_complete_model_builder):
        """The Task-4 payoff flow: duplicate → edit B → open Compare → see the §4.2 dashboard with the
        headline Δ; an edit to B is reflected the next time Compare opens (no stale results)."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Compare is disabled in a single-model session.
        expect(page.locator("#compare-tab")).to_be_disabled()

        # Add the second model; Compare becomes enabled.
        model_builder.add_model_by_duplication()
        expect(page.locator("#compare-tab")).to_be_enabled()

        # Open Compare → the §4.2 dashboard renders with both model cards and the headline Δ card.
        model_builder.open_compare()
        expect(page.locator("#comparison-dashboard")).to_be_visible()
        expect(page.locator("#comparison-dashboard")).to_contain_text("CO₂e")          # KPI totals
        expect(page.locator("#comparison-dashboard")).to_contain_text("What explains the difference")
        # The paired and cumulative chart canvases are present (Chart.js draws into them client-side).
        expect(page.locator("#comparisonPairedChart")).to_be_visible()
        expect(page.locator("#comparisonCumulativeChart")).to_be_visible()

        # A model tab leaves the dashboard and re-opens the builder on model B's slot.
        model_builder.switch_to_model(1)
        model_builder.canvas.wait_for(state="visible")

        # Edit B's system name, then re-open Compare — the new name is reflected (no stale results).
        new_name = "Edge caching variant"
        click_and_wait_for_htmx(page, page.locator("#btn-change-system-name"))
        page.locator("#sidePanel").wait_for(state="attached")
        page.locator("#name").clear()
        page.locator("#name").fill(new_name)
        model_builder.side_panel.submit_and_wait_for_close()

        model_builder.open_compare()
        expect(page.locator("#comparison-dashboard")).to_contain_text(new_name)

    def test_compare_renders_charts_with_no_leader_lines_or_console_errors(
            self, minimal_complete_model_builder):
        """Regression for the Compare-page leader-line / chart bug (post-Task-4 fix).

        Switching to the canvas-less Compare dashboard used to leave the builder's leader lines orphaned
        on <body>; their internal resize/scroll listeners then threw on disconnected anchors (uncaught
        ``Cannot read properties of null``), which could abort chart init, while a model tab on the
        dashboard POSTed switch-model whose chrome OOB fragments had no targets (``oobErrorNoTarget``).

        Guards: opening Compare (and switching back across A/B/Compare, including a resize on the
        dashboard) produces no uncaught console error, the comparison chart canvases hold live Chart.js
        instances, and no builder leader-line SVG survives onto the dashboard.
        """
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        model_builder.add_model_by_duplication()

        # Enter Compare: charts draw, builder leader lines are gone, and a dashboard resize (the action
        # that crashed against disconnected anchors) is clean.
        model_builder.open_compare()
        page.wait_for_function(
            "() => window.charts && window.charts['comparisonPairedChart']"
            " && window.charts['comparisonCumulativeChart']")
        assert page.evaluate("document.querySelectorAll('svg.leader-line').length") == 0
        page.set_viewport_size({"width": 1000, "height": 720})
        page.set_viewport_size({"width": 1440, "height": 900})

        # A model tab leaves the dashboard for the builder — no chrome-OOB-without-target error — and the
        # builder's leader lines rebuild on the now-visible canvas.
        model_builder.switch_to_model(0)
        model_builder.canvas.wait_for(state="visible")
        page.wait_for_function("() => document.querySelectorAll('svg.leader-line').length > 0")

        # Bounce among the three tabs once more to catch any residual orphaned-line / OOB noise.
        model_builder.switch_to_model(1)
        model_builder.open_compare()
        page.wait_for_function("() => window.charts && window.charts['comparisonPairedChart']")
        model_builder.switch_to_model(1)
        model_builder.canvas.wait_for(state="visible")

        assert not console_errors, f"Unexpected console errors on the Compare flow: {console_errors}"

    def test_compare_surfaces_a_changed_usage_journey_step_weight(self, minimal_complete_model_builder):
        """The dict-weight diff fix: duplicate, change a usage-journey-step's count on the copy only, open
        Compare and see that weight difference in "What differs between the models" — the case that used to
        show nothing (the count is an ExplainableObjectDict value the input diff used to skip)."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Duplicate (the copy becomes active, slot 1) and bump its step count from 1 to 3 — the two models
        # now differ ONLY by a uj_steps weight.
        model_builder.add_model_by_duplication()
        # The first count input on the active canvas is the step's "Times per journey" weight (a second,
        # hidden one is the step→job count). hx-trigger="change" needs a real edit, so type and press Enter.
        count_input = page.locator("[data-model-canvas='1'] input.count-inline-edit").first
        count_input.wait_for(state="visible")
        with page.expect_response(lambda r: "update-dict-count" in r.url):
            count_input.click()
            count_input.fill("3")
            count_input.press("Enter")

        model_builder.open_compare()

        # The diff table shows the changed step weight (the library labels it "Times per journey (<step>)").
        diff_table = page.locator("#comparison-diff-table")
        expect(diff_table).to_be_visible()
        changed_row = diff_table.locator("tbody tr", has_text="Times per journey")
        expect(changed_row).to_have_count(1)
        expect(changed_row).to_contain_text("1")
        expect(changed_row).to_contain_text("3")
        expect(changed_row).to_contain_text("changed")

    def test_compare_keeps_the_shared_toolbar_for_the_active_model(self, minimal_complete_model_builder):
        """Regression: the shared toolbar (system name, edge toggle, upload/download, "Show results")
        must persist on the Compare dashboard, bound to the active model — singleton-chrome design.

        It used to vanish because the dashboard rendered without the builder's toolbar/side-panel/result
        chrome. Guards: the toolbar and its system name (showing the *active* model) are present on
        Compare, and its actions (rename → #sidePanel, "Show results" → #result-block) work over the
        dashboard with no uncaught console error or missing-target.
        """
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        # Duplicate (B becomes active) and rename B so we can assert the toolbar shows the *active* model.
        model_builder.add_model_by_duplication()
        new_name = "Edge caching variant"
        click_and_wait_for_htmx(page, page.locator("#btn-change-system-name"))
        page.locator("#sidePanel").wait_for(state="attached")
        page.locator("#name").clear()
        page.locator("#name").fill(new_name)
        model_builder.side_panel.submit_and_wait_for_close()

        model_builder.open_compare()

        # The toolbar persists on the dashboard, bound to the active model (B).
        expect(page.locator("#toolbar-nav")).to_be_visible()
        expect(page.locator("#system-name")).to_contain_text(new_name)
        expect(page.locator("#show-results-toolbar-btn")).to_be_visible()
        expect(page.locator("#edge-modeling-toggle-wrapper")).to_be_visible()

        # The rename side panel opens over the dashboard (its layout helper must tolerate the absent
        # builder canvas), then closes cleanly.
        click_and_wait_for_htmx(page, page.locator("#btn-change-system-name"))
        page.locator("#sidePanel #name").wait_for(state="visible")
        model_builder.side_panel.close()

        # "Show results" opens the active model's result panel over the dashboard.
        click_and_wait_for_htmx(page, page.locator("#show-results-toolbar-btn"))
        page.locator("#lineChart").wait_for(state="visible")

        assert not console_errors, f"Unexpected console errors on the Compare toolbar flow: {console_errors}"

    def test_tab_strip_layout_two_models_then_one(self, minimal_complete_model_builder):
        """§4.2 tab-strip layout: with two models the order is [A ✕] [B ✕] [Compare] — every model tab
        has its own browser-tab-style ✕ and Compare reads as a tab flush immediately to the right of the
        last model tab (not a floated/right-anchored button); with one model it's [A] [+Add] [Compare
        disabled] with no ✕ on the sole model."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Single model: no ✕, the +Add menu, Compare disabled.
        expect(page.locator(".model-tab__close")).to_have_count(0)
        expect(page.locator("#add-model-toggle")).to_be_visible()
        expect(page.locator("#compare-tab")).to_be_disabled()

        model_builder.add_model_by_duplication()

        # Two models: each model tab carries its own ✕ (one per tab); Compare is enabled.
        expect(page.locator("[data-model-tab]")).to_have_count(2)
        expect(page.locator(".model-tab__close")).to_have_count(2)
        for slot in (0, 1):
            tab = page.locator(f"#model-tab-{slot}").locator("xpath=ancestor::span[contains(@class,'model-tab')][1]")
            expect(tab.locator(".model-tab__close")).to_have_count(1)
            expect(page.locator(f"#remove-model-tab-{slot}")).to_be_visible()
        expect(page.locator("#compare-tab")).to_be_enabled()

        # DOM order: model tabs, then the Compare tab last.
        tab_order = page.eval_on_selector_all(
            "#model-tab-strip [data-model-tab], #model-tab-strip #compare-tab",
            "els => els.map(e => e.id)")
        assert tab_order == ["model-tab-0", "model-tab-1", "compare-tab"], tab_order

        # Compare reads as a tab (shares the .model-tab affordance, accented as a destination) and sits
        # flush right after the last model tab — not floated to the edge (no margin-left:auto gap).
        tab_layout = page.evaluate(
            """() => {
                const cmp = document.getElementById('compare-tab').closest('.model-tab');
                const lastModelTab = document.getElementById('model-tab-1').closest('.model-tab');
                const gap = cmp.getBoundingClientRect().left - lastModelTab.getBoundingClientRect().right;
                return {
                    isCompareTab: cmp.classList.contains('model-tab') && cmp.classList.contains('model-tab--compare'),
                    gap,
                    marginLeft: getComputedStyle(cmp).marginLeft,
                };
            }""")
        assert tab_layout["isCompareTab"], tab_layout
        assert tab_layout["gap"] < 12, f"Compare not flush after the last model tab: {tab_layout}"
        assert tab_layout["marginLeft"] != "auto", tab_layout

    def test_remove_non_active_model_keeps_active(self, minimal_complete_model_builder):
        """Removing the NON-active model via its ✕ leaves the current active model active; removing the
        active model promotes the survivor. Each ✕ targets its own slot (per-tab remove, not "active")."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Duplicate → B (slot 1) is active. Switch so A (slot 0) is active, then remove the NON-active B.
        model_builder.add_model_by_duplication()
        model_builder.switch_to_model(0)
        assert model_builder.active_slot() == "0"
        model_builder.remove_model(1)
        assert model_builder.active_model_tab_count() == 1
        # The surviving sole model is A, still active.
        assert model_builder.active_slot() == "0"
        expect(page.locator("#system-name")).not_to_contain_text("Copy of")

        # Re-add B (active), then remove the ACTIVE model (B, slot 1): A is promoted to the sole active.
        model_builder.add_model_by_duplication()
        assert model_builder.active_slot() == "1"
        model_builder.remove_model(1)
        assert model_builder.active_model_tab_count() == 1
        assert model_builder.active_slot() == "0"
        expect(page.locator("#system-name")).not_to_contain_text("Copy of")

    def test_compare_assumptions_diff_clears_the_results_button(self, minimal_complete_model_builder):
        """Bug A: the "What differs" section used to overflow under the floating results button. With a
        real diff present, the last diff row must sit fully above the results button when scrolled to
        the bottom of the dashboard."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Create a one-row diff: duplicate, bump the copy's first step count so the models differ.
        model_builder.add_model_by_duplication()
        count_input = page.locator("[data-model-canvas='1'] input.count-inline-edit").first
        count_input.wait_for(state="visible")
        with page.expect_response(lambda r: "update-dict-count" in r.url):
            count_input.click()
            count_input.fill("7")
            count_input.press("Enter")

        model_builder.open_compare()
        expect(page.locator("#comparison-diff-table")).to_be_visible()

        # Scroll the dashboard to the bottom; the last diff row clears the floating results button.
        cleared = page.evaluate(
            """() => {
                const dash = document.getElementById('comparison-dashboard');
                dash.scrollTop = dash.scrollHeight;
                const rows = document.querySelectorAll('#comparison-diff-table tbody tr');
                const lastRow = rows[rows.length - 1].getBoundingClientRect();
                const btn = document.getElementById('panel-result-btn').getBoundingClientRect();
                return lastRow.bottom <= btn.top + 1;
            }""")
        assert cleared, "The last assumptions-diff row is occluded by the floating results button"
