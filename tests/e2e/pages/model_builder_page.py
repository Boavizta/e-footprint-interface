"""Model builder page object - main page for the e-footprint interface."""
from playwright.sync_api import Page, expect

from tests.e2e.pages.side_panel_page import SidePanelPage
from tests.e2e.pages.components.object_card import ObjectCard
from tests.e2e.utils import click_and_wait_for_htmx


class ModelBuilderPage:
    """Page object for the main model builder interface.

    This is the primary page where users build their digital service models
    by adding servers, services, jobs, usage patterns, etc.
    """

    def __init__(self, page: Page):
        self.page = page
        self.side_panel = SidePanelPage(page)
        self.canvas = page.locator("#model-canva")

    def goto(self):
        """Navigate to the model builder page."""
        self.page.goto("/model_builder/")
        self.canvas.wait_for(state="visible")
        return self

    def goto_home_and_start(self):
        """Navigate to home page and click 'Start modeling' button."""
        self.page.goto("/")
        self.page.locator("#btn-start-modeling-my-service").click()
        self.canvas.wait_for(state="visible")
        return self

    def should_have_leader_line(self):
        """Assert that LeaderLine JS library is loaded."""
        self.page.wait_for_function("window.LeaderLine !== undefined")
        return self

    # --- Object card accessors ---

    def get_object_card(self, object_type: str, name: str) -> ObjectCard:
        """Get an object card by type and name.

        Args:
            object_type: The object type prefix (e.g., 'UsageJourney', 'Server', 'Job')
            name: The display name of the object

        Returns:
            ObjectCard instance for interacting with the card
        """
        # Use CSS selector that matches the exact type prefix followed by hyphen
        # This avoids matching "UsageJourneyStep" when looking for "UsageJourney"
        locator = self.page.locator(f"div[id^='{object_type}-']").filter(has_text=name)
        return ObjectCard(locator)

    def object_should_exist(self, object_type: str, name: str):
        """Assert that an object card exists on the canvas."""
        card = self.get_object_card(object_type, name)
        card.should_exist()
        return self

    def object_should_not_exist(self, object_type: str, name: str):
        """Assert that an object card does not exist on the canvas."""
        locator = self.page.locator(f"div[id^='{object_type}'] p").filter(has_text=name)
        expect(locator).not_to_be_visible()
        return self

    # --- Add object buttons ---

    def click_add_usage_journey(self):
        """Click the 'Add Usage Journey' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#btn-add-usage-journey"))
        return self.side_panel

    def click_add_server(self):
        """Click the 'Add Server' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#btn-add-server"))
        return self.side_panel

    def click_add_usage_pattern(self):
        """Click the 'Add Usage Pattern' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#add_usage_pattern"))
        return self.side_panel

    # --- Result panel ---

    def open_result_panel(self):
        """Open the result panel (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#btn-open-panel-result"))
        self.page.locator("#lineChart").wait_for(state="visible")
        self.page.wait_for_timeout(100)  # Wait for chart to render
        return self

    def close_result_panel(self):
        """Close the result panel."""
        self.page.locator("#result-block div[onclick='hidePanelResult()']").click()
        return self

    def result_chart_should_be_visible(self):
        """Assert that the result chart is visible."""
        expect(self.page.locator("#lineChart")).to_be_visible()
        return self

    # --- Import/Export ---

    def open_import_panel(self):
        """Open the JSON import panel."""
        click_and_wait_for_htmx(self.page, self.page.locator("button[hx-get*='open-import-json-panel']"))
        self.page.locator("input[type='file']").wait_for(state="attached")
        return self.side_panel

    def import_json_file(self, file_path: str):
        """Import a JSON model file.

        Args:
            file_path: Path to the JSON file to import
        """
        self.open_import_panel()
        self.page.locator("input[type='file']").set_input_files(file_path)
        # Here we don’t use click_and_wait_for_htmx because hx attributes are not on the button but on the form
        self.page.wait_for_timeout(20)
        with self.page.expect_response(lambda r: "upload-json" in r.url):
            self.page.locator("button[type='submit']").click()
        self.side_panel.should_be_closed()
        return self
