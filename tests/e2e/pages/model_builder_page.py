"""Model builder page object - main page for the e-footprint interface."""
from playwright.sync_api import Page, expect

from tests.e2e.pages.side_panel_page import SidePanelPage
from tests.e2e.pages.components.object_card import ObjectCard
from tests.e2e.utils import click_and_wait_for_htmx


def card_id_selector(object_type: str) -> str:
    """CSS matching an object card's id for either canvas placement (model-comparison web_id prefix).

    Root canvas cards are now namespaced ``{system id}-{class}-{efootprint id}`` and nested cards stay
    ``{class}-{efootprint id}_in_{parent web_id}``. So a card of ``object_type`` is matched either by
    its id starting with ``{class}-`` (nested) or containing ``-{class}-`` while not being nested
    (root). The root branch excludes the derived sibling divs that embed the same web_id — ``flush-``
    (accordion-collapse) and ``add-step-to-`` — leaving only the card root div; ``:not([id*='_in_'])``
    stops a nested card whose ``_in_`` suffix embeds a parent's web_id from matching its parent's
    class; the hyphen boundary keeps "UsageJourney" from matching "UsageJourneyStep" and "Server" from
    matching "GPUServer".
    """
    root = (f"div[id*='-{object_type}-']"
            ":not([id*='_in_']):not([id^='flush-']):not([id^='add-step-to-'])")
    return f"div[id^='{object_type}-'], {root}"


