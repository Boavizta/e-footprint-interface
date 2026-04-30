# Testing — e-footprint-interface

This is the canonical testing guide. `tests/AGENTS.md`, `tests/integration/AGENTS.md`, and `tests/e2e/AGENTS.md` are thin pointers to this file.

## Test layers

| Layer | Location | Framework | When to use |
|-------|----------|-----------|-------------|
| JS unit | `js_tests/` | Jest + jsdom | Pure JS logic that can be tested without a browser (math utils, DOM manipulation helpers) |
| Python unit | `tests/unit_tests/` | pytest | Single-class behaviour: entity hooks, form parsing, view parameter mapping, UI config providers |
| Integration | `tests/integration/` | pytest | Cross-layer workflows without a browser: create/edit/delete round-trips, cascade deletion, calculated attributes |
| E2E | `tests/e2e/` | Playwright + pytest | Full user workflows in a real browser; anything involving HTMX swaps, JS interactions, or rendered output |

## Running tests

```bash
# Python (all)
poetry run pytest

# Specific layer
poetry run pytest tests/unit_tests
poetry run pytest tests/integration
poetry run pytest tests/e2e --base-url http://localhost:8000   # requires running server

# Jest
npm run jest
```

## Key shared fixtures — `tests/fixtures/system_builders.py`

| Fixture | What it provides |
|---------|------------------|
| `minimal_system` | A complete efootprint `System` object |
| `minimal_system_data` | The same system serialized to dict |
| `minimal_repository` | `InMemorySystemRepository` loaded with `minimal_system_data` |
| `minimal_model_web` | `ModelWeb` wrapping `minimal_system` |
| `empty_repository` | `InMemorySystemRepository` with no system |
| `default_system_repository` | Repository with default data and calculated attributes computed |
| `create_hourly_usage()` | Helper returning an `ExplainableHourlyQuantitiesFromFormInputs` |

Both `InMemorySystemRepository` and `SessionSystemRepository` support `interface_config` (in-RAM storage, merged on `save_data()`). Set `repository.interface_config = {...}` before `persist_to_cache()` to test config persistence.

## Python unit tests (`tests/unit_tests/`)

Organised by Clean Architecture layer:

- `domain/entities/` — one test class per web wrapper entity; use snapshot tests for form generation via `assert_creation_context_matches_snapshot()`.
- `application/use_cases/` — test orchestration, hook dispatch, return types.
- `adapters/` — view parameter mapping, form parsing, repository, UI config providers.

## Integration tests (`tests/integration/`)

These are integration tests of the Clean Architecture layer (adapters → use cases → domain), run **without Django** by relying on `InMemorySystemRepository`.

### Goals

- Validate end-to-end flows (create / edit / delete) via:
  - `model_builder.adapters.forms.form_data_parser.parse_form_data`
  - `model_builder.application.use_cases.*`
  - `model_builder.domain.entities.web_core.model_web.ModelWeb`
- Keep tests **easy to write, read, and maintain**.

### Non-goals

- No Django request/session scaffolding.
- No testing of HTML rendering / templates / HTMX responses.

### Form data generation (preferred workflow)

Always build "HTTP-like" form payloads with `tests.fixtures.form_data_builders.create_post_data_from_class_default_values`, then parse them with `parse_form_data(post_data, post_data["type_object_available"])`, and feed the parsed dict to the use case.

`create_post_data_from_class_default_values(...)`:

- Fills scalar quantity defaults as `Class_attr` + `Class_attr__unit`.
- Uses web-wrapper defaults (`*.default_values`) when available.
- Supports nested forms and explainable objects "form_inputs" via `__` overrides.

Patterns:

- **Plain scalar/ids overrides:** pass overrides as clean keys; the helper prefixes them.
  - `create_post_data_from_class_default_values("X", "Job", server=server_id)` becomes `Job_server = server_id`.
- **Nested object forms:** pass `*_form_data` dicts; the helper JSON-encodes them.
  - `create_post_data_from_class_default_values("Server", "Server", Storage_form_data=storage_post_data)`
- **ExplainableObject form inputs:** override with `attr__form_input_key=value`.

### Use case execution

- Create: `CreateObjectUseCase(repository).execute(CreateObjectInput(...))`
- Edit: `EditObjectUseCase(ModelWeb(repository)).execute(EditObjectInput(...))`
- Delete: `DeleteObjectUseCase(ModelWeb(repository)).execute(DeleteObjectInput(...))`

