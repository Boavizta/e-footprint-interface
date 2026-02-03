"""Unit tests for RecurrentEdgeDeviceNeedBaseWeb entity."""
from unittest.mock import MagicMock

import pytest

from model_builder.domain.entities.web_core.usage.edge.recurrent_edge_device_need_base_web import (
    RecurrentEdgeDeviceNeedBaseWeb,
)
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.web_core.usage.snapshot_model_webs import (
    build_recurrent_edge_device_need_model_web,
)


class TestRecurrentEdgeDeviceNeedBaseWeb:
    """Tests for RecurrentEdgeDeviceNeedBaseWeb-specific behavior."""

    # --- get_creation_prerequisites ---

    def test_get_creation_prerequisites_requires_edge_devices(self):
        """No edge devices should block recurrent edge device need creation."""
        model_web = MagicMock()
        model_web.edge_devices = []

        with pytest.raises(ValueError):
            RecurrentEdgeDeviceNeedBaseWeb.get_creation_prerequisites(model_web)

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_recurrent_edge_device_need_model_web()
        assert_creation_context_matches_snapshot(RecurrentEdgeDeviceNeedBaseWeb, model_web=model_web)
