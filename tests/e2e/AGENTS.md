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
    return system_to_json(system, save_calculated_attributes=False)
```

### Building System Dicts from Individual Objects not linked to a System

Use `EMPTY_SYSTEM_DICT` as the base and `system_to_json()` on individual modeling objects (not the whole System). This lets you build complex test fixtures without constructing a complete System.

Build the system data and load it into the browser in a single fixture - no need for a two-stage pattern:

```python
from copy import deepcopy
from efootprint.api_utils.system_to_json import system_to_json
from tests.e2e.conftest import load_system_dict_into_browser
from tests.e2e.utils import EMPTY_SYSTEM_DICT, add_only_update

@pytest.fixture
def edge_system_in_browser(model_builder_page: ModelBuilderPage):
    # Create objects using from_defaults() where available
    edge_device = EdgeComputer.from_defaults("Shared Edge Device", storage=edge_storage)
    process1 = RecurrentEdgeProcess.from_defaults("Process 1", edge_device=edge_device)
    edge_function1 = EdgeFunction("Function 1", recurrent_edge_device_needs=[process1])
    journey1 = EdgeUsageJourney.from_defaults(name="Journey 1", edge_functions=[edge_function1])

    # Start with empty system dict (use deepcopy to avoid mutating the shared dict)
    system_data = deepcopy(EMPTY_SYSTEM_DICT)

    # system_to_json() on a single object serializes it AND all its dependencies
    system_data.update(system_to_json(journey1, save_calculated_attributes=False))

    # Use add_only_update() to merge additional object trees without overwriting shared objects
    add_only_update(system_data, system_to_json(journey2, save_calculated_attributes=False))

    # Load into browser and return the page object ready to use
    return load_system_dict_into_browser(model_builder_page, system_data)
```

**Key helpers:**
- `EMPTY_SYSTEM_DICT` (from `tests/e2e/utils.py`) - Minimal valid system dict as starting point
- `add_only_update(target, source)` (from `tests/e2e/utils.py`) - Recursively merges dicts, only adding missing keys (never overwrites)
- `load_system_dict_into_browser(model_builder_page, system_data)` (from `tests/e2e/conftest.py`) - Loads system dict into browser session

**Prefer `from_defaults()`:** Most efootprint classes have a `from_defaults()` class method that creates objects with sensible defaults, avoiding verbose ExplainableQuantity construction.


## Page Object Model

Use page objects from `tests/e2e/pages/` for all interactions. Add new methods there rather than writing raw Playwright calls in tests.


## HTMX Interactions

Use `click_and_wait_for_htmx()` from `tests/e2e/utils.py` for HTMX-triggered clicks. This handles waiting for the HTTP response.


## Test Structure

- One test file per domain concept (servers, jobs, usage patterns, etc.)
- Group related tests in classes
- Use descriptive test names that explain the workflow being tested
- Mark all E2E tests with `@pytest.mark.e2e`
