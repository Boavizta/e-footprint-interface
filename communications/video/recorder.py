"""Reusable Playwright recorder for captioned interface demos.

Adapted from Clémence's September 2026 demo video kit in the workspace.
The local Django server and Playwright Chromium are the only recording targets.
"""

import json
import os
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent / "output"
BASE_URL = os.environ.get("EF_BASE_URL", "http://127.0.0.1:8000")
CHROMIUM = os.environ.get("PW_CHROMIUM")
VIDEO_SIZE = {"width": 1440, "height": 900}

OVERLAY_JS = """
(() => {
  const install = () => {
    if (!document.body || document.getElementById('__democursor')) return;
    const cursor = document.createElement('div');
    cursor.id = '__democursor';
    cursor.style.cssText = 'position:fixed;top:-50px;left:-50px;width:22px;height:22px;' +
      'border-radius:50%;background:rgba(37,99,235,.30);border:2.5px solid rgba(37,99,235,.95);' +
      'z-index:2147483647;pointer-events:none;transform:translate(-50%,-50%);' +
      'box-shadow:0 1px 6px rgba(0,0,0,.35);';
    document.body.appendChild(cursor);
    const caption = document.createElement('div');
    caption.id = '__democaption';
    caption.style.cssText = 'position:fixed;bottom:26px;left:50%;transform:translateX(-50%);' +
      'max-width:76%;padding:10px 22px;border-radius:12px;background:rgba(17,24,39,.90);' +
      'color:#fff;font:600 19px/1.35 system-ui,sans-serif;z-index:2147483646;' +
      'pointer-events:none;display:none;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,.4);';
    document.body.appendChild(caption);
    document.addEventListener('mousemove', event => {
      cursor.style.left = event.clientX + 'px'; cursor.style.top = event.clientY + 'px';
    }, true);
    document.addEventListener('mousedown', () => {
      cursor.style.width = '32px'; cursor.style.height = '32px';
      cursor.style.background = 'rgba(234,88,12,.45)';
    }, true);
    document.addEventListener('mouseup', () => {
      cursor.style.width = '22px'; cursor.style.height = '22px';
      cursor.style.background = 'rgba(37,99,235,.30)';
    }, true);
  };
  window.__setCaption = text => {
    const caption = document.getElementById('__democaption');
    if (!caption) return;
    caption.textContent = text || '';
    caption.style.display = text ? 'block' : 'none';
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
  new MutationObserver(install).observe(document.documentElement, {childList: true, subtree: false});
})();
"""


class Demo:
    """Human-paced interaction helpers for the recorded page."""

    def __init__(self, page):
        self.page = page
        self.x, self.y = 40, 40

    @staticmethod
    def pause(seconds: float):
        time.sleep(seconds)

    def caption(self, text: str, hold: float = 1.5):
        self.page.evaluate("text => window.__setCaption(text)", text)
        self.pause(hold)

    def glide(self, x: float, y: float, duration: float = 0.55):
        self.page.mouse.move(self.x, self.y)
        self.page.mouse.move(x, y, steps=max(12, int(duration * 60)))
        self.x, self.y = x, y

    def move_to(self, locator):
        locator.scroll_into_view_if_needed()
        self.pause(0.2)
        box = locator.bounding_box()
        if box is None:
            raise RuntimeError("Target has no visible bounding box")
        self.glide(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self.pause(0.2)

    def click(self, locator, settle: float = 0.8):
        self.move_to(locator)
        self.page.mouse.down()
        self.pause(0.12)
        self.page.mouse.up()
        self.pause(settle)

    def smooth_scroll_to(self, locator, block: str = "center", settle: float = 1.0):
        locator.evaluate("(el, block) => el.scrollIntoView({behavior:'smooth', block})", block)
        self.pause(settle)

    def set_range_to_minimum(self, locator, settle: float = 0.8):
        """Drag a range thumb to its minimum so the change is visible on camera."""
        self.move_to(locator)
        box = locator.bounding_box()
        x0 = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        self.page.mouse.move(x0, y)
        self.page.mouse.down()
        self.page.mouse.move(box["x"] + 2, y, steps=24)
        self.page.mouse.up()
        self.x, self.y = box["x"] + 2, y
        self.pause(settle)

    def hover_sankey_node(self, plot, label: str, occurrence: int = 0, hold: float = 1.4):
        """Hover a rendered ECharts Sankey node by its payload label.

        Repeated labels (for example France under Manufacturing and Use) are selected
        by their payload order. Use the chart's actual layout rather than fixed pixels.
        """
        payload = json.loads(plot.get_attribute("data-sankey"))
        matches = [node for node in payload["nodes"] if node["label"].startswith(label)]
        if len(matches) <= occurrence:
            raise LookupError(f"Sankey node {label!r} occurrence {occurrence} not found")
        name_key = matches[occurrence]["name_key"]
        layout = plot.evaluate("""(el, key) => {
          const chart = el.__sankeyChart;
          const data = chart.getModel().getSeriesByIndex(0).getData();
          for (let i = 0; i < data.count(); i++) {
            if (data.getName(i) === key) return data.getItemLayout(i);
          }
          return null;
        }""", name_key)
        if not layout:
            raise LookupError(f"Rendered Sankey node {label!r} not found")
        box = plot.bounding_box()
        x = box["x"] + payload["layout"]["left_padding_px"] + layout["x"] + layout["dx"] / 2
        y = box["y"] + 10 + layout["y"] + layout["dy"] / 2
        self.glide(x, y)
        self.pause(hold)


def import_model_quiet(context, model_path: Path, configure=None):
    """Import and optionally configure the demo model before the recorded page opens."""
    from tests.e2e.pages import ModelBuilderPage

    page = context.new_page()
    try:
        page.goto(BASE_URL + "/model_builder/")
        builder = ModelBuilderPage(page)
        builder.canvas.wait_for(state="visible")
        builder.dismiss_template_picker_if_present()
        builder.import_json_file(str(model_path))
        if configure:
            configure(builder)
    finally:
        video = page.video
        page.close()
        if video:
            Path(video.path()).unlink(missing_ok=True)


def run_video(name: str, demo_fn, setup_fn=None, viewport=VIDEO_SIZE) -> Path:
    """Record one demo, trim its loading frames, and encode an H.264 MP4."""
    raw_dir = OUTPUT / "raw" / name
    raw_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else playwright.chromium.launch()
        context = browser.new_context(
            base_url=BASE_URL, viewport=viewport,
            record_video_dir=str(raw_dir), record_video_size=viewport,
        )
        context.add_init_script(OVERLAY_JS)
        context.add_init_script("localStorage.setItem('efootprint_onboarding_seen', 'true')")
        try:
            if setup_fn:
                setup_fn(context)
            page = context.new_page()
            try:
                trim_start = demo_fn(Demo(page))
            finally:
                video = page.video
                page.close()
                webm_path = Path(video.path()) if video else None
        finally:
            context.close()
            browser.close()

    if not webm_path or not webm_path.exists():
        raise RuntimeError("Playwright did not produce a video")
    output = OUTPUT / f"{name}.mp4"
    command = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{trim_start:.2f}",
               "-i", str(webm_path), "-c:v", "libx264", "-crf", "20",
               "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True)
    return output
