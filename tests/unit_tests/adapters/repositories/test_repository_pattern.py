"""Tests demonstrating the new repository pattern for ModelWeb.

These tests__old show how to use the InMemorySystemRepository to test ModelWeb
without requiring Django session infrastructure.
"""
from model_builder.adapters.repositories import InMemorySystemRepository
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

        repository.save_system_data(data)

        assert repository.has_system_data()
        assert repository.get_system_data() == data

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
        model_web.update_system_data_with_up_to_date_calculated_attributes()

        # Repository should have updated data
        saved_data = repository.get_system_data()
        assert saved_data is not None
        assert "efootprint_version" in saved_data

    def test_repository_interface_contract(self):
        """Verify that InMemorySystemRepository implements ISystemRepository correctly."""
        repository = InMemorySystemRepository()

        # Should implement all abstract methods
        assert isinstance(repository, ISystemRepository)
        assert hasattr(repository, 'get_system_data')
        assert hasattr(repository, 'save_system_data')
        assert hasattr(repository, 'has_system_data')
        assert hasattr(repository, 'clear')


if __name__ == "__main__":
    unittest.main()
