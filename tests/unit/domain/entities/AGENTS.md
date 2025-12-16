# Entity Tests Guidelines

## Structure

- One test class per entity (e.g., `TestServerWeb`)
- Use comment sections within the class to group tests by method: `# --- method_name ---`
- Don't over-structure with multiple classes per file

## Fixtures

- Use pytest fixtures from `conftest.py` with clear names: `minimal_repository`, `minimal_model_web`
- For snapshot tests, use `MagicMock()` instead of real `model_web` (avoids data-dependent test failures)
- When rebuilding snapshot contexts, mirror the lightweight mocks used in `tests__old/test_structure.py`
  (e.g., deterministic `servers`, `installed_services`, `response_objs`), so creation forms match stored snapshots
  without pulling real `ModelWeb` or hitting external APIs.

## What to Test

Test only entity-specific behavior, not inherited behavior from parent classes:
- `can_delete` hook logic
- `self_delete` cascade behavior
- `pre_create` / `pre_edit` hooks
- Form structure via snapshot tests
- No need to test obvious methods elements like attribute values.

## Snapshot Testing

Use `assert_creation_context_matches_snapshot(WebClass, model_web=MagicMock())` for form structure tests:
- Reference files in `class_structures/` directory
- Temp files (`*_tmp.json`) are created on failure for debugging
- Pass `MagicMock()` as model_web to avoid test coupling to data

```python
from tests.unit.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from unittest.mock import MagicMock

def test_generate_object_creation_context_matches_snapshot(self, minimal_model_web):
    assert_creation_context_matches_snapshot(ServerWeb, model_web=MagicMock())
```

## Example Test Structure

```python
class TestServerWeb:
    """Tests for ServerWeb-specific behavior."""

    # --- can_delete ---

    def test_can_delete_blocked_by_jobs(self, minimal_model_web):
        ...

    def test_can_delete_allowed_without_jobs(self, minimal_model_web):
        ...

    # --- self_delete ---

    def test_self_delete_cascades_to_installed_services(self, minimal_model_web):
        ...

    # --- pre_create ---

    def test_pre_create_creates_storage_and_adds_reference_to_form_data(self, minimal_model_web):
        ...

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self, minimal_model_web):
        assert_creation_context_matches_snapshot(ServerWeb, model_web=MagicMock())
```
