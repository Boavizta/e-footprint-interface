"""Tests demonstrating the new repository pattern for ModelWeb.

These tests__old show how to use the InMemorySystemRepository to test ModelWeb
without requiring Django session infrastructure.
"""
from unittest.mock import MagicMock, patch

from e_footprint_interface import __version__ as interface_version
from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository
from model_builder.domain.interfaces import ISystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb


class TestInMemoryRepository:
    """Tests for the InMemorySystemRepository implementation."""

    def test_repository_starts_empty(self):
        """A new repository should have no system data."""
        repository = InMemorySystemRepository()
        assert not repository.has_system_data()
        assert repository.get_system_data() is None

    def test_repository_with_initial_data(self):
        """A repository can be initialized with data."""
        initial_data = {"System": {"sys-1": {"name": "Test System"}}}
        repository = InMemorySystemRepository(initial_data=initial_data)

        assert repository.has_system_data()
        assert repository.get_system_data()["System"]["sys-1"]["name"] == "Test System"

    def test_initial_data_is_copied(self):
        """Initial data should be deep copied to avoid mutation."""
        initial_data = {"System": {"sys-1": {"name": "Test System"}}}
        repository = InMemorySystemRepository(initial_data=initial_data)

        # Mutate original data
        initial_data["System"]["sys-1"]["name"] = "Modified"

        # Repository should have original value
        assert repository.get_system_data()["System"]["sys-1"]["name"] == "Test System"

    def test_save_and_retrieve(self):
        """Data can be saved and retrieved."""
        repository = InMemorySystemRepository()
        data = {"System": {"sys-1": {"name": "Test System"}}}

        repository.save_data(data)

        assert repository.has_system_data()
        assert repository.get_system_data() == data

    def test_interface_config_defaults_to_empty_dict(self):
        repository = InMemorySystemRepository()
        assert repository.interface_config == {}

    def test_save_merges_interface_config(self):
        repository = InMemorySystemRepository()
        repository.interface_config = {"sankey_diagrams": [{"id": "deadbeef"}]}

        repository.save_data({"System": {"sys-1": {"name": "Test System"}}})

        saved_data = repository.get_system_data()
        assert saved_data["interface_config"] == {"sankey_diagrams": [{"id": "deadbeef"}]}
        assert "efootprint_interface_version" in saved_data

    def test_save_interface_config_merges_metadata_without_replacing_system_data(self):
        repository = InMemorySystemRepository(initial_data={"System": {"sys-1": {"name": "Test System"}}})
        repository.interface_config = {"card_order": {"server-list": ["Server_a"]}}

        repository.save_interface_config()

        assert repository.get_system_data() == {
            "System": {"sys-1": {"name": "Test System"}},
            "interface_config": {"card_order": {"server-list": ["Server_a"]}},
            "efootprint_interface_version": interface_version,
        }

    def test_clear(self):
        """Clear should remove all data."""
        repository = InMemorySystemRepository(initial_data={"key": "value"})
        repository.clear()

        assert not repository.has_system_data()
        assert repository.get_system_data() is None


class TestModelWebWithRepository:
    """Tests demonstrating ModelWeb working with ISystemRepository."""
    def test_model_web_accepts_repository(self, minimal_system_data):
        """ModelWeb should accept an ISystemRepository implementation."""
        repository = InMemorySystemRepository(initial_data=minimal_system_data)

        # This should work without Django sessions
        model_web = ModelWeb(repository)

        assert model_web.system is not None
        assert model_web.system_data is not None

    def test_model_web_saves_through_repository(self, minimal_system_data):
        """ModelWeb should save changes through the repository."""
        repository = InMemorySystemRepository(initial_data=minimal_system_data)
        model_web = ModelWeb(repository)

        # Get initial server count
        initial_server_count = len(model_web.servers)
        assert initial_server_count > 0, "Test data should have at least one server"

        # Trigger a save
        model_web.persist_to_cache()

        # Repository should have updated data
        saved_data = repository.get_system_data()
        assert saved_data is not None
        assert "efootprint_version" in saved_data

    def test_model_web_supplies_canonical_and_inputs_only_recovery_payloads(self, minimal_system_data):
        from efootprint.api_utils.system_to_json import CALCULATION_GRAPH_KEY

        repository = InMemorySystemRepository(initial_data=minimal_system_data)
        model_web = ModelWeb(repository)
        raw_system = next(iter(model_web.response_objs["System"].values()))
        _ = raw_system.total_footprint
        repository.save_data = MagicMock()

        model_web.persist_to_cache()

        canonical_data = repository.save_data.call_args.args[0]
        recovery_data = repository.save_data.call_args.kwargs["recovery_data"]
        assert CALCULATION_GRAPH_KEY in canonical_data
        assert CALCULATION_GRAPH_KEY not in recovery_data
        assert "total_footprint" in canonical_data["System"][raw_system.id]
        assert "total_footprint" not in recovery_data["System"][raw_system.id]

        recovered = ModelWeb(InMemorySystemRepository(initial_data=recovery_data))
        recovered_system = next(iter(recovered.response_objs["System"].values()))
        assert recovered_system.total_footprint is not None

    def test_repository_interface_contract(self):
        """Verify that InMemorySystemRepository implements ISystemRepository correctly."""
        repository = InMemorySystemRepository()

        # Should implement all abstract methods
        assert isinstance(repository, ISystemRepository)
        assert hasattr(repository, 'get_system_data')
        assert hasattr(repository, 'save_data')
        assert hasattr(repository, 'save_interface_config')
        assert hasattr(repository, 'has_system_data')
        assert hasattr(repository, 'clear')


