"""E2E for the two-model comparison builder.

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

        # Edit the copy independently: rename it via the active tab's pencil.
        new_name = "Edge caching variant"
        model_builder.rename_active_model(new_name)
        expect(model_builder.active_model_name()).to_contain_text(new_name)

        # Refresh: both models, their names, and the active selection survive the reload.
        page.reload()
        model_builder.canvas.wait_for(state="visible")
        assert model_builder.active_model_tab_count() == 2
        assert model_builder.active_slot() == "1"
        expect(model_builder.active_model_name()).to_contain_text(new_name)
        # The tab carries a fixed role label, not the model name (slot 1 = "Comparison model").
        expect(page.locator("[data-model-tab='1']")).to_contain_text("Comparison model")

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
        """Duplicate → edit B → open Compare → see the comparison dashboard with the headline Δ;
        an edit to B is reflected the next time Compare opens (no stale results)."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Compare is disabled in a single-model session.
        expect(page.locator("#compare-tab")).to_be_disabled()

        # Add the second model; Compare becomes enabled.
        model_builder.add_model_by_duplication()
        expect(page.locator("#compare-tab")).to_be_enabled()

        # Open Compare → the dashboard renders with both model cards and the headline Δ card.
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
        model_builder.rename_active_model(new_name)

        model_builder.open_compare()
        expect(page.locator("#comparison-dashboard")).to_contain_text(new_name)

    def test_compare_renders_charts_with_no_leader_lines_or_console_errors(
            self, minimal_complete_model_builder):
        """Regression for the Compare-page leader-line / chart bug (post-Task-4 fix).

        Switching to the canvas-less Compare dashboard used to leave the builder's leader lines orphaned
        on <body>; their internal resize/scroll listeners then threw on disconnected anchors (uncaught
        ``Cannot read properties of null``), which could abort chart init. The comparison view carries no
        per-model chrome, and its model tabs POST switch-model with ``skip_chrome`` so the switch emits no
        chrome OOB at a missing target (``oobErrorNoTarget``).

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

        # The changed-attributes sub-table shows the step weight (the library labels it
        # "Times per journey (<step>)"); the difference type is carried by the sub-table, so there is no
        # status column to assert on.
        diff_table = page.locator("#comparison-changed-table")
        expect(diff_table).to_be_visible()
        changed_row = diff_table.locator("tbody tr", has_text="Times per journey")
        expect(changed_row).to_have_count(1)
        expect(changed_row).to_contain_text("1")
        expect(changed_row).to_contain_text("3")

    def test_compare_is_a_self_contained_view_without_model_chrome(self, minimal_complete_model_builder):
        """The Compare dashboard is self-contained: it carries the tab strip but NOT the per-model
        toolbar (tools / system name) nor the floating "Show results" button — those are model-scoped and
        live on the builder. The model names still appear (in the KPI cards), and opening Compare raises
        no console error (the dashboard's switch POSTs skip_chrome so no chrome OOB hits a missing target).
        """
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        model_builder.add_model_by_duplication()
        new_name = "Edge caching variant"
        model_builder.rename_active_model(new_name)

        model_builder.open_compare()

        # No per-model chrome on the comparison view.
        expect(page.locator("#toolbar-nav")).to_have_count(0)
        expect(page.locator("#system-name")).to_have_count(0)
        expect(page.locator("#show-results-toolbar-btn")).to_have_count(0)
        expect(page.locator("#edge-modeling-toggle-wrapper")).to_have_count(0)
        expect(page.locator("#panel-result-btn")).to_have_count(0)
        expect(page.locator("#sidePanel")).to_have_count(0)

        # The tab strip stays (to navigate back / re-compare) and the renamed model shows in the KPI cards.
        expect(page.locator("#model-tab-strip")).to_be_visible()
        expect(page.locator("#comparison-dashboard")).to_contain_text(new_name)

        assert not console_errors, f"Unexpected console errors on the Compare view: {console_errors}"

    def test_tab_strip_layout_two_models_then_one(self, minimal_complete_model_builder):
        """Tab-strip layout: with two models the order is [A ✕] [B ✕] [Compare] — every model tab
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
        expect(model_builder.active_model_name()).not_to_contain_text("Copy of")

        # Re-add B (active), then remove the ACTIVE model (B, slot 1): A is promoted to the sole active.
        model_builder.add_model_by_duplication()
        assert model_builder.active_slot() == "1"
        model_builder.remove_model(1)
        assert model_builder.active_model_tab_count() == 1
        assert model_builder.active_slot() == "0"
        expect(model_builder.active_model_name()).not_to_contain_text("Copy of")
