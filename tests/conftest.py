"""Pytest configuration and shared fixtures."""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source

# tests.narrate_collector writes what each test crossed, for the comprehension pages (specs/testing.md).
pytest_plugins = ["tests.fixtures.system_builders", "tests.narrate_collector"]

Source._use_name_as_id = True
