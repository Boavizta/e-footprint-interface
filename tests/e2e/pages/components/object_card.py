"""Object card component for interacting with modeling objects on the canvas."""
from playwright.sync_api import Locator

from tests.e2e.utils import click_and_wait_for_htmx


class ObjectCard:
    """Represents an object card on the model builder canvas.

    Object cards display modeling objects (servers, jobs, usage patterns, etc.)
    and provide buttons for editing, deleting, and adding related objects.
    """

    def __init__(self, locator: Locator):
        self.locator = locator

    def click_edit_button(self):
        """Click the main edit button on the card (triggers HTMX)."""
        click_and_wait_for_htmx(self.locator.page, self.locator.locator("button[id^='button-']").first)

    def click_delete_button(self):
        """Click the delete button (triggers HTMX)."""
        click_and_wait_for_htmx(self.locator.page, self.locator.locator("button[hx-get*='ask-delete-object']"))

    def click_add_step_button(self):
        """Click the 'add step' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.locator.page, self.locator.locator("div[id^='add-step-to']"))

    def click_add_service_button(self):
        """Click the 'add service' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.locator.page, self.locator.locator("button[id^='add-service-to']"))

    def click_add_job_button(self):
        """Click the 'add job' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.locator.page, self.locator.locator("button[hx-get*='open-create-object-panel/JobBase']"))

    def click_add_child_button(self, child_type: str):
        """Click the 'add child' button for a specific child type (triggers HTMX)."""
        button = self.locator.locator(f"button[hx-get*='{child_type}']").first
        if not button.is_visible():
            self.open_accordion()
        click_and_wait_for_htmx(self.locator.page, button)

    def open_accordion(self):
        self.locator.locator(".chevron-btn").first.click()

    def has_class(self, class_name: str) -> bool:
        """Check if the card has a specific CSS class."""
        return class_name in (self.locator.get_attribute("class") or "")

    def should_exist(self, timeout: float = 5000):
        """Assert that the card exists in the DOM with its expected content."""
        from playwright.sync_api import expect
        # expect().to_be_attached() retries the entire locator chain including filters
        expect(self.locator).to_be_attached(timeout=timeout)
        return self

    def should_be_visible(self):
        """Assert that the card is visible."""
        self.locator.wait_for(state="visible")
        return self

    def should_have_class(self, class_name: str):
        """Assert that the card has a specific CSS class."""
        from playwright.sync_api import expect
        import re
        expect(self.locator).to_have_class(re.compile(class_name))
        return self
