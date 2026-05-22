"""Tests for ModelWeb.has_edge_objects."""
from unittest.mock import MagicMock

from model_builder.domain.entities.web_core.model_web import ModelWeb


def _make_stub_with_objects(objects_by_type: dict):
    """Build a bare ModelWeb whose get_web_objects_from_efootprint_type returns the configured lists."""
    model_web = ModelWeb.__new__(ModelWeb)
    model_web.get_web_objects_from_efootprint_type = lambda name: objects_by_type.get(name, [])
    return model_web


class TestHasEdgeObjects:
    def test_returns_false_on_web_only_model(self, minimal_model_web):
        assert minimal_model_web.has_edge_objects is False

    def test_returns_true_with_only_edge_usage_pattern(self):
        model_web = _make_stub_with_objects({"EdgeUsagePattern": [MagicMock()]})
        assert model_web.has_edge_objects is True

    def test_returns_true_with_only_edge_device(self):
        model_web = _make_stub_with_objects({"EdgeDevice": [MagicMock()]})
        assert model_web.has_edge_objects is True

    def test_returns_true_for_mixed_system_with_recurrent_server_need_bridge(self):
        model_web = _make_stub_with_objects({
            "EdgeUsagePattern": [MagicMock()],
            "EdgeDevice": [MagicMock()],
            "RecurrentServerNeed": [MagicMock()],
        })
        assert model_web.has_edge_objects is True
