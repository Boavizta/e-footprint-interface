"""LinkedIn feature video: exploring e-commerce impact repartition Sankeys."""

import os
import time
from pathlib import Path

from tests.e2e.pages import ModelBuilderPage
from tests.e2e.pages.sankey_page import SankeyPage

from communications.video.recorder import Demo, ROOT, import_model_quiet, run_video


LIBRARY_DIR = Path(os.environ.get("EF_LIBRARY_DIR", ROOT.parent / "e-footprint")).resolve()
MODEL = LIBRARY_DIR / "efootprint/modeling_templates/introductory/ecommerce.json"
NAME = "sankey_impact_repartition"


def configure_first_view(builder: ModelBuilderPage):
    """Set the opening diagram to total → phase → journeys → steps → hardware."""
    builder.open_result_panel()
    card = SankeyPage(builder).first_card()
    card.wait_for_diagram_update(timeout=120000)
    for label in ("Countries", "Category"):
        if card.analyse_by_chip_is_active(label):
            card.toggle_analyse_by_chip(label)
    builder.page.wait_for_timeout(500)
    assert card.aggregation_threshold() == 1
    active = {chip.inner_text() for chip in card._container.locator('.chip[data-type="analyse"].active').all()}
    assert active == {"Total impact", "Phase", "Usage journeys", "Steps / Functions", "Hardware"}


def setup(context):
    if not MODEL.is_file():
        raise FileNotFoundError(f"Demo model not found: {MODEL}. Set EF_LIBRARY_DIR to the paired library checkout.")
    import_model_quiet(context, MODEL, configure=configure_first_view)


def click_sankey_chip(d: Demo, card, chip_type: str, label: str):
    chip = card._container.locator(f'.chip[data-type="{chip_type}"]').filter(has_text=label)
    with d.page.expect_response(lambda response: "sankey-diagram" in response.url):
        d.click(chip, settle=0.2)
    card.wait_for_diagram_update(timeout=120000)
    d.pause(0.5)


def demo(d: Demo) -> float:
    page = d.page
    started = time.monotonic()
    page.goto("/model_builder/")
    builder = ModelBuilderPage(page)
    builder.canvas.wait_for(state="visible")
    trim_start = time.monotonic() - started + 0.25
    d.pause(0.8)

    d.caption("Impact repartition Sankeys: see where a system's footprint flows", hold=2.7)
    france = page.locator("[id*='UsagePattern']").filter(has_text="Daily shoppers in France").first
    us = page.locator("[id*='UsagePattern']").filter(has_text="Daily shoppers in the US").first
    d.move_to(france)
    d.move_to(us)
    d.caption("This e-commerce model has shopper patterns in France and the US.", hold=2.4)

    d.caption("Find the Sankey diagrams in Results.", hold=1.4)
    d.click(page.locator("#btn-open-panel-result"), settle=0.8)
    page.locator("#lineChart").wait_for(state="visible")
    sankey = SankeyPage(builder)
    first = sankey.first_card()
    first.wait_for_diagram_update(timeout=120000)
    d.smooth_scroll_to(first._container, block="start", settle=1.4)
    d.caption("Each column accounts for the full impact shown. Flow widths reveal hotspots.", hold=3.0)

    plot = first.plot_locator()
    d.smooth_scroll_to(plot, settle=1.1)
    d.caption("Hover over a node to inspect its impact and share.", hold=1.2)
    d.hover_sankey_node(plot, "Manufacturing", hold=1.6)
    d.hover_sankey_node(plot, "Shopping journey", occurrence=1, hold=1.6)
    d.hover_sankey_node(plot, "Check out", occurrence=1, hold=1.6)

    threshold = first._container.locator('[name="aggregation_threshold_percent"]')
    d.smooth_scroll_to(threshold, settle=0.8)
    d.move_to(threshold)
    d.caption("At 1%, smaller contributors are grouped together.", hold=2.1)
    with page.expect_response(lambda response: "sankey-diagram" in response.url):
        d.set_range_to_minimum(threshold)
    assert first.aggregation_threshold() == 0
    d.caption("At 0%, every node is visible.", hold=1.9)
    plot = first.plot_locator()
    d.smooth_scroll_to(plot, settle=0.9)
    d.hover_sankey_node(plot, "Product database ser", hold=1.7)

    d.hover_sankey_node(plot, "Default laptop", hold=1.8)
    d.caption("Laptops dominate this view. We can focus on the rest of the system.", hold=2.9)
    d.smooth_scroll_to(first._container.locator(".advanced-toggle"), settle=0.8)
    d.click(first._container.locator(".advanced-toggle"), settle=0.5)
    d.caption("Exclude Devices in Advanced options.", hold=1.6)
    click_sankey_chip(d, first, "exclude", "Device")
    plot = first.plot_locator()
    d.smooth_scroll_to(plot, settle=1.0)
    d.hover_sankey_node(plot, "Product database ser", hold=2.2)

    d.caption("Add another Sankey to examine a different breakdown.", hold=1.8)
    add_button = page.locator(".btn-add-sankey")
    d.smooth_scroll_to(add_button, settle=1.0)
    count = len(sankey.cards())
    with page.expect_response(lambda response: "sankey-form" in response.url):
        d.click(add_button, settle=0.3)
    page.locator("#sankey-cards-container .sankey-card").nth(count).wait_for(state="visible")
    second = sankey.cards()[-1]
    second.wait_for_diagram_update(timeout=120000)
    d.smooth_scroll_to(second._container, block="start", settle=1.0)
    d.caption("This view follows impact through phase, country, category and hardware.", hold=2.6)
    for label in ("Usage journeys", "Steps / Functions"):
        click_sankey_chip(d, second, "analyse", label)

    plot = second.plot_locator()
    d.smooth_scroll_to(plot, settle=1.1)
    d.hover_sankey_node(plot, "Manufacturing", hold=0.6)
    d.caption("The two patterns have the same volumes, so manufacturing impact is nearly equal.", hold=2.4)
    d.hover_sankey_node(plot, "France", occurrence=0, hold=1.4)
    d.hover_sankey_node(plot, "United States", occurrence=0, hold=1.4)

    d.hover_sankey_node(plot, "Use", hold=0.6)
    d.caption("Use-phase impact is much higher in the US because its electricity is more carbon-intensive.", hold=2.5)
    d.hover_sankey_node(plot, "France", occurrence=1, hold=1.4)
    d.hover_sankey_node(plot, "United States", occurrence=1, hold=1.5)

    d.caption("Stack Sankeys to analyse a system from different angles.", hold=2.4)
    export_link = page.locator('a[href="download-json/"]')
    d.smooth_scroll_to(export_link, block="start", settle=1.2)
    d.move_to(export_link)
    d.caption("These views travel with the exported JSON, ready to share.", hold=2.8)
    d.caption("", hold=0.3)
    d.pause(0.4)
    return trim_start


if __name__ == "__main__":
    print(run_video(NAME, demo, setup_fn=setup))
