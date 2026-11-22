"""Pytest configuration and shared fixtures."""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source

# comprehension_harness.python.collector writes what each test crossed, for the comprehension pages (specs/testing.md).
pytest_plugins = ["tests.fixtures.system_builders", "comprehension_harness.python.collector"]

Source._use_name_as_id = True
