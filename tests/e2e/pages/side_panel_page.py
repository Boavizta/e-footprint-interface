"""Side panel page object for form interactions."""
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect

from tests.e2e.utils import click_and_wait_for_htmx


class SidePanelPage:
    """Page object for the side panel that contains forms for creating/editing objects."""

    def __init__(self, page: Page):
        self.page = page
        self.panel = page.locator("#sidePanel")
        self.form = page.locator("#sidePanelForm")
        self.submit_button = page.locator("#btn-submit-form")
        self.close_button = page.locator("#btn-close-side-panel")

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

    def expand_section(self, section_name: str):
        """Open a collapsed accordion section in the side panel."""
        button = self.panel.get_by_role("button", name=section_name, exact=True)
        expect(button).to_be_visible()
        if button.get_attribute("aria-expanded") != "true":
            button.click()
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
        """Click the submit button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.submit_button)
        return self

    def submit_and_wait_for_close(self):
        """Submit the form, wait for its HTMX request, then wait for the panel to close."""
        hx_url = self.form.get_attribute("hx-post")
        if hx_url:
            try:
                with self.page.expect_response(lambda r: hx_url in r.url, timeout=1000):
                    self.submit_button.click()
            except PlaywrightTimeoutError:
                # Some valid flows close the panel without an easily matchable response in Playwright.
                pass
        else:
            self.submit_button.click()
        self.form.wait_for(state="hidden", timeout=500)
        self.page.wait_for_function(
            "() => document.querySelector('.htmx-request') === null",
            timeout=1000,
        )
        return self

    def close(self):
        """Click the close button to close the side panel."""
        self.close_button.click()
        self.form.wait_for(state="hidden", timeout=500)
        return self

    def click_delete_button(self):
        """Click the delete button in the panel (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.panel.locator("button[hx-get*='ask-delete-object']"))
        return self

    def confirm_delete(self):
        """Click the 'Yes, delete' confirmation button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.get_by_role("button", name="Yes, delete"))
        self.page.locator("#model-builder-modal").wait_for(state="hidden", timeout=5000)
        return self

    def add_to_select_multiple(self, web_id: str, option_label: str):
        """Select an option from the unselected dropdown and add it to the selection.

        Args:
            web_id: The web_id of the select_multiple field (e.g. 'UsageJourneyStep_jobs')
            option_label: The display label of the option to add
        """
        self.page.locator(f"#select-new-object-{web_id}").select_option(label=option_label)
        self.page.locator(f"#add-btn-{web_id}").click()
        return self

    def add_to_dict_count(self, web_id: str, option_label: str, count: str = "1"):
        """Add an object to a dict-count widget and optionally change its count."""
        self.page.locator(f"#select-new-object-{web_id}").select_option(label=option_label)
        self.page.locator(f"#add-btn-{web_id}").click()
        if count != "1":
            row = self.page.locator(f"#objects-already-selected-for-{web_id} tr").filter(has_text=option_label)
            row.locator("input[type='number']").fill(count)
            row.locator("input[type='number']").dispatch_event("change")
        return self

    def remove_from_dict_count(self, web_id: str, option_label: str):
        """Remove an object from a dict-count widget."""
        row = self.page.locator(f"#objects-already-selected-for-{web_id} tr").filter(has_text=option_label)
        row.locator("button").click()
        return self

    def update_dict_count_value(self, web_id: str, option_label: str, count: str):
        """Update the count for one selected entry in a dict-count widget."""
        row = self.page.locator(f"#objects-already-selected-for-{web_id} tr").filter(has_text=option_label)
        row.locator("input[type='number']").fill(count)
        row.locator("input[type='number']").dispatch_event("change")
        return self

    def link_group_member(self, web_id: str, option_label: str):
        """Link an existing subgroup or device from the group edit panel."""
        self.expand_section("Sub-groups" if "sub_group" in web_id else "Devices")
        self.page.locator(f"#select-new-object-{web_id}").select_option(label=option_label)
        with self.page.expect_response(lambda response: "/model_builder/link-dict-entry/" in response.url):
            self.page.locator(f"#add-btn-{web_id}").click()
        self.page.wait_for_function(
            "() => document.querySelector('.htmx-request') === null",
            timeout=2000,
        )
        return self

    def set_linked_entry_count(self, entry_name: str, count: str, section_name: str):
        """Update a linked subgroup or device count inside the group edit panel."""
        self.expand_section(section_name)
        row = self.panel.locator(f"[data-linked-entry-name='{entry_name}']").first
        field = row.locator("input[type='number']")
        with self.page.expect_response(lambda response: "/model_builder/update-dict-count/" in response.url):
            field.click()
            field.fill(count)
            field.press("Tab")
        self.page.wait_for_function(
            "() => document.querySelector('.htmx-request') === null",
            timeout=2000,
        )
        return self

    def remove_linked_entry(self, entry_name: str, section_name: str):
        """Remove a linked subgroup or device from the group edit panel."""
        self.expand_section(section_name)
        row = self.panel.locator(f"[data-linked-entry-name='{entry_name}']").first
        with self.page.expect_response(lambda response: "/model_builder/unlink-dict-entry/" in response.url):
            row.locator("button.unlink-btn").click()
        self.page.wait_for_function(
            "() => document.querySelector('.htmx-request') === null",
            timeout=2000,
        )
        return self

    def set_group_membership_count(self, group_name: str, count: str):
        """Update a group membership count from a device edit panel."""
        self.expand_section("Group membership")
        row = self.panel.locator(f"[data-group-membership-name='{group_name}']").first
        field = row.locator("input[type='number']")
        with self.page.expect_response(lambda response: "/model_builder/update-dict-count/" in response.url):
            field.click()
            field.fill(count)
            field.press("Tab")
        self.page.wait_for_function(
            "() => document.querySelector('.htmx-request') === null",
            timeout=2000,
        )
        return self

    def remove_group_membership(self, group_name: str):
        """Remove a group membership from a device edit panel."""
        self.expand_section("Group membership")
        row = self.panel.locator(f"[data-group-membership-name='{group_name}']").first
        with self.page.expect_response(lambda response: "/model_builder/unlink-dict-entry/" in response.url):
            row.locator("button.unlink-btn").click()
        self.page.wait_for_function(
            "() => document.querySelector('.htmx-request') === null",
            timeout=2000,
        )
        return self

    def get_type_selector(self):
        """Get the object type selector dropdown (scoped to the visible form)."""
        # Scope to sidePanelForm to avoid matching hidden storage form selector
        return self.form.locator("#type_object_available").first

    def select_object_type(self, type_value: str):
        """Select the type of object to create."""
        self.get_type_selector().select_option(type_value)
        return self
