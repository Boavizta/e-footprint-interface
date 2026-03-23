"""Page objects for the Sankey impact repartition section."""
from playwright.sync_api import Page, Locator, expect

from tests.e2e.pages.model_builder_page import ModelBuilderPage


class SankeyCard:
    """Page object for a single Sankey analysis card."""

    def __init__(self, page: Page, card_id: str):
        self.page = page
        self.card_id = card_id

    @property
    def _container(self) -> Locator:
        return self.page.locator(f"#sankey-card-{self.card_id}")

    def diagram_area_locator(self) -> Locator:
        return self.page.locator(f"#sankey-diagram-area-{self.card_id}")

    def plot_locator(self) -> Locator:
        return self.page.locator(f"#sankey-plot-{self.card_id}")

    def settings_visible(self) -> bool:
        settings_el = self.page.locator(f"#settings-{self.card_id}")
        return settings_el.is_visible()

    def title_text(self) -> str:
        title_el = self.page.locator(f"#sankey-title-{self.card_id} .card-title")
        return title_el.inner_text()

    def diagram_is_rendered(self) -> bool:
        """Check that ECharts has rendered content inside the plot container."""
        plot_el = self.plot_locator()
        return plot_el.locator("canvas").count() > 0

    def wait_for_diagram_update(self, timeout: int = 10000) -> None:
        """Wait for ECharts to render inside the plot container."""
        self.plot_locator().locator("canvas").first.wait_for(state="attached", timeout=timeout)

    def set_lifecycle_filter(self, value: str) -> None:
        """Set the lifecycle phase filter. value: '' | 'Manufacturing' | 'Usage'."""
        with self.page.expect_response(lambda r: "sankey-diagram" in r.url):
            self._container.locator('[name="lifecycle_phase_filter"]').select_option(value)

    def set_aggregation_threshold(self, value: float) -> None:
        """Set the aggregation threshold slider (0–10)."""
        with self.page.expect_response(lambda r: "sankey-diagram" in r.url):
            self._container.locator('[name="aggregation_threshold_percent"]').fill(str(value))
            self._container.locator('[name="aggregation_threshold_percent"]').dispatch_event("change")

    def toggle_phase_split(self, enabled: bool) -> None:
        checkbox = self._container.locator('[name="phase_split"]')
        if checkbox.is_checked() != enabled:
            with self.page.expect_response(lambda r: "sankey-diagram" in r.url):
                checkbox.click()

    def toggle_category_split(self, enabled: bool) -> None:
        checkbox = self._container.locator('[name="category_split"]')
        if checkbox.is_checked() != enabled:
            with self.page.expect_response(lambda r: "sankey-diagram" in r.url):
                checkbox.click()

    def toggle_object_split(self, enabled: bool) -> None:
        checkbox = self._container.locator('[name="object_split"]')
        if checkbox.is_checked() != enabled:
            with self.page.expect_response(lambda r: "sankey-diagram" in r.url):
                checkbox.click()

    def open_advanced(self) -> None:
        """Open the advanced settings panel if not already open."""
        advanced_el = self.page.locator(f"#advanced-{self.card_id}")
        if not advanced_el.is_visible():
            self._container.locator(".advanced-toggle").click()
            advanced_el.wait_for(state="visible")

    def toggle_analyse_by_chip(self, label: str) -> None:
        """Toggle an analyse-by chip by its UI label text."""
        with self.page.expect_response(lambda r: "sankey-diagram" in r.url):
            self._container.locator(f'.chip[data-type="analyse"]').filter(has_text=label).click()

    def toggle_exclude_chip(self, label: str) -> None:
        """Toggle an exclude chip by its UI label text."""
        with self.page.expect_response(lambda r: "sankey-diagram" in r.url):
            self._container.locator(f'.chip[data-type="exclude"]').filter(has_text=label).click()

    def analyse_by_chip_exists(self, label: str) -> bool:
        return self._container.locator(f'.chip[data-type="analyse"]').filter(has_text=label).count() > 0

    def exclude_chip_exists(self, label: str) -> bool:
        return self._container.locator(f'.chip[data-type="exclude"]').filter(has_text=label).count() > 0

    def remove(self) -> None:
        """Remove this card (client-side only). Waits for fade-out animation."""
        self._container.locator(".btn-delete").click()
        self._container.wait_for(state="hidden", timeout=2000)


class SankeyPage:
    """Page object for the full Sankey section inside the result panel."""

    def __init__(self, model_builder_page: ModelBuilderPage):
        self.page = model_builder_page.page
        self._model_builder_page = model_builder_page

    def first_card(self) -> SankeyCard:
        """Return the first Sankey card, waiting for it to be created."""
        self.page.locator("#sankey-cards-container .sankey-card").first.wait_for(state="visible", timeout=10000)
        return self.cards()[0]

    def cards(self) -> list[SankeyCard]:
        """Return all current SankeyCard objects."""
        cards_locator = self.page.locator("#sankey-cards-container .sankey-card")
        count = cards_locator.count()
        result = []
        for i in range(count):
            card_el = cards_locator.nth(i)
            raw_id = card_el.get_attribute("id") or ""
            card_id = raw_id.replace("sankey-card-", "")
            result.append(SankeyCard(self.page, card_id))
        return result

    def add_card(self) -> SankeyCard:
        """Click '+ Add another analysis view', wait for card + initial diagram, return new card."""
        count_before = self.page.locator("#sankey-cards-container .sankey-card").count()
        with self.page.expect_response(lambda r: "sankey-form" in r.url):
            self.page.locator(".btn-add-sankey").click()
        # Wait for the new card to appear in the DOM
        self.page.locator("#sankey-cards-container .sankey-card").nth(count_before).wait_for(
            state="visible", timeout=10000)
        new_card = self.cards()[-1]
        new_card.wait_for_diagram_update()
        return new_card

    def onboarding_banner_visible(self) -> bool:
        banner = self.page.locator("#sankey-onboarding-banner")
        return banner.is_visible()

    def dismiss_onboarding_banner(self) -> None:
        self.page.locator("#sankey-onboarding-banner .onboarding-dismiss").click()
        self.page.locator("#sankey-onboarding-banner").wait_for(state="hidden")