### Assertions

Prefer **structure-based** assertions over full JSON equality. Use a helper like `_current_structure(ModelWeb(repo))` (class → set(ids)).

For computed impacts, assert coarse signals:

- "network energy footprint increases after increasing data transferred"
- "emissions series is non-empty and non-zero for key categories"

### Dict-based relationships

For testing edge device groups and other dict-based relationships, use the dict mutation view functions directly or build dict-count form payloads. See existing tests in `test_edge_device_groups.py` for patterns.

## E2E tests (`tests/e2e/`)

### Philosophy: minimal, non-redundant

Each test should cover a **distinct user workflow**. Avoid redundant tests that are subsets of each other.

- **Bad:** Separate tests for "create one item" and "create multiple items" — the multiple test already covers single creation.
- **Bad:** Testing a UI behavior in isolation when another test already exercises it as part of a workflow.
- **Good:** One test that creates multiple items, implicitly covering single creation.
- **Good:** Testing chart behavior inline while testing usage pattern creation.

### Test data: programmatic fixtures

Build test data using efootprint classes, not JSON files. Use `from_defaults()` where available.

```python
@pytest.fixture
def edge_system_in_browser(model_builder_page: ModelBuilderPage):
    edge_device = EdgeComputer.from_defaults("Shared Edge Device", storage=edge_storage)
    process1 = RecurrentEdgeProcess.from_defaults("Process 1", edge_device=edge_device)
    edge_function1 = EdgeFunction("Function 1", recurrent_edge_device_needs=[process1])
    journey1 = EdgeUsageJourney.from_defaults(name="Journey 1", edge_functions=[edge_function1])

    system_data = deepcopy(EMPTY_SYSTEM_DICT)
    system_data.update(system_to_json(journey1, save_calculated_attributes=False))
    add_only_update(system_data, system_to_json(journey2, save_calculated_attributes=False))

    return load_system_dict_into_browser(model_builder_page, system_data)
```

**Key helpers** (from `tests/e2e/utils.py` and `tests/e2e/conftest.py`):

- `EMPTY_SYSTEM_DICT` — minimal valid system dict as starting point.
- `add_only_update(target, source)` — recursively merges dicts, only adding missing keys.
- `load_system_dict_into_browser(model_builder_page, system_data)` — loads system dict into browser session.

**Prefer `from_defaults()`:** most efootprint classes have a `from_defaults()` class method that creates objects with sensible defaults, avoiding verbose `ExplainableQuantity` construction.

### Page Object Model

Use page objects from `tests/e2e/pages/` for all interactions. Add new methods there rather than writing raw Playwright calls in tests.

### HTMX interactions

Use `click_and_wait_for_htmx()` from `tests/e2e/utils.py` for HTMX-triggered clicks. This handles waiting for the HTTP response — don't write raw Playwright clicks for HTMX flows.

### Test structure

- One test file per domain concept (servers, jobs, usage patterns, etc.).
- Group related tests in classes.
- Use descriptive test names that explain the workflow being tested.
- Mark all E2E tests with `@pytest.mark.e2e`.

## What NOT to test in the interface

Domain computation correctness (carbon math, Sankey flow values, timeseries generation) is tested in the e-footprint library's own test suite. Interface tests cover parameter mapping, response structure, and UI behaviour only.

## Style guardrails

- Keep tests short, linear, and readable.
- Use double quotes for strings.
- Respect 120-character lines and don't systematically break lines between parameters.
- If you must add new test data, extend the generic form builder first rather than writing class-specific builders.

## JS unit tests (`js_tests/`)

Add files here for JS logic that is complex enough to fail silently if broken and that doesn't require a real browser. The jsdom environment is sufficient for DOM manipulation helpers.

Run with `npm run jest`. Jest config is in `package.json` (`"testEnvironment": "jsdom"`).

When a test exercises JS that manipulates a real Django partial, do **not** hand-roll the markup in JS — declare a named case in `js_tests/build_fixtures.py` (`CASES`) and `mount("<fixture-name>")` from the test. The npm `jest` script renders `js_tests/fixtures/*.html` from the actual templates before running jest, so a class rename or attribute change in the template fails its tests instead of silently drifting. Generated fixtures are gitignored. See `source_metadata.test.js` for the pattern.

## Flakiness

If a test fails on the first run but passes on retry, **flag it explicitly** to the developer as a flaky test rather than silently re-running.
