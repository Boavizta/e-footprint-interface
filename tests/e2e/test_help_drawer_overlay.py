"""Tests for the help drawer overlay behaviour.

These cover tasks 1 and 2 of the help-drawer-overlay feature:
- the canvas "?" button opens the help drawer as a non-destructive overlay on top
  of an open, dirty side panel; closing the cross restores the edit form intact.
- opening any side panel while the help drawer is open auto-closes the help drawer.
- the in-tooltip ``{class:X}`` link (rendered by handle_class into a popover subtree
  that HTMX never processed) opens the overlay via the delegated click listener — no
  URL navigation, no destructive swap.
- help-to-help navigation inside the drawer reuses the same delegated listener.
"""
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ModelBuilderPage
from tests.e2e.utils import click_and_wait_for_htmx


@pytest.mark.e2e
class TestHelpDrawerOverlay:
    """Behavioural tests for the #helpDrawer overlay layer."""

    def test_help_drawer_overlays_dirty_side_panel_without_destroying_it(
        self, empty_model_builder: ModelBuilderPage
    ):
        """Opening help while editing must not fire the unsaved modal nor wipe the form."""
        model_builder = empty_model_builder
        page = model_builder.page

        model_builder.click_add_usage_journey()
        # str.html fires tagFormAsModified on click, not on input — the click is what dirties the form.
        page.locator("#UsageJourney_name").click()
        page.locator("#UsageJourney_name").fill("dirty draft")

        help_button = page.locator("#btn-add-usage-journey + button[data-help-class='UsageJourney']")
        click_and_wait_for_htmx(page, help_button)

        # Help drawer rendered with class-help content, side panel still mounted, no modal fired.
        expect(page.locator("#helpDrawer")).to_be_visible()
        expect(page.locator("#helpDrawerTitle")).to_contain_text("About")
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()
        expect(page.locator("#sidePanel")).to_be_visible()
        expect(page.locator("#UsageJourney_name")).to_have_value("dirty draft")
        # Side panel underneath keeps the column expanded.
        expect(page.locator("#model-canva-scrollable-area")).to_have_class(re.compile(r"\bside-panel-open\b"))

        page.locator("#btn-close-help-drawer").click()

        expect(page.locator("#helpDrawer")).not_to_be_visible()
        expect(page.locator("#UsageJourney_name")).to_have_value("dirty draft")
        # Side panel still open underneath, so the column must stay expanded.
        expect(page.locator("#model-canva-scrollable-area")).to_have_class(re.compile(r"\bside-panel-open\b"))

        # formModified must still be true: closing the side panel now fires the unsaved-changes modal.
        page.locator("#btn-close-side-panel").click()
        expect(page.locator("#unsavedModal.show")).to_be_visible()

    def test_opening_side_panel_auto_closes_help_drawer(
        self, empty_model_builder: ModelBuilderPage
    ):
        """Any HTMX swap into #sidePanel must close the help drawer; closing the help drawer
        alone (no side panel underneath) must restore the canvas to full width."""
        model_builder = empty_model_builder
        page = model_builder.page
        canvas = page.locator("#model-canva-scrollable-area")

        help_button = page.locator("#btn-add-usage-journey + button[data-help-class='UsageJourney']")
        click_and_wait_for_htmx(page, help_button)
        expect(page.locator("#helpDrawer")).to_be_visible()
        expect(page.locator("#helpDrawerTitle")).to_contain_text("About")
        # Cold-open shrinks the canvas to make room for the overlay.
        expect(canvas).to_have_class(re.compile(r"\bside-panel-open\b"))

        # Closing via the cross with no side panel underneath restores the canvas to full width.
        page.locator("#btn-close-help-drawer").click()
        expect(page.locator("#helpDrawer")).not_to_be_visible()
        expect(canvas).to_have_class(re.compile(r"\bw-100\b"))
        expect(canvas).not_to_have_class(re.compile(r"\bside-panel-open\b"))

        # Re-open the help drawer, then trigger any side-panel swap and assert auto-close.
        click_and_wait_for_htmx(page, help_button)
        expect(page.locator("#helpDrawer")).to_be_visible()

        model_builder.click_add_usage_journey()

        expect(page.locator("#helpDrawer")).not_to_be_visible()
        expect(page.locator("#sidePanel")).to_be_visible()
        expect(page.locator("#UsageJourney_name")).to_be_visible()

    def test_tooltip_class_link_opens_help_drawer_without_navigating(
        self, empty_model_builder: ModelBuilderPage
    ):
        """The original bug: clicking a {class:X} link inside a field tooltip must open the
        help drawer overlay, not navigate the browser, and must leave a dirty edit form intact."""
        model_builder = empty_model_builder
        page = model_builder.page

        model_builder.click_add_usage_journey()
        page.locator("#UsageJourney_name").click()
        page.locator("#UsageJourney_name").fill("dirty draft")

        # Reveal the uj_steps tooltip programmatically — Bootstrap's hover trigger is flaky in CI,
        # and the bug is identical regardless of how the popover got shown.
        initial_url = page.url
        page.evaluate(
            "bootstrap.Popover.getOrCreateInstance("
            "document.querySelector('#field-group-UsageJourney_uj_steps [data-bs-toggle=popover]')"
            ", {animation: false}).show()"
        )

        # Bootstrap injects the popover content into a body-level subtree that HTMX never
        # processed — the link works only because help_drawer_utils.js listens on document.body.
        help_link = page.locator(
            ".popover button[data-help-class='UsageJourneyStep']"
        )
        expect(help_link).to_be_visible()
        help_link.click()

        expect(page.locator("#helpDrawer")).to_be_visible()
        expect(page.locator("#helpDrawerTitle")).to_contain_text("About Usage journey step")
        expect(page).to_have_url(initial_url)
        expect(page.locator("#UsageJourney_name")).to_have_value("dirty draft")
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()

        page.locator("#btn-close-help-drawer").click()
        expect(page.locator("#helpDrawer")).not_to_be_visible()
        expect(page.locator("#UsageJourney_name")).to_have_value("dirty draft")

    def test_help_to_help_navigation_swaps_drawer_content(
        self, empty_model_builder: ModelBuilderPage
    ):
        """Clicking a {class:Y} link rendered inside the help drawer must swap the drawer
        content without firing the unsaved-changes modal or touching the side panel."""
        model_builder = empty_model_builder
        page = model_builder.page

        help_button = page.locator("#btn-add-usage-journey + button[data-help-class='UsageJourney']")
        click_and_wait_for_htmx(page, help_button)
        expect(page.locator("#helpDrawerTitle")).to_contain_text("About Usage journey")

        # UsageJourney's class description contains "{class:UsageJourneyStep}" — that anchor is the
        # in-drawer help-to-help link.
        inner_link = page.locator(
            "#helpDrawer button[data-help-class='UsageJourneyStep']"
        ).first
        expect(inner_link).to_be_visible()
        inner_link.click()

        expect(page.locator("#helpDrawerTitle")).to_contain_text("About Usage journey step")
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()
        # No side panel was opened during this flow.
        expect(page.locator("#sidePanel")).not_to_be_visible()
