"""Unit tests for ExternalAPIWeb entity."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.constants.units import u

from model_builder.domain.entities.web_builders.services.external_api_web import ExternalAPIWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.snapshot_model_webs import build_basic_model_web


class _FakeCapacity:
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def __truediv__(self, other):
        return _FakeQuantity(self._value / other.value)


class _FakeQuantity:
    def __init__(self, magnitude):
        self._magnitude = magnitude

    def to(self, _):
        return self

    @property
    def magnitude(self):
        return self._magnitude


class TestExternalAPIWeb:
    """Tests for ExternalAPIWeb-specific behavior."""

    # --- get_htmx_form_config ---

    def test_get_htmx_form_config_targets_server_list(self):
        """HTMX config should append to the server list."""
        assert ExternalAPIWeb.get_htmx_form_config({}) == {"hx_target": "#external-api-list", "hx_swap": "beforeend"}

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_basic_model_web()
        assert_creation_context_matches_snapshot(ExternalAPIWeb, model_web=model_web, object_type="ExternalAPI")
