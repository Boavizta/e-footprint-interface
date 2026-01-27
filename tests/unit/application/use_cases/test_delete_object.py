"""Unit tests for DeleteObjectUseCase.

These tests focus on the generic orchestration behavior of the use case,
not object-specific deletion rules (those belong in entity tests).
"""
from unittest.mock import patch, MagicMock

from model_builder.application.use_cases.delete_object import (
    DeleteObjectUseCase, DeleteObjectInput, DeleteCheckResult)


class TestDeleteObjectUseCase:
    """Tests for DeleteObjectUseCase orchestration behavior."""

    # --- check_can_delete ---

    def test_check_can_delete_returns_delete_check_result(self, minimal_model_web):
        """check_can_delete returns a DeleteCheckResult."""
        use_case = DeleteObjectUseCase(minimal_model_web)

        result = use_case.check_can_delete(minimal_model_web.servers[0].efootprint_id)

        assert isinstance(result, DeleteCheckResult)

    def test_check_can_delete_blocked_object_returns_container_names(self, minimal_model_web):
        """When blocked, result includes blocking container names as strings."""
        use_case = DeleteObjectUseCase(minimal_model_web)
        uj = minimal_model_web.usage_journeys[0]

        result = use_case.check_can_delete(uj.efootprint_id)

        assert result.can_delete is False
        assert len(result.blocking_containers) > 0
        assert all(isinstance(name, str) for name in result.blocking_containers)

    def test_check_can_delete_uses_class_can_delete_hook(self, minimal_model_web):
        """Uses web class can_delete hook when available."""
        use_case = DeleteObjectUseCase(minimal_model_web)
        server = minimal_model_web.servers[0]

        result = use_case.check_can_delete(server.efootprint_id)

        # ServerWeb.can_delete checks jobs specifically, not generic containers
        assert result.can_delete is False
        assert "Test Job" in result.blocking_containers

    # --- execute ---

    def test_execute_returns_deleted_object_info(self, minimal_model_web):
        """execute returns info about the deleted object."""
        use_case = DeleteObjectUseCase(minimal_model_web)
        up = minimal_model_web.usage_patterns[0]

        output = use_case.execute(DeleteObjectInput(object_id=up.efootprint_id))

        assert output.deleted_object_name == up.name
        assert output.deleted_object_type == "UsagePattern"

    def test_execute_persists_deletion_to_repository(self, minimal_repository, minimal_model_web):
        """execute persists the deletion to the repository."""
        use_case = DeleteObjectUseCase(minimal_model_web)
        up_id = minimal_model_web.usage_patterns[0].efootprint_id

        use_case.execute(DeleteObjectInput(object_id=up_id))

        updated_data = minimal_repository.get_system_data()
        assert up_id not in updated_data.get("UsagePattern", {})

    def test_execute_calls_pre_delete_hook_when_defined(self, minimal_model_web):
        """execute calls pre_delete hook on web class when defined."""
        from model_builder.domain.entities.web_core.usage.usage_pattern_web import UsagePatternWeb

        use_case = DeleteObjectUseCase(minimal_model_web)
        up = minimal_model_web.usage_patterns[0]
        original_pre_delete = UsagePatternWeb.pre_delete

        # Wrap original to track calls while preserving behavior
        with patch.object(
            UsagePatternWeb, 'pre_delete',
            wraps=original_pre_delete
        ) as mock_pre_delete:
            use_case.execute(DeleteObjectInput(object_id=up.efootprint_id))

            mock_pre_delete.assert_called_once()
