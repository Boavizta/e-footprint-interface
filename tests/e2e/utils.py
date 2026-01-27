"""E2E test utilities."""
from playwright.sync_api import Page, Locator
from collections.abc import Mapping


def click_and_wait_for_htmx(page: Page, locator: Locator):
    """Click an HTMX element and wait for its request to complete."""
    # Get the HTMX URL from the element
    hx_url = locator.get_attribute("hx-get") or locator.get_attribute("hx-post")
    if hx_url:
        with page.expect_response(lambda r: hx_url in r.url):
            locator.click()
    else:
        locator.click()


def add_only_update(target: dict, source: Mapping) -> dict:
    """
    Recursively update `target` with values from `source`,
    adding missing keys only and never overriding existing ones.

    Mutates and returns `target`.
    """
    for key, value in source.items():
        if key not in target:
            target[key] = value
        else:
            if isinstance(target[key], Mapping) and isinstance(value, Mapping):
                add_only_update(target[key], value)
            # else: existing non-dict value wins → do nothing
    return target


EMPTY_SYSTEM_DICT = {
        "efootprint_version": "14.1.0",
        "System": {
            "uuid-system-1": {
                "name": "My system",
                "id": "uuid-system-1",
                "usage_patterns": [],
                "edge_usage_patterns": [],
                }
        }
    }
