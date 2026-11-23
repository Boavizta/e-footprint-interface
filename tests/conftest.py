"""Pytest configuration and shared fixtures."""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source

# comprehension_harness.python.collector writes what each test crossed, for the comprehension pages (specs/testing.md);
# comprehension_harness.python.journey writes the screens a journey test walks (tests/e2e/journeys/).
pytest_plugins = ["tests.fixtures.system_builders", "comprehension_harness.python.collector",
                  "comprehension_harness.python.journey"]

Source._use_name_as_id = True