if __name__ == "__main__":
    unittest.main()


class FakeSession(dict):
    def __init__(self):
        super().__init__()
        self.session_key = "session-key"
        self.modified = False

    def save(self):
        pass


class TestSessionSystemRepositoryInterfaceConfigFallback:
    def test_interface_config_falls_back_to_session_when_cache_empty(self):
        session = FakeSession()
        session[SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY] = {"sankey_diagrams": [{"id": "deadbeef"}]}
        session[SessionSystemRepository.INTERFACE_VERSION_SESSION_KEY] = "1.0.0"
        repository = SessionSystemRepository(session)

        with patch("model_builder.adapters.repositories.session_system_repository.CacheBackend.get_with_source", return_value=(None, None)):
            assert repository.interface_config == {"sankey_diagrams": [{"id": "deadbeef"}]}

    def test_save_data_persists_interface_config_to_session(self):
        session = FakeSession()
        repository = SessionSystemRepository(session)
        repository.interface_config = {"sankey_diagrams": [{"id": "deadbeef"}]}
        canonical_data = {"System": {"sys-1": {"name": "Test System"}}, "calculation_graph": {}}
        recovery_data = {"System": {"sys-1": {"name": "Test System"}}}

        with patch("model_builder.adapters.repositories.session_system_repository.CacheBackend.set") as cache_set:
            repository.save_data(canonical_data, recovery_data=recovery_data)

        assert session[SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY] == {"sankey_diagrams": [{"id": "deadbeef"}]}
        assert session[SessionSystemRepository.INTERFACE_VERSION_SESSION_KEY]
        assert canonical_data["interface_config"] == recovery_data["interface_config"]
        assert canonical_data["efootprint_interface_version"] == recovery_data["efootprint_interface_version"]

        redis_write, postgres_write = cache_set.call_args_list
        assert redis_write.args == ("system_data:session-key:0", canonical_data)
        assert redis_write.kwargs["write_postgres"] is False
        assert "write_redis" not in redis_write.kwargs
        assert postgres_write.args == ("system_data:session-key:0", recovery_data)
        assert postgres_write.kwargs["write_redis"] is False
        assert "write_postgres" not in postgres_write.kwargs

    def test_save_interface_config_preserves_canonical_and_recovery_representations(self):
        session = FakeSession()
        repository = SessionSystemRepository(session)
        canonical_data = {
            "System": {"sys-1": {"name": "Test System", "total_footprint": {"value": 42}}},
            "calculation_graph": {"nodes": ["canonical-only"]},
        }
        recovery_data = {"System": {"sys-1": {"name": "Test System"}}}
        redis_cache = MagicMock()
        postgres_cache = MagicMock()
        redis_cache.get.return_value = canonical_data
        postgres_cache.get.return_value = recovery_data

        def get_cache(alias):
            return redis_cache if alias == CacheBackend.REDIS_CACHE_ALIAS else postgres_cache

        repository.interface_config = {"card_order": {"server-list": ["Server_a"]}}
        with patch.object(CacheBackend, "_get_cache", side_effect=get_cache):
            repository.save_interface_config()

        saved_canonical = redis_cache.set.call_args.args[1]
        saved_recovery = postgres_cache.set.call_args.args[1]
        assert saved_canonical["calculation_graph"] == {"nodes": ["canonical-only"]}
        assert saved_canonical["System"]["sys-1"]["total_footprint"] == {"value": 42}
        assert "calculation_graph" not in saved_recovery
        assert "total_footprint" not in saved_recovery["System"]["sys-1"]
        assert saved_canonical["interface_config"] == saved_recovery["interface_config"] == {
            "card_order": {"server-list": ["Server_a"]}
        }
        assert session[SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY] == saved_canonical["interface_config"]

    def test_clear_removes_interface_config_session_keys(self):
        session = FakeSession()
        session[SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY] = {"sankey_diagrams": [{"id": "deadbeef"}]}
        session[SessionSystemRepository.INTERFACE_VERSION_SESSION_KEY] = "1.0.0"
        repository = SessionSystemRepository(session)

        with patch("model_builder.adapters.repositories.session_system_repository.CacheBackend.delete"):
            repository.clear()

        assert SessionSystemRepository.INTERFACE_CONFIG_SESSION_KEY not in session
        assert SessionSystemRepository.INTERFACE_VERSION_SESSION_KEY not in session
