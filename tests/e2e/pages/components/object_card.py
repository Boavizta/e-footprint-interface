"""Object card component for interacting with modeling objects on the canvas."""
import re

from playwright.sync_api import Locator, expect

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

    def child_add_button_should_be_disabled(self, child_type: str):
        """Assert that the 'add child' button for a child type is disabled (no HTMX, has tooltip)."""
        if not self.locator.locator("button[disabled]").first.is_visible():
            self.open_accordion()
        # Disabled button has no hx-get; enabled button does
        expect(self.locator.locator(f"button[hx-get*='{child_type}']")).to_have_count(0)
        # Tooltip attrs live on the wrapper span (Bootstrap tooltips don't fire on disabled buttons).
        expect(self.locator.locator("span[data-bs-toggle='tooltip']").first).to_be_visible()
        expect(self.locator.locator("span[data-bs-toggle='tooltip'] button[disabled]").first).to_be_visible()

    def click_unlink_button(self):
        """Click the unlink button for a grouped entry (triggers HTMX)."""
        button = self.locator.locator("button.unlink-btn").first
        button.scroll_into_view_if_needed()
        # click_and_wait_for_htmx includes the 20 ms HTMX settleDelay wait.
        click_and_wait_for_htmx(self.locator.page, button)
        return self

    def set_inline_count(self, value: str):
        """Update the inline count control for a grouped entry."""
        # Wait for HTMX settleDelay so event listeners are registered on OOB-swapped inputs.
        self.locator.page.wait_for_timeout(20)
        field = self.locator.locator("input[name='count']").first
        hx_url = field.get_attribute("hx-post")
        if hx_url:
            with self.locator.page.expect_response(lambda r: hx_url in r.url):
                field.evaluate(
                    """(el, newValue) => {
                        el.value = newValue;
                        el.dispatchEvent(new Event("change", { bubbles: true }));
                    }""",
                    value,
                )
        else:
            field.evaluate(
                """(el, newValue) => {
                    el.value = newValue;
                    el.dispatchEvent(new Event("change", { bubbles: true }));
                }""",
                value,
            )
        return self

    def inline_count_should_equal(self, value: str):
        """Assert the grouped entry inline count."""
        expect(self.locator.locator("input[name='count']").first).to_have_value(value)
        return self

    def has_link_existing_child_button(self, child_type: str) -> bool:
        """Return whether a 'link existing' button is present for the given child type."""
        return self.locator.locator(
            f"button[hx-get*='open-link-existing-panel'][hx-get*='{child_type}']").count() > 0

    def click_link_existing_child_button(self, child_type: str):
        """Click the 'link existing' button for a specific child type (triggers HTMX)."""
        button = self.locator.locator(
            f"button[hx-get*='open-link-existing-panel'][hx-get*='{child_type}']")
        click_and_wait_for_htmx(self.locator.page, button)

    def open_accordion(self):
        self.locator.locator(".chevron-btn").first.click()

    def get_nested_object_card(self, object_type: str, name: str):
        """Get a nested object card rendered inside this card."""
        locator = self.locator.locator(f"div[id^='{object_type}-']").filter(has_text=name).first
        return ObjectCard(locator)

    def accordion_should_be_open(self):
        """Assert that the card's accordion is expanded (Bootstrap .show class present)."""
        expect(self.locator.locator(".accordion-collapse").first).to_have_class(re.compile(r"\bshow\b"))
        return self

    def accordion_should_be_closed(self):
        """Assert that the card's accordion is collapsed (Bootstrap .show class absent).

        Retries until the Bootstrap collapse animation completes.
        """
        expect(self.locator.locator(".accordion-collapse").first).not_to_have_class(re.compile(r"\bshow\b"))
        return self

    def has_class(self, class_name: str) -> bool:
        """Check if the card has a specific CSS class."""
        return class_name in (self.locator.get_attribute("class") or "")

    def should_exist(self, timeout: float = 5000):
        """Assert that the card exists in the DOM with its expected content."""
        # expect().to_be_attached() retries the entire locator chain including filters
        expect(self.locator).to_be_attached(timeout=timeout)
        return self

    def should_be_visible(self):
        """Assert that the card is visible."""
        self.locator.wait_for(state="visible")
        return self

    def should_have_class(self, class_name: str):
        """Assert that the card has a specific CSS class."""
        expect(self.locator).to_have_class(re.compile(class_name))
        return self
