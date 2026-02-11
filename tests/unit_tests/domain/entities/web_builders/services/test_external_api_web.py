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
        assert ExternalAPIWeb.get_htmx_form_config({}) == {"hx_target": "#server-list", "hx_swap": "beforeend"}

    # --- pre_create ---

    def test_pre_create_creates_storage_and_server_and_sets_parent_id(self):
        """pre_create should create storage/server and set parent id in form data."""
        model_web = MagicMock()
        storage = MagicMock()
        server = SimpleNamespace(id="server-id")
        server_web = SimpleNamespace(modeling_obj=server)

        model_web.add_new_efootprint_object_to_system.side_effect = [storage, server_web]

        with patch("model_builder.domain.entities.web_builders.services.external_api_web.Storage.ssd") as ssd_mock, \
            patch("model_builder.domain.entities.web_builders.services.external_api_web.ServerTypes.serverless") as serverless_mock, \
            patch("model_builder.domain.entities.web_builders.services.external_api_web.GPUServer.from_defaults") as gpu_mock:
            ssd_mock.return_value = storage
            serverless_mock.return_value = "serverless"
            gpu_mock.return_value = server

            form_data = {"type_object_available": "GenAIModel", "name": "GenAI"}
            result = ExternalAPIWeb.pre_create(form_data, model_web)

        assert result["efootprint_id_of_parent_to_link_to"] == "server-id"
        assert "efootprint_id_of_parent_to_link_to" not in form_data
        assert ExternalAPIWeb._created_server_web == server_web

    def test_pre_create_rejects_unsupported_service_type(self):
        """Unsupported service types should raise an explicit error."""
        with pytest.raises(Exception):
            ExternalAPIWeb.pre_create({"type_object_available": "Other"}, MagicMock())

    # --- post_create ---

    def test_post_create_returns_server_reference(self):
        """post_create should return the created server web object."""
        server_web = SimpleNamespace(modeling_obj=SimpleNamespace(id="server-id"))
        ExternalAPIWeb._created_server_web = server_web

        result = ExternalAPIWeb.post_create(MagicMock(), {}, MagicMock())

        assert result == {"return_server_instead": True, "server_web": server_web}

    # --- handle_creation_error ---

    def test_handle_creation_error_adjusts_gpu_count_and_retries(self):
        """Insufficient capacity should adjust GPU count and re-add the service."""
        new_service = MagicMock()
        server = SimpleNamespace(
            name="Server",
            installed_services=[new_service],
            ram_per_gpu=_FakeCapacity(1.0),
        )
        server_web = SimpleNamespace(modeling_obj=server)
        ExternalAPIWeb._created_server_web = server_web

        model_web = MagicMock()

        error = InsufficientCapacityError(
            overloaded_object=server,
            capacity_type="ram",
            available_capacity=_FakeCapacity(1.0),
            requested_capacity=_FakeCapacity(2.0),
        )

        result = ExternalAPIWeb.handle_creation_error(error, {}, model_web)

        assert server.compute.value.magnitude == 3
        assert server.compute.value.units == u.gpu
        new_service.after_init.assert_called_once()
        model_web.add_new_efootprint_object_to_system.assert_called_once_with(new_service)
        assert result == new_service

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_basic_model_web()
        assert_creation_context_matches_snapshot(ExternalAPIWeb, model_web=model_web, object_type="ExternalAPI")
