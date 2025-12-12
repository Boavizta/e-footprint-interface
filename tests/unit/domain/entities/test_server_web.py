"""Unit tests for ServerWeb entity."""
from unittest.mock import MagicMock

from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.server import Server
from efootprint.builders.services.web_application import WebApplication

from model_builder.domain.entities.web_core.hardware.server_web import ServerWeb
from tests.unit.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot


class TestServerWeb:
    """Tests for ServerWeb-specific behavior."""

    # --- can_delete ---

    def test_can_delete_blocked_by_jobs(self, minimal_model_web):
        """Server with jobs cannot be deleted - jobs block deletion."""
        server_web = minimal_model_web.servers[0]
        assert len(server_web.jobs) > 0

        can_delete, blocking_names = ServerWeb.can_delete(server_web)

        assert can_delete is False
        assert blocking_names == [job.name for job in server_web.jobs]

    def test_can_delete_allowed_without_jobs(self, minimal_model_web):
        """Server without jobs can be deleted."""
        storage = Storage.from_defaults("Unused Storage")
        server = Server.from_defaults("Unused Server", storage=storage)
        minimal_model_web.add_new_efootprint_object_to_system(storage)
        added_server = minimal_model_web.add_new_efootprint_object_to_system(server)

        can_delete, blocking_names = ServerWeb.can_delete(added_server)

        assert can_delete is True
        assert blocking_names == []

    # --- self_delete ---

    def test_self_delete_cascades_to_installed_services(self, minimal_model_web):
        """When a server is deleted, its installed services are also deleted."""
        storage = Storage.from_defaults("Service Test Storage")
        server = Server.from_defaults("Service Test Server", storage=storage)
        minimal_model_web.add_new_efootprint_object_to_system(storage)
        server_web = minimal_model_web.add_new_efootprint_object_to_system(server)

        service = WebApplication.from_defaults("Test Service", server=server)
        added_service = minimal_model_web.add_new_efootprint_object_to_system(service)
        service_id = added_service.efootprint_id

        server_web.self_delete()

        assert service_id not in minimal_model_web.flat_efootprint_objs_dict

    # --- pre_create ---

    def test_pre_create_creates_storage_and_adds_reference_to_form_data(self, minimal_model_web):
        """pre_create creates storage and adds its ID to form data with clean key.

        Note: Hooks now receive pre-parsed form data (from adapter layer).
        The _parsed_storage key contains already-parsed storage form data.
        """
        # Pre-parsed storage data (as would come from parse_form_data_with_nested)
        parsed_storage = {"name": "New Storage", "type_object_available": "Storage"}
        form_data = {
            "name": "New Server",
            "type_object_available": "BoaviztaCloudServer",
            "_parsed_storage": parsed_storage,
        }
        initial_storage_count = len(minimal_model_web.storages)

        result = ServerWeb.pre_create(form_data, minimal_model_web)

        # Storage created
        assert len(minimal_model_web.storages) == initial_storage_count + 1
        # Form data modified with clean key (no prefix)
        assert "storage" in result
        # Reference points to valid storage
        assert result["storage"] in minimal_model_web.flat_efootprint_objs_dict

    # --- pre_edit ---

    def test_pre_edit_updates_storage(self, minimal_model_web):
        """pre_edit updates the server's storage object.

        Note: Hooks now receive pre-parsed form data (from adapter layer).
        The _parsed_storage key contains already-parsed storage form data.
        """
        server_web = minimal_model_web.servers[0]
        storage = server_web.storage
        new_name = "Updated Storage Name"

        # Pre-parsed storage data (as would come from parse_form_data_with_nested)
        parsed_storage = {"storage_id": storage.efootprint_id, "name": new_name}
        form_data = {"_parsed_storage": parsed_storage}

        ServerWeb.pre_edit(form_data, server_web, minimal_model_web)

        assert storage.name == new_name

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self, minimal_model_web):
        """Creation context form structure matches reference snapshot."""
        # ServerBase is the object_type used in forms (not Server which is a concrete class)
        assert_creation_context_matches_snapshot(ServerWeb, model_web=MagicMock(), object_type="ServerBase")

    # --- generate_object_edition_context ---

    def test_generate_object_edition_context_includes_storage(self, minimal_model_web):
        """Edition context includes both server and storage data."""
        from model_builder.adapters.forms.form_context_builder import FormContextBuilder

        server_web = minimal_model_web.servers[0]
        form_builder = FormContextBuilder(minimal_model_web)
        context = form_builder.build_edition_context(server_web)

        assert context["object_to_edit"] == server_web
        assert context["storage_to_edit"] == server_web.storage
        assert "storage_form_fields" in context
