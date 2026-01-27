# Use Case Tests Guidelines

## Structure

- One test class per use case (e.g., `TestDeleteObjectUseCase`)
- Use comment sections within the class to group by method: `# --- check_can_delete ---`, `# --- execute ---`

## Fixtures

- Use pytest fixtures from `conftest.py`: `minimal_repository`, `minimal_model_web`
- Create the use case instance in each test: `use_case = DeleteObjectUseCase(minimal_repository)`

## What to Test

Test **orchestration behavior**, not object-specific rules (those belong in entity tests):
- Return types and structure
- Hook dispatch (verify hooks are called with `patch.object(..., wraps=original)`)
- Repository persistence
- Generic behavior across object types

## Testing Hooks Are Called

Use `patch.object` with `wraps` to verify hooks are called while preserving behavior:

```python
from unittest.mock import patch

def test_execute_calls_pre_delete_hook_when_defined(self, minimal_repository, minimal_model_web):
    from model_builder.domain.entities.web_core.usage.usage_pattern_web import UsagePatternWeb

    use_case = DeleteObjectUseCase(minimal_repository)
    up = minimal_model_web.usage_patterns[0]
    original_pre_delete = UsagePatternWeb.pre_delete

    with patch.object(UsagePatternWeb, 'pre_delete', wraps=original_pre_delete) as mock:
        use_case.execute(DeleteObjectInput(object_id=up.efootprint_id))
        mock.assert_called_once()
```

## Example Test Structure

```python
class TestDeleteObjectUseCase:
    """Tests for DeleteObjectUseCase orchestration behavior."""

    # --- check_can_delete ---

    def test_check_can_delete_returns_delete_check_result(self, minimal_repository, minimal_model_web):
        use_case = DeleteObjectUseCase(minimal_repository)
        result = use_case.check_can_delete(minimal_model_web.servers[0].efootprint_id)
        assert isinstance(result, DeleteCheckResult)

    def test_check_can_delete_uses_class_can_delete_hook(self, minimal_repository, minimal_model_web):
        # Verify the use case dispatches to web class hooks
        ...

    # --- execute ---

    def test_execute_returns_deleted_object_info(self, minimal_repository, minimal_model_web):
        ...

    def test_execute_persists_deletion_to_repository(self, minimal_repository, minimal_model_web):
        ...

    def test_execute_calls_pre_delete_hook_when_defined(self, minimal_repository, minimal_model_web):
        # Use patch.object with wraps=original to verify hook is called
        ...
```
