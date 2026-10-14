"""E2E test utilities."""
from playwright.sync_api import Page, Locator
from collections.abc import Mapping


def wait_for_htmx_idle(page: Page):
    """Wait for response swaps and descendant requests."""
    page.wait_for_function("() => document.querySelector('.htmx-request, .htmx-settling, .htmx-added') === null")


def click_and_wait_for_htmx(page: Page, locator: Locator):
    """Wait for an HTMX response; form saves also wait for accepted updates to settle."""
    # Already-swapped controls must be processed; pending reads may still be cancelled by this click.
    page.wait_for_function("() => document.querySelector('.htmx-settling, .htmx-added') === null")
    source = locator.evaluate_handle("""element => {
        if (element.hasAttribute('hx-get') || element.hasAttribute('hx-post')) return element;
        if (element.matches('button, input') && ['submit', 'image'].includes(element.type)) {
            return element.form || element;
        }
        return element;
    }""")
    try:
        hx_url = source.evaluate("element => element.getAttribute('hx-get') || element.getAttribute('hx-post')")
        if hx_url:
            with page.expect_response(lambda r: hx_url in r.url) as response:
                locator.click()
            if source.evaluate("element => element.hasAttribute('hx-post')"):
                response.value.finished()
                # Keep the original node when a form is replaced; unrelated pending reads may remain.
                page.wait_for_function("""source => !source.classList.contains('htmx-request')
                    && document.querySelector('.htmx-settling, .htmx-added') === null""", arg=source)
        else:
            locator.click()
    finally:
        source.dispose()


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
