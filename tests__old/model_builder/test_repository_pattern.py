"""Tests demonstrating the new repository pattern for ModelWeb.

These tests__old show how to use the InMemorySystemRepository to test ModelWeb
without requiring Django session infrastructure.
"""
import json
import os
import unittest

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.interfaces import ISystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb


class TestInMemoryRepository(unittest.TestCase):
    """Tests for the InMemorySystemRepository implementation."""

    def test_repository_starts_empty(self):
        """A new repository should have no system data."""
        repository = InMemorySystemRepository()
        self.assertFalse(repository.has_system_data())
        self.assertIsNone(repository.get_system_data())

    def test_repository_with_initial_data(self):
        """A repository can be initialized with data."""
        initial_data = {"System": {"sys-1": {"name": "Test System"}}}
        repository = InMemorySystemRepository(initial_data=initial_data)

        self.assertTrue(repository.has_system_data())
        self.assertEqual(repository.get_system_data()["System"]["sys-1"]["name"], "Test System")

    def test_initial_data_is_copied(self):
        """Initial data should be deep copied to avoid mutation."""
        initial_data = {"System": {"sys-1": {"name": "Test System"}}}
        repository = InMemorySystemRepository(initial_data=initial_data)

        # Mutate original data
        initial_data["System"]["sys-1"]["name"] = "Modified"

        # Repository should have original value
        self.assertEqual(repository.get_system_data()["System"]["sys-1"]["name"], "Test System")

    def test_save_and_retrieve(self):
        """Data can be saved and retrieved."""
        repository = InMemorySystemRepository()
        data = {"System": {"sys-1": {"name": "Test System"}}}

        repository.save_system_data(data)

        self.assertTrue(repository.has_system_data())
        self.assertEqual(repository.get_system_data(), data)

    def test_clear(self):
        """Clear should remove all data."""
        repository = InMemorySystemRepository(initial_data={"key": "value"})
        repository.clear()

        self.assertFalse(repository.has_system_data())
        self.assertIsNone(repository.get_system_data())


class TestModelWebWithRepository(unittest.TestCase):
    """Tests demonstrating ModelWeb working with ISystemRepository."""

    @classmethod
    def setUpClass(cls):
        """Load test system data once for all tests__old."""
        test_data_path = os.path.join(
            os.path.dirname(__file__),
            "default_system_data_with_calculated_attributes.json"
        )
        with open(test_data_path, "r") as f:
            cls.test_system_data = json.load(f)

    def test_model_web_accepts_repository(self):
        """ModelWeb should accept an ISystemRepository implementation."""
        repository = InMemorySystemRepository(initial_data=self.test_system_data)

        # This should work without Django sessions
        model_web = ModelWeb(repository)

        self.assertIsNotNone(model_web.system)
        self.assertIsNotNone(model_web.system_data)

    def test_model_web_saves_through_repository(self):
        """ModelWeb should save changes through the repository."""
        repository = InMemorySystemRepository(initial_data=self.test_system_data)
        model_web = ModelWeb(repository)

        # Get initial server count
        initial_server_count = len(model_web.servers)
        self.assertGreater(initial_server_count, 0, "Test data should have at least one server")

        # Trigger a save
        model_web.update_system_data_with_up_to_date_calculated_attributes()

        # Repository should have updated data
        saved_data = repository.get_system_data()
        self.assertIsNotNone(saved_data)
        self.assertIn("efootprint_version", saved_data)

    def test_repository_interface_contract(self):
        """Verify that InMemorySystemRepository implements ISystemRepository correctly."""
        repository = InMemorySystemRepository()

        # Should implement all abstract methods
        self.assertTrue(isinstance(repository, ISystemRepository))
        self.assertTrue(hasattr(repository, 'get_system_data'))
        self.assertTrue(hasattr(repository, 'save_system_data'))
        self.assertTrue(hasattr(repository, 'has_system_data'))
        self.assertTrue(hasattr(repository, 'clear'))


if __name__ == "__main__":
    unittest.main()