class ModelBuilderPage:
    """Page object for the main model builder interface.

    This is the primary page where users build their digital service models
    by adding servers, services, jobs, usage patterns, etc.
    """

    def __init__(self, page: Page):
        self.page = page
        self.side_panel = SidePanelPage(page)
        # The builder now hosts one resident canvas per workspace slot (model-comparison); the active
        # one is the visible (non-d-none) #model-canva-{slot}. A single-model session has just slot 0.
        self.canvas = page.locator("[data-model-canvas]:not(.d-none)")
        self.template_picker = page.locator("#template-picker")

    def goto(self):
        """Navigate to the model builder page."""
        self.page.goto("/model_builder/")
        self.canvas.wait_for(state="visible")
        self.dismiss_template_picker_if_present()
        return self

    def goto_home_and_start(self):
        """Navigate to home page and click 'Start modeling' button."""
        self.page.goto("/")
        self.page.locator("#btn-start-modeling-my-service").click()
        self.canvas.wait_for(state="visible")
        self.dismiss_template_picker_if_present()
        return self

    def dismiss_template_picker_if_present(self):
        """Close the first-run picker (revealing the empty canvas behind it).

        Entering the builder with an empty model now overlays the template picker, so
        tests that want a blank usable canvas dismiss it. Closing only removes the
        overlay client-side; the empty model stays in the session. Idempotent — a no-op
        when the picker is not shown (e.g. a model that already has content).
        """
        if self.template_picker.is_visible():
            self.template_picker.locator(".btn-close").click()
            self.template_picker.wait_for(state="detached")
        return self

    def open_template_picker_from_help_menu(self):
        """Open Help ▸ Open templates from the toolbar."""
        self.page.locator("#help-menu-toggle").click()
        click_and_wait_for_htmx(self.page, self.page.locator(".dropdown-item[hx-get]"))
        self.template_picker.wait_for(state="visible")
        return self

    def pick_template(self, template_id: str):
        """Click a template card in the picker and wait for the canvas to load."""
        click_and_wait_for_htmx(self.page, self.template_picker.locator(f"[data-template-id='{template_id}']"))
        self.template_picker.wait_for(state="detached")
        self.canvas.wait_for(state="visible")
        return self

    def reset_to_default(self):
        """Reset the model via the toolbar button, confirming the discard, then dismiss the picker.

        The reset button POSTs and re-opens the first-run picker over the now-empty canvas. It
        confirms first when the current model is non-empty (the callers here always reset a
        populated model), so accept that dialog. Leaves a blank, usable canvas.
        """
        self.page.once("dialog", lambda dialog: dialog.accept())
        click_and_wait_for_htmx(self.page, self.page.locator("#btn-reboot-modeling"))
        self.dismiss_template_picker_if_present()
        return self

    def should_have_leader_line(self):
        """Assert that LeaderLine JS library is loaded."""
        self.page.wait_for_function("window.LeaderLine !== undefined")
        return self

    # --- Guided tour (driver.js) ---

    @property
    def tour_popover(self):
        """The driver.js tour popover (present only while the tour is running)."""
        return self.page.locator(".driver-popover")

    def replay_tour_from_help_menu(self):
        """Open Help ▸ Replay tour from the toolbar and wait for the overlay."""
        self.page.locator("#help-menu-toggle").click()
        self.page.locator('[data-action="replay-tour"]').click()
        self.tour_popover.wait_for(state="visible")
        return self

    def advance_tour_to_help_step(self):
        """Click Next until the tour's help step opens the help drawer.

        The help step opens the drawer via an async htmx swap, so wait for the drawer to
        appear on each step before advancing — otherwise we race past the step (clicking
        Next while it is still hidden) and run the tour off its end.
        """
        help_drawer = self.page.locator("#helpDrawer")
        for _ in range(10):
            try:
                expect(help_drawer).to_be_visible(timeout=1000)
                return self
            except AssertionError:
                pass
            next_btn = self.page.locator(".driver-popover-next-btn")
            if next_btn.count() == 0:
                break
            next_btn.click()
        raise AssertionError("Tour never reached the help step that opens the drawer.")

    # --- Object card accessors ---

    def get_object_card(self, object_type: str, name: str) -> ObjectCard:
        """Get an object card by type and name.

        Args:
            object_type: The object type prefix (e.g., 'UsageJourney', 'Server', 'Job')
            name: The display name of the object

        Returns:
            ObjectCard instance for interacting with the card
        """
        locator = self.page.locator(card_id_selector(object_type)).filter(has_text=name)
        return ObjectCard(locator)

    def get_edge_device_group_card(self, name: str) -> ObjectCard:
        """Get an edge device group card from the infrastructure column."""
        locator = self.page.locator("#edge-device-groups-list").locator(
            card_id_selector("EdgeDeviceGroup")).filter(has_text=name)
        return ObjectCard(locator)

    def get_ungrouped_edge_device_card(self, name: str) -> ObjectCard:
        """Get an ungrouped edge device card from the infrastructure column."""
        locator = self.page.locator("#edge-devices-list").locator(
            ", ".join(card_id_selector(t) for t in ("EdgeDevice", "EdgeComputer", "EdgeAppliance"))
        ).filter(has_text=name)
        return ObjectCard(locator)

    def object_should_exist(self, object_type: str, name: str):
        """Assert that an object card exists on the canvas."""
        card = self.get_object_card(object_type, name)
        card.should_exist()
        return self

    def object_should_not_exist(self, object_type: str, name: str):
        """Assert that an object card does not exist on the canvas."""
        locator = self.page.locator(card_id_selector(object_type)).filter(has_text=name)
        expect(locator).not_to_be_visible()
        return self

    def ungrouped_edge_device_should_exist(self, name: str):
        """Assert that an edge device is shown as a standalone infrastructure card."""
        self.get_ungrouped_edge_device_card(name).should_exist()
        return self

    def ungrouped_edge_device_should_not_exist(self, name: str):
        """Assert that an edge device is not shown in the ungrouped infrastructure list."""
        expect(self.page.locator("#edge-devices-list").locator(
            "div[id*='-EdgeDevice-'], div[id*='-EdgeComputer-'], div[id*='-EdgeAppliance-']"
        ).filter(has_text=name)).to_have_count(0)
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

    def click_add_external_api(self):
        """Click the 'Add external API' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#btn-add-external-api"))
        return self.side_panel

    def click_add_usage_pattern(self):
        """Click the 'Add Usage Pattern' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#add_usage_pattern"))
        return self.side_panel

    def click_add_edge_usage_pattern(self):
        """Click the 'Add Edge Usage Pattern' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#add_edge_usage_pattern"))
        return self.side_panel

    def click_add_edge_device_group(self):
        """Click the 'Add group' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#btn-add-edge-device-group"))
        return self.side_panel

    def click_add_edge_device(self):
        """Click the 'Add edge device' button (triggers HTMX)."""
        click_and_wait_for_htmx(self.page, self.page.locator("#btn-add-edge-device"))
        return self.side_panel

    # --- Model-comparison workspace tabs ---

    def add_model_by_duplication(self):
        """Open the +Add menu and duplicate the current model; the new model becomes active (slot 1)."""
        self.page.locator("#add-model-toggle").click()
        click_and_wait_for_htmx(self.page, self.page.locator(".dropdown-item", has_text="Duplicate current model"))
        # The full builder re-rendered with both canvases; wait for the new active slot to settle.
        expect(self.page.locator("#model-tab-strip")).to_have_attribute("data-active-slot", "1")
        self.page.locator("[data-model-canvas='1']").wait_for(state="visible")
        return self

    def switch_to_model(self, slot: int):
        """Click a model tab to switch the active model (client-side canvas toggle + server persist)."""
        click_and_wait_for_htmx(self.page, self.page.locator(f"[data-model-tab='{slot}']"))
        expect(self.page.locator("#model-tab-strip")).to_have_attribute("data-active-slot", str(slot))
        self.page.locator(f"[data-model-canvas='{slot}']").wait_for(state="visible")
        return self

    def remove_model(self, slot: int):
        """Remove a specific model via the browser-tab-style ✕ on its own tab, confirming the discard.

        Each model tab carries its own ✕ (id ``remove-model-tab-{slot}``) that removes that slot; the
        other model survives as the sole model, so afterwards the workspace is back in single-model mode
        with the +Add affordance.
        """
        self.page.once("dialog", lambda dialog: dialog.accept())
        click_and_wait_for_htmx(self.page, self.page.locator(f"#remove-model-tab-{slot}"))
        expect(self.page.locator("[data-model-tab]")).to_have_count(1)
        self.page.locator("[data-model-canvas]").first.wait_for(state="visible")
        return self

    def active_model_tab_count(self) -> int:
        return self.page.locator("[data-model-tab]").count()

    def active_slot(self) -> str:
        return self.page.locator("#model-tab-strip").get_attribute("data-active-slot")

    def active_model_name(self):
        """Locator for the active model's name (shown/edited in the toolbar; tabs carry fixed role labels)."""
        return self.page.locator("#system-name")

    def rename_active_model(self, new_name: str):
        """Rename the active model via the toolbar's editable system-name field."""
        click_and_wait_for_htmx(self.page, self.page.locator("#btn-change-system-name"))
        self.page.locator("#sidePanel #name").wait_for(state="visible")
        self.page.locator("#name").clear()
        self.page.locator("#name").fill(new_name)
        self.side_panel.submit_and_wait_for_close()
        return self

    def open_compare(self):
        """Click ⇄Compare and wait for the comparison dashboard to render."""
        click_and_wait_for_htmx(self.page, self.page.locator("#compare-tab"))
        self.page.locator("#comparison-dashboard").wait_for(state="visible")
        return self

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

    # --- Error modal ---

    def expect_error_modal(self, message_substring: str):
        """Assert that the error modal is visible and contains text."""
        modal = self.page.locator("#model-builder-modal")
        expect(modal).to_be_visible()
        expect(modal).to_contain_text(message_substring)
        return self

    def close_error_modal(self, modal_id: str = "model-builder-modal"):
        """Close the error modal."""
        go_back_button = self.page.locator(f"#btn-go-back-modal-{modal_id}")
        expect(go_back_button).to_be_visible()
        go_back_button.click()
        expect(self.page.locator("#model-builder-modal")).not_to_be_visible()
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
