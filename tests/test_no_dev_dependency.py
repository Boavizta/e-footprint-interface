import re
import unittest
from pathlib import Path


class TestNoDevDependency(unittest.TestCase):
    def test_no_active_develop_true_in_pyproject(self):
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        for line in pyproject_path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            self.assertFalse(
                re.search(r"\bdevelop\s*=\s*true\b", stripped),
                f"Active 'develop = true' dependency found in pyproject.toml: {line!r}. "
                "Revert to the published package version before committing.",
            )
