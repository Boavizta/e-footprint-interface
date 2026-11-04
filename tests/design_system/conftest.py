"""Design-system checks run against a live server and only report: they never block a merge.

Opt-in so `pytest tests --ignore=tests/e2e` stays server-free:
    DESIGN_SYSTEM_CHECKS=1 poetry run pytest tests/design_system --base-url http://localhost:8000
"""
import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("DESIGN_SYSTEM_CHECKS") == "1":
        return
    skip = pytest.mark.skip(reason="Set DESIGN_SYSTEM_CHECKS=1 to run design-system checks (needs a running server)")
    for item in items:
        if "tests/design_system/" in str(item.fspath):
            item.add_marker(skip)
