"""Side panel page object for form interactions."""
from playwright.sync_api import Page, expect


class SidePanelPage:
    """Page object for the side panel that contains forms for creating/editing objects."""

    def __init__(self, page: Page):
        self.page = page
        self.panel = page.locator("#sidePanel")
        self.form = page.locator("#sidePanelForm")
        self.submit_button = page.locator("#btn-submit-form")

    def should_be_visible(self):
        """Assert that the side panel is visible."""
        expect(self.panel).to_be_visible()
        return self

    def should_be_closed(self):
        """Assert that the side panel form is closed/empty."""
        expect(self.form).not_to_be_visible()
        return self

    def should_contain_text(self, text: str):
        """Assert that the panel contains specific text."""
        expect(self.panel).to_contain_text(text)
        return self

    def fill_field(self, field_id: str, value: str, clear_first: bool = True):
        """Fill a form field by its ID.

        Args:
            field_id: The ID of the field (without #)
            value: The value to enter
            clear_first: Whether to clear the field before typing
        """
        field = self.page.locator(f"#{field_id}")
        if clear_first:
            field.clear()
        field.fill(value)
        return self

    def select_option(self, field_id: str, value: str):
        """Select an option in a dropdown by its ID.

        Args:
            field_id: The ID of the select element (without #)
            value: The value or label to select
        """
        self.page.locator(f"#{field_id}").select_option(value)
        return self

    def submit(self):
        """Click the submit button and wait for form to close."""
        self.submit_button.click()
        return self

    def submit_and_wait_for_close(self):
        """Submit the form and wait for the panel to close."""
        self.submit_button.click()
        self.form.wait_for(state="hidden", timeout=10000)
        return self

    def click_delete_button(self):
        """Click the delete button in the panel."""
        self.panel.locator("button[hx-get*='ask-delete-object']").click()
        return self

    def confirm_delete(self):
        """Click the 'Yes, delete' confirmation button in the modal."""
        self.page.get_by_role("button", name="Yes, delete").click()
        # Wait for modal to close
        self.page.locator("#model-builder-modal").wait_for(state="hidden", timeout=5000)
        return self

    def get_type_selector(self):
        """Get the object type selector dropdown."""
        return self.page.locator("#type_object_available")

    def select_object_type(self, type_value: str):
        """Select the type of object to create."""
        self.get_type_selector().select_option(type_value)
        return self
