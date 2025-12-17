# E2E Testing Guidelines

## Philosophy: Minimal, Non-Redundant Tests

Each test should cover a **distinct user workflow**. Avoid redundant tests that are subsets of each other.

**Bad:** Separate tests for "create one item" and "create multiple items" - the multiple test already covers single creation.

**Bad:** Testing a UI behavior (like chart visibility) in isolation when another test already exercises it as part of a workflow.

**Good:** One test that creates multiple items, implicitly covering single creation.

**Good:** Testing chart behavior inline while testing usage pattern creation.


## Test Data: Programmatic Fixtures

Build test data using efootprint classes, not JSON files.

```python
from efootprint.api_utils.system_to_json import system_to_json
from tests.fixtures import build_minimal_system, create_hourly_usage

@pytest.fixture
def system_dict_complete():
    system = build_minimal_system("Test System")
    return system_to_json(system, save_calculated_attributes=True)
```

### Orphaned Objects Pattern

For objects that need to appear in the UI but aren't connected via the normal object graph (e.g., servers without jobs), add them directly to the system dict:

```python
system_dict = system_to_json(system, save_calculated_attributes=True)
server = Server.from_defaults("Test Server", storage=storage)
system_dict["Server"] = {server.id: server.to_json(save_calculated_attributes=True)}
```


## Page Object Model

Use page objects from `tests/e2e/pages/` for all interactions. Add new methods there rather than writing raw Playwright calls in tests.


## HTMX Interactions

Use `click_and_wait_for_htmx()` from `tests/e2e/utils.py` for HTMX-triggered clicks. This handles waiting for the HTTP response.


## Test Structure

- One test file per domain concept (servers, jobs, usage patterns, etc.)
- Group related tests in classes
- Use descriptive test names that explain the workflow being tested
- Mark all E2E tests with `@pytest.mark.e2e`
