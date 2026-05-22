"""Tests for ModelWeb.has_edge_objects.

Drives real ModelWeb instances (via `minimal_model_web`) so the iteration logic — not a
monkey-patched lookup — is exercised end-to-end. This catches typos in
EDGE_EFOOTPRINT_CLASS_NAMES that a stub-based lookup would silently mask.
"""
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup


class TestHasEdgeObjects:
    def test_returns_false_on_web_only_model(self, minimal_model_web):
        assert minimal_model_web.has_edge_objects is False

    def test_returns_true_after_adding_edge_device(self, minimal_model_web):
        minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Sensor", components=[]))
        assert minimal_model_web.has_edge_objects is True

    def test_returns_true_after_adding_edge_device_group(self, minimal_model_web):
        minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Group"))
        assert minimal_model_web.has_edge_objects is True
