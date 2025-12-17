"""E2E test utilities."""
from playwright.sync_api import Page, Locator


def click_and_wait_for_htmx(page: Page, locator: Locator):
    """Click an HTMX element and wait for its request to complete."""
    # Get the HTMX URL from the element
    page.wait_for_timeout(50)
    hx_url = locator.get_attribute("hx-get") or locator.get_attribute("hx-post")
    if hx_url:
        with page.expect_response(lambda r: hx_url in r.url):
            locator.click()
    else:
        locator.click()
