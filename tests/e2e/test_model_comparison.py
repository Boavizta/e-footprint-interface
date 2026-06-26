"""E2E for the two-model comparison builder.

The critical flow reserved for Playwright: duplicate the working model, edit the copy, refresh and
see both models + the active selection survive, then remove the copy to return to single-model mode.
This is the headline user-visible milestone, and it exercises the resident-canvas DOM in a real browser
(where a duplicate id would actually break HTMX/leaderlines, unlike a server-render assertion).

The comparison dashboard is a resident in-flow sibling of the canvases: opening Compare hides the
builder chrome and reveals the #comparison-view block; a model tab dismisses it client-side (reveal the
canvas), with no /model_builder/ reload — the perf win these tests guard.
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

        # The active model's own tab leaves the dashboard and re-reveals its (resident) canvas — a
        # client-side dismiss with no switch-model POST (slot 1 is already active).
        model_builder.dismiss_compare_to_active_model(1)
        model_builder.canvas.wait_for(state="visible")

        # Edit B's system name, then re-open Compare — the new name is reflected (no stale results).
        new_name = "Edge caching variant"
        model_builder.rename_active_model(new_name)

        model_builder.open_compare()
        expect(page.locator("#comparison-dashboard")).to_contain_text(new_name)

    def test_compare_renders_charts_with_no_leader_lines_or_console_errors(
            self, minimal_complete_model_builder):
        """Regression for the Compare-page leader-line / chart bug.

        Opening Compare hides the resident canvas (d-none) and tears down the builder's leader lines —
        their SVGs live on <body>, and their internal resize/scroll listeners would otherwise throw on
        disconnected anchors (uncaught ``Cannot read properties of null``), which could abort chart init.
        On dismiss the builder's lines rebuild on the now-visible canvas.

        Guards: opening Compare (and switching back across A/B/Compare, including a resize on the
        dashboard) produces no uncaught console error, the comparison chart canvases hold live Chart.js
        instances, and no builder leader-line SVG survives while the comparison view is shown.
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
        model_builder.dismiss_compare_to_active_model(1)  # same-slot dismiss: client-side, no POST
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

    def test_compare_hides_the_per_model_chrome_while_the_builder_stays_resident(
            self, minimal_complete_model_builder):
        """While Compare is open, the per-model chrome (toolbar / system name / "Show results" button /
        side panel) is hidden, not destroyed — the builder stays resident behind the comparison view so a
        model tab dismisses it client-side. The model names still appear (in the KPI cards), and opening
        Compare raises no console error.
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

        # The per-model chrome is hidden (the toolbar and the canvas region carry d-none) but still
        # resident — the builder is not torn down, so dismissing is a client-side reveal.
        expect(page.locator("#toolbar-nav")).to_be_hidden()
        expect(page.locator("#model-builder-page")).to_be_hidden()
        expect(page.locator("#comparison-view")).to_be_visible()

        # The tab strip stays (to navigate back / re-compare) and the renamed model shows in the KPI cards.
        expect(page.locator("#model-tab-strip")).to_be_visible()
        expect(page.locator("#comparison-dashboard")).to_contain_text(new_name)

        # On desktop the ⇄Compare tab stays visible and carries the active highlight (the active destination).
        expect(page.locator("#compare-tab")).to_be_visible()
        assert page.evaluate(
            "document.getElementById('compare-tab').closest('.model-tab').classList.contains('bg-white')"), \
            "the ⇄Compare tab is not highlighted as active on desktop while comparing"

        assert not console_errors, f"Unexpected console errors on the Compare view: {console_errors}"

    def test_compare_on_mobile_uses_the_resident_flow_and_hides_the_compare_tab(
            self, minimal_complete_model_builder):
        """On a phone viewport the burger ⇄Compare entry uses the resident-sibling flow (swaps into
        #comparison-view), so the builder is hidden — not destroyed — and the revealed mobile strip shows
        only the two fixed-width model tabs (⇄Compare is hidden on mobile while comparing)."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        # Build the two-model state at the default (desktop) viewport — the #add-model-toggle helper is
        # desktop-only — then shrink to a phone viewport.
        model_builder.add_model_by_duplication()
        page.set_viewport_size({"width": 390, "height": 844})

        # Tag the builder so we can prove it is hidden, not destroyed, by the resident flow.
        page.evaluate("document.getElementById('model-builder-page').dataset.identityProbe = 'kept'")

        # Open the burger and click its ⇄Compare entry (the mobile entry point).
        page.locator("#toolbar-nav .navbar-toggler").click()
        compare_btn = page.locator("#navbarSupportedContent").get_by_role("button", name="Compare")
        click_and_wait_for_htmx(page, compare_btn)
        page.locator("#comparison-dashboard").wait_for(state="visible")

        # Resident flow: the comparison view shows, the builder is hidden but NOT destroyed (probe survives).
        expect(page.locator("#comparison-view")).to_be_visible()
        expect(page.locator("#model-builder-page")).to_be_hidden()
        assert page.evaluate(
            "document.getElementById('model-builder-page').dataset.identityProbe") == "kept"

        # The revealed mobile strip shows only the two fixed-width model tabs; ⇄Compare is hidden on mobile.
        expect(page.locator("#model-tab-strip")).to_be_visible()
        expect(page.locator("[data-model-tab]")).to_have_count(2)
        expect(page.locator("#compare-tab")).to_be_hidden()

    def test_dismissing_compare_is_client_side_with_no_builder_reload(self, minimal_complete_model_builder):
        """The headline perf win: opening Compare keeps the builder DOM resident, so dismissing to a model
        is a client-side reveal — no GET /model_builder/ in the network log, and the same canvas element
        is revealed (identity preserved, never re-rendered)."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        model_builder.add_model_by_duplication()

        # Tag the resident canvas so we can prove the SAME element is revealed after dismiss (no re-render).
        page.evaluate("document.querySelector('[data-model-canvas=\"1\"]').dataset.identityProbe = 'kept'")

        model_builder.open_compare()

        builder_reloads: list[str] = []
        page.on("request", lambda req: builder_reloads.append(req.url)
                if req.url.rstrip("/").endswith("/model_builder") else None)

        # Dismiss back to the active model (slot 1) — a client-side reveal, no switch-model POST.
        model_builder.dismiss_compare_to_active_model(1)
        model_builder.canvas.wait_for(state="visible")
        expect(page.locator("#comparison-view")).to_be_hidden()
        expect(page.locator("#model-builder-page")).to_be_visible()

        # No /model_builder/ reload fired, and the canvas is the same element (identity probe survived).
        assert builder_reloads == [], f"Unexpected /model_builder/ reload(s): {builder_reloads}"
        assert page.evaluate(
            "document.querySelector('[data-model-canvas=\"1\"]').dataset.identityProbe") == "kept"

    def test_reopening_compare_shows_fresh_values_after_an_edit_no_chart_leak(
            self, minimal_complete_model_builder):
        """Reopening Compare reflects an edit (rebuilt fresh) and re-creates exactly three live charts —
        the previous instances were destroyed on dismiss (no Chart.js canvas-registry leak)."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        model_builder.add_model_by_duplication()
        model_builder.open_compare()
        page.wait_for_function(
            "() => window.charts && window.charts['comparisonPairedChart']"
            " && window.charts['comparisonCumulativeChart']")

        # Dismiss to model B (the active slot), edit it, reopen Compare — the charts are destroyed on leave
        # and re-created. The dismiss to the active model is client-side, no switch-model POST.
        model_builder.dismiss_compare_to_active_model(1)
        model_builder.canvas.wait_for(state="visible")
        # The dismiss destroys the comparison charts so they don't leak across reopen.
        assert page.evaluate("() => !window.charts['comparisonPairedChart']")

        new_name = "Edge caching variant"
        model_builder.rename_active_model(new_name)
        model_builder.open_compare()
        expect(page.locator("#comparison-dashboard")).to_contain_text(new_name)  # fresh values
        page.wait_for_function("() => window.charts && window.charts['comparisonPairedChart']")

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

    def _open_modified_side_panel(self, model_builder):
        """Open an Add-Usage-Journey side panel and mark it modified (clicking the name field tags the
        form modified, the same way the unsaved-changes guard is exercised elsewhere)."""
        model_builder.click_add_usage_journey()
        model_builder.page.locator("#UsageJourney_name").wait_for(state="visible")
        model_builder.page.locator("#UsageJourney_name").click()  # onclick tags the form modified

    def test_opening_compare_with_a_modified_panel_does_not_warn_and_keeps_the_panel(
            self, minimal_complete_model_builder):
        """Opening Compare is non-destructive: a modified side panel survives hidden behind the comparison
        view (no unsaved-changes warning, the panel is never emptied)."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        model_builder.add_model_by_duplication()
        self._open_modified_side_panel(model_builder)

        model_builder.open_compare()

        # No warning, and the panel rode along hidden inside the (now d-none) builder — still populated.
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()
        expect(page.locator("#comparison-view")).to_be_visible()
        assert page.evaluate(
            "() => document.querySelector('#sidePanel #UsageJourney_name') !== null"), \
            "the side panel was discarded on opening Compare"

    def test_same_slot_dismiss_resumes_the_panel_without_warning_or_switch_post(
            self, minimal_complete_model_builder):
        """Returning to the SAME model from Compare is a pure client-side reveal: the preserved panel
        resumes, with no unsaved-changes warning and no /switch-model/ POST."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        model_builder.add_model_by_duplication()  # slot 1 active
        self._open_modified_side_panel(model_builder)
        model_builder.open_compare()

        switch_posts: list[str] = []
        page.on("request", lambda req: switch_posts.append(req.url) if "/switch-model/" in req.url else None)

        # Click the active model's own tab — the capture handler dismisses Compare and preventDefaults the
        # click, so no switch request fires.
        page.locator("[data-model-tab='1']").click()
        expect(page.locator("#comparison-view")).to_be_hidden()
        expect(page.locator("#model-builder-page")).to_be_visible()

        # The panel resumed intact and no warning was shown; no switch-model POST went out.
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()
        expect(page.locator("#sidePanel #UsageJourney_name")).to_be_visible()
        assert switch_posts == [], f"Unexpected /switch-model/ POST(s) on a same-slot dismiss: {switch_posts}"

    def test_cross_slot_dismiss_warns_over_the_revealed_model_then_continue_switches(
            self, minimal_complete_model_builder):
        """Dismissing to the OTHER model tears the dashboard down first, so the unsaved-changes modal lands
        over the revealed edited model; Continue then re-fires the switch and lands on the other model."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        model_builder.add_model_by_duplication()  # slot 1 active
        self._open_modified_side_panel(model_builder)
        model_builder.open_compare()

        # Click the OTHER model's tab — the capture handler dismisses Compare (revealing the edited model),
        # then the switch's unsaved guard shows the modal over it (not over the comparison).
        page.locator("[data-model-tab='0']").click()
        expect(page.locator("#unsavedModal.show")).to_be_visible()
        expect(page.locator("#comparison-view")).to_be_hidden()       # warning anchored on the revealed model
        expect(page.locator("#model-builder-page")).to_be_visible()
        assert model_builder.active_slot() == "1"                     # not switched yet

        # Continue re-fires the deferred /switch-model/ and lands on the other model.
        page.locator("#continue-unsaved-modal").click()
        expect(page.locator("#model-tab-strip")).to_have_attribute("data-active-slot", "0")
        expect(page.locator("[data-model-canvas='0']")).to_be_visible()

    def test_cross_slot_dismiss_cancel_keeps_the_user_on_the_revealed_edited_model(
            self, minimal_complete_model_builder):
        """On the cross-slot warning, Cancel leaves the user anchored on the revealed edited model with the
        comparison already dismissed (the switch was never issued)."""
        model_builder = minimal_complete_model_builder
        page = model_builder.page

        model_builder.add_model_by_duplication()  # slot 1 active
        self._open_modified_side_panel(model_builder)
        model_builder.open_compare()

        page.locator("[data-model-tab='0']").click()
        expect(page.locator("#unsavedModal.show")).to_be_visible()

        page.locator("#cancel-unsaved-modal").click()
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()
        # The comparison stays dismissed and the user is still on the edited model (slot 1), panel intact.
        expect(page.locator("#comparison-view")).to_be_hidden()
        assert model_builder.active_slot() == "1"
        expect(page.locator("[data-model-canvas='1']")).to_be_visible()
        expect(page.locator("#sidePanel #UsageJourney_name")).to_be_visible()

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
