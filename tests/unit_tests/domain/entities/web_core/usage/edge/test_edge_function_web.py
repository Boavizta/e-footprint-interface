"""Unit tests for EdgeFunctionWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from model_builder.domain.entities.web_core.usage.edge.edge_function_web import EdgeFunctionWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.snapshot_model_webs import build_basic_model_web


def _build_edge_function_web():
    modeling_obj = SimpleNamespace(id="edge-fn", class_as_simple_str="EdgeFunction", name="edge-fn")
    return EdgeFunctionWeb(modeling_obj, MagicMock())


class TestEdgeFunctionWeb:
    """Tests for EdgeFunctionWeb-specific behavior."""

    # --- child_object_types_str ---

    def test_child_object_types_str_includes_edge_and_server_needs(self):
        """Edge functions should expose both edge device and server recurrent needs."""
        edge_function = _build_edge_function_web()
        assert edge_function.child_object_types_str == ["RecurrentEdgeDeviceNeedBase", "RecurrentServerNeed"]

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_basic_model_web()
        assert_creation_context_matches_snapshot(EdgeFunctionWeb, model_web=model_web)
