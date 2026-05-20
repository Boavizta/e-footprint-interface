"""Tests for the help drawer overlay behaviour.

These cover task 1 of the help-drawer-overlay feature:
- the canvas "?" button opens the help drawer as a non-destructive overlay on top
  of an open, dirty side panel; closing the cross restores the edit form intact.
- opening any side panel while the help drawer is open auto-closes the help drawer.
"""
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
        page.locator("#UsageJourney_name").click()
        page.locator("#UsageJourney_name").type("dirty draft")

        help_button = page.locator("#btn-add-usage-journey + button.help-drawer-trigger")
        click_and_wait_for_htmx(page, help_button)

        # Help drawer visible, side panel still mounted with the dirty value, no modal fired.
        expect(page.locator("#helpDrawer")).to_be_visible()
        expect(page.locator("#unsavedModal.show")).not_to_be_visible()
        expect(page.locator("#sidePanel")).to_be_visible()
        expect(page.locator("#UsageJourney_name")).to_have_value("dirty draft")

        page.locator("#btn-close-help-drawer").click()

        expect(page.locator("#helpDrawer")).not_to_be_visible()
        expect(page.locator("#UsageJourney_name")).to_have_value("dirty draft")

        # formModified must still be true: closing the side panel now fires the unsaved-changes modal.
        page.locator("#btn-close-side-panel").click()
        expect(page.locator("#unsavedModal.show")).to_be_visible()

    def test_opening_side_panel_auto_closes_help_drawer(
        self, empty_model_builder: ModelBuilderPage
    ):
        """Any HTMX swap into #sidePanel must close the help drawer."""
        model_builder = empty_model_builder
        page = model_builder.page

        help_button = page.locator("#btn-add-usage-journey + button.help-drawer-trigger")
        click_and_wait_for_htmx(page, help_button)
        expect(page.locator("#helpDrawer")).to_be_visible()

        model_builder.click_add_usage_journey()

        expect(page.locator("#helpDrawer")).not_to_be_visible()
        expect(page.locator("#sidePanel")).to_be_visible()
        expect(page.locator("#UsageJourney_name")).to_be_visible()
