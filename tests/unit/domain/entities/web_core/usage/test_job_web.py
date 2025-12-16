"""Unit tests for JobWeb entity."""
from typing import List

import pytest
from efootprint.all_classes_in_order import SERVICE_CLASSES
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.job import Job, GPUJob
from efootprint.builders.services.web_application import WebApplication

from model_builder.domain.entities.web_core.usage.job_web import JobWeb
from tests.unit.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot


class _StubService:
    def __init__(self, name: str, efootprint_id: str):
        self.name = name
        self.efootprint_id = efootprint_id


class _StubServer:
    def __init__(self, name: str, efootprint_id: str, installed_services: List):
        self.name = name
        self.efootprint_id = efootprint_id
        self.installed_services = installed_services


class _FakeModelWeb:
    """Lightweight stand-in used to generate deterministic snapshot data."""

    def __init__(self):
        service = _StubService("service", "service_efootprint_id")
        self._servers = [_StubServer("server", "server_efootprint_id", [service])]
        # Mark all service classes as present to expose all compatible job classes in the form
        self.response_objs = {service_class.__name__: {} for service_class in SERVICE_CLASSES}

    @property
    def servers(self):
        return self._servers

    @property
    def services(self):
        return []

    def get_web_objects_from_efootprint_type(self, _):
        return []

    def get_efootprint_objects_from_efootprint_type(self, _):
        return []


class TestJobWeb:
    """Tests for JobWeb-specific behavior."""

    # --- links_to ---

    def test_links_to_points_to_server_web_id(self, minimal_model_web):
        """links_to should point to the job's server."""
        job_web = minimal_model_web.jobs[0]

        assert job_web.links_to == job_web.server.web_id

    # --- get_creation_prerequisites ---

    def test_get_creation_prerequisites_requires_server(self):
        """Creating a job without any server should raise an explicit error."""
        fake_model_web = _FakeModelWeb()
        fake_model_web._servers = []  # type: ignore[attr-defined]

        with pytest.raises(ValueError):
            JobWeb.get_creation_prerequisites(fake_model_web)

    def test_get_creation_prerequisites_include_services_and_direct_calls(self, minimal_model_web):
        """Prerequisites should include installed services and direct server call options."""
        server = minimal_model_web.servers[0]
        service = WebApplication.from_defaults("Test Service", server=server.modeling_obj)
        added_service = minimal_model_web.add_new_efootprint_object_to_system(service)

        prereqs = JobWeb.get_creation_prerequisites(minimal_model_web)
        intermediate = prereqs["intermediate_by_parent"][server.efootprint_id]

        assert prereqs["parents"] == minimal_model_web.servers
        assert Job in prereqs["available_classes"] and GPUJob in prereqs["available_classes"]

        # Service is listed as an intermediate option
        assert added_service.efootprint_id in [elt.efootprint_id for elt in intermediate["items"]]
        # Direct call option present for CPU servers
        assert {"id": "direct_server_call", "label": "direct call to server", "type_classes": [Job]} in \
            intermediate["extra_options"]
        # Service-compatible job classes are mapped
        assert added_service.efootprint_id in prereqs["type_classes_by_intermediate"]
        assert prereqs["type_classes_by_intermediate"][added_service.efootprint_id] != []

    def test_get_creation_prerequisites_for_gpu_server_adds_gpu_direct_call(self, minimal_model_web):
        """GPU servers should expose GPU-specific direct call options."""
        storage = Storage.from_defaults("GPU Storage")
        gpu_server = GPUServer.from_defaults("GPU Server", storage=storage)
        minimal_model_web.add_new_efootprint_object_to_system(storage)
        added_gpu_server = minimal_model_web.add_new_efootprint_object_to_system(gpu_server)

        prereqs = JobWeb.get_creation_prerequisites(minimal_model_web)
        gpu_options = prereqs["intermediate_by_parent"][added_gpu_server.efootprint_id]["extra_options"]

        assert {"id": "direct_server_call_gpu", "label": "direct call to GPU server", "type_classes": [GPUJob]} in \
            gpu_options

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        job_snapshot_model_web = _build_job_snapshot_model_web()
        assert_creation_context_matches_snapshot(JobWeb, model_web=job_snapshot_model_web)


def _build_job_snapshot_model_web():
    """Create a deterministic mock ModelWeb mirroring legacy snapshot setup."""
    from copy import deepcopy
    from dataclasses import dataclass
    from unittest.mock import MagicMock

    @dataclass
    class _MockModelingObjectWeb:
        id: str
        name: str

    basic_model_web = MagicMock()
    option1 = _MockModelingObjectWeb(id="efootprint_id1", name="option1")
    option2 = _MockModelingObjectWeb(id="efootprint_id2", name="option2")
    basic_model_web.get_efootprint_objects_from_efootprint_type.return_value = [option1, option2]

    model_web = deepcopy(basic_model_web)

    server = MagicMock()
    server.name = "server"
    server.efootprint_id = "server_efootprint_id"
    service = MagicMock()
    service.name = "service"
    service.efootprint_id = "service_efootprint_id"
    server.installed_services = [service]

    model_web.servers = [server]
    model_web.response_objs = {service_class.__name__: service_class for service_class in SERVICE_CLASSES}

    return model_web
