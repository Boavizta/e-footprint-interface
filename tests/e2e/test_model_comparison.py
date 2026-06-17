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

        # Switch to B and remove it — back to single-model mode with the +Add affordance restored.
        model_builder.switch_to_model(1)
        model_builder.remove_active_model()
        assert model_builder.active_model_tab_count() == 1
        expect(page.locator("#add-model-toggle")).to_be_visible()

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
