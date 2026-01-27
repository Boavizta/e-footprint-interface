"""Unit tests for CreateObjectUseCase.

These tests focus on the generic orchestration behavior of the use case,
not object-specific creation rules (those belong in entity tests).
"""
from unittest.mock import patch, MagicMock

import pytest

from model_builder.application.use_cases.create_object import (
    CreateObjectUseCase, CreateObjectInput, CreateObjectOutput)


class TestCreateObjectUseCase:
    """Tests for CreateObjectUseCase orchestration behavior."""

    # --- execute ---

    def test_execute_returns_create_object_output(self, minimal_repository):
        """execute returns a CreateObjectOutput with created object info."""
        use_case = CreateObjectUseCase(minimal_repository)
        form_data = {"name": "New Storage", "type_object_available": "Storage"}

        output = use_case.execute(CreateObjectInput(
            object_type="Storage",
            form_data=form_data
        ))

        assert isinstance(output, CreateObjectOutput)
        assert output.created_object_name == "New Storage"
        assert output.created_object_type == "Storage"

    # --- cleanup behavior ---

    def test_no_cleanup_when_pre_add_to_system_fails(self, minimal_repository):
        """When pre_add_to_system hook fails, should not try to delete non-added object.

        This tests the fix for the KeyError when self_delete was called on an object
        that was never added to response_objs.
        """
        from model_builder.domain.entities.web_core.hardware.storage_web import StorageWeb

        use_case = CreateObjectUseCase(minimal_repository)
        form_data = {"name": "Test Storage", "type_object_available": "Storage"}

        # Add a pre_add_to_system hook to StorageWeb that raises an error
        def failing_pre_add_to_system(obj, model_web):
            raise Exception("Simulated pre_add_to_system failure")

        with patch.object(StorageWeb, 'pre_add_to_system', failing_pre_add_to_system, create=True):
            with pytest.raises(Exception, match="Simulated pre_add_to_system failure"):
                use_case.execute(CreateObjectInput(
                    object_type="Storage",
                    form_data=form_data
                ))

        # If we get here without KeyError, the cleanup logic correctly skipped self_delete

    def test_cleanup_when_post_add_step_fails(self, minimal_repository, minimal_model_web):
        """When a step after add_new_efootprint_object_to_system fails, should cleanup the added object."""
        use_case = CreateObjectUseCase(minimal_repository)

        # Count objects before
        initial_count = len(minimal_model_web.flat_efootprint_objs_dict)

        form_data = {"name": "New Storage", "type_object_available": "Storage"}

        # Mock _link_to_parent to raise an error after object is added
        with patch.object(use_case, '_link_to_parent', side_effect=Exception("Simulated link failure")):
            with pytest.raises(Exception, match="Simulated link failure"):
                use_case.execute(CreateObjectInput(
                    object_type="Storage",
                    form_data=form_data,
                    parent_id="some-parent-id"  # Trigger linking attempt
                ))

        # Verify object was cleaned up - reload model to check
        from model_builder.domain.entities.web_core.model_web import ModelWeb
        model_web_after = ModelWeb(minimal_repository)
        assert len(model_web_after.flat_efootprint_objs_dict) == initial_count
