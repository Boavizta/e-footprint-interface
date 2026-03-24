import tomllib
import unittest
from pathlib import Path

from e_footprint_interface import __version__


def get_version_from_pyproject():
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as file:
        pyproject = tomllib.load(file)
    return pyproject["tool"]["poetry"]["version"]


class TestVersion(unittest.TestCase):
    def test_version_is_up_to_date(self):
        self.assertEqual(get_version_from_pyproject(), __version__)
