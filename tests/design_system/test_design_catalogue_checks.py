"""Accessibility scan and screenshot of the live /design catalogue.

The catalogue renders the real tokens and components, so checking it checks the design system.
"""
from pathlib import Path

from playwright.sync_api import Page

REPO_ROOT = Path(__file__).resolve().parents[2]
AXE_SCRIPT = REPO_ROOT / "node_modules" / "axe-core" / "axe.min.js"
SCREENSHOT_DIR = REPO_ROOT / "tests" / "design_system" / "screenshots"


def test_design_catalogue_has_no_serious_accessibility_violations(page: Page, base_url):
    page.goto(f"{base_url}/design/")
    page.add_script_tag(path=str(AXE_SCRIPT))
    results = page.evaluate("axe.run(document, {runOnly: ['wcag2a', 'wcag2aa']})")
    violations = [v for v in results["violations"] if v["impact"] in ("serious", "critical")]
    report = "\n".join(
        f"- {v['id']} ({v['impact']}): {v['help']} — {len(v['nodes'])} element(s)" for v in violations)
    assert not violations, f"WCAG AA violations on /design:\n{report}"


def test_capture_design_catalogue_screenshot(page: Page, base_url):
    """Full-page capture uploaded as a CI artifact, so a reviewer can eyeball visual changes."""
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{base_url}/design/")
    page.wait_for_load_state("networkidle")
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    page.screenshot(path=str(SCREENSHOT_DIR / "design-catalogue.png"), full_page=True)
