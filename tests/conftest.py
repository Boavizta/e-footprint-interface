"""Pytest configuration and shared fixtures."""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source

pytest_plugins = ["tests.fixtures.system_builders"]

Source._use_name_as_id = True
