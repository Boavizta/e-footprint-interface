"""Unit tests for RecurrentServerNeedWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from model_builder.domain.entities.web_core.usage.edge.recurrent_server_web import RecurrentServerNeedWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.snapshot_model_webs import build_basic_edge_devices_model_web


class TestRecurrentServerNeedWeb:
    """Tests for RecurrentServerNeedWeb-specific behavior."""

    # --- get_creation_prerequisites ---

    def test_get_creation_prerequisites_requires_edge_devices(self):
        """No edge devices should block recurrent server need creation."""
        model_web = MagicMock()
        model_web.edge_devices = []

        with pytest.raises(ValueError):
            RecurrentServerNeedWeb.get_creation_prerequisites(model_web)

    # --- links_to ---

    def test_links_to_includes_edge_device_and_job_links(self):
        """links_to should concatenate edge device and job links."""
        job1 = SimpleNamespace(links_to="server-1")
        job2 = SimpleNamespace(links_to="server-2")
        edge_device = SimpleNamespace(web_id="edge-device")
        modeling_obj = SimpleNamespace(
            id="rs-1",
            class_as_simple_str="RecurrentServerNeed",
            name="rs",
            jobs=[job1, job2],
            edge_device=edge_device,
        )

        web_obj = RecurrentServerNeedWeb(modeling_obj, MagicMock())

        assert web_obj.links_to == "edge-device|server-1|server-2"

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_basic_edge_devices_model_web()
        assert_creation_context_matches_snapshot(RecurrentServerNeedWeb, model_web=model_web)
