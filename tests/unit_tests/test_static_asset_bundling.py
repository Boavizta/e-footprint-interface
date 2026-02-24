import re
import unittest
from pathlib import Path

from tests.utils import test_rootdir


class TestStaticAssetBundling(unittest.TestCase):
    def test_result_charts_loaded_from_bundle(self):
        base_html = (test_rootdir / "../theme/templates/base.html").read_text(encoding="utf-8")
        self.assertIn("bundles/result_charts.js", base_html)
        self.assertNotIn("scripts/result_charts/", base_html)

    def test_no_unbundled_module_scripts_in_templates(self):
        repo_rootdir = (test_rootdir / "..").resolve()
        template_paths = list((repo_rootdir / "theme/templates").rglob("*.html")) + list(
            (repo_rootdir / "model_builder/templates").rglob("*.html")
        )
        self.assertGreater(len(template_paths), 0, "Expected to find HTML templates to scan")

        module_script_tags = []
        for template_path in template_paths:
            html = template_path.read_text(encoding="utf-8")
            module_script_tags.extend(
                re.findall(r"<script\b[^>]*\btype=[\"']module[\"'][^>]*>", html, flags=re.IGNORECASE)
            )

        self.assertGreater(
            len(module_script_tags),
            0,
            "Expected at least one <script type=\"module\"> tag in templates (result charts bundle).",
        )

        for tag in module_script_tags:
            # Enforce policy: module entrypoints must be bundled assets served via `{% static 'bundles/...' %}`.
            # This avoids un-hashed module imports being cached incorrectly in production.
            self.assertNotIn("scripts/", tag, f"Unbundled module script detected: {tag}")
            self.assertIn("bundles/", tag, f"Expected bundled module script, got: {tag}")
