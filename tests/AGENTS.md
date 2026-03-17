# Tests — Overview

This document describes the overall test infrastructure. For E2E-specific guidelines (fixtures, page objects, HTMX helpers), see `tests/e2e/AGENTS.md`.

## Test layers

| Layer | Location | Framework | When to use |
|-------|----------|-----------|-------------|
| JS unit | `js_tests/` | Jest + jsdom | Pure JS logic that can be tested without a browser (math utils, DOM manipulation helpers like chip toggles) |
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
|---------|-----------------|
| `minimal_system` | A complete efootprint `System` object |
| `minimal_system_data` | The same system serialized to dict |
| `minimal_repository` | `InMemorySystemRepository` loaded with `minimal_system_data` |
| `minimal_model_web` | `ModelWeb` wrapping `minimal_system` |
| `empty_repository` | `InMemorySystemRepository` with no system |
| `default_system_repository` | Repository with default data and calculated attributes computed |
| `create_hourly_usage()` | Helper returning an `ExplainableHourlyQuantitiesFromFormInputs` for timeseries fields |

## JS unit tests (`js_tests/`)

Two existing files test pure math utilities (timeseries volume computation and display aggregation). Add new files here for JS logic that is complex enough to fail silently if broken and that doesn't require a real browser. The jsdom environment is sufficient for DOM manipulation helpers.

Run with `npm run jest`. Jest config is in `package.json` (`"testEnvironment": "jsdom"`).

## Python unit tests (`tests/unit_tests/`)

Organised by Clean Architecture layer:
- `domain/entities/` — one test class per web wrapper entity; use snapshot tests for form generation via `assert_creation_context_matches_snapshot()`
- `application/use_cases/` — test orchestration, hook dispatch, return types
- `adapters/` — view parameter mapping, form parsing, repository, UI config providers

## Integration tests (`tests/integration/`)

Use `InMemorySystemRepository` (not a browser). Test multi-step workflows: object creation followed by linking, deletion cascades, edition with recalculation. Don't test rendering or HTMX.

## E2E tests (`tests/e2e/`)

See `tests/e2e/AGENTS.md` for full guidelines. Key points:
- Build fixtures programmatically with efootprint classes (`from_defaults()` where available), not JSON files
- Use page objects from `tests/e2e/pages/` for all browser interactions
- Use `click_and_wait_for_htmx()` for HTMX-triggered actions
- Mark all tests `@pytest.mark.e2e`
- Keep tests non-redundant: one test per distinct workflow

## What NOT to test in the interface

Domain computation correctness (carbon math, Sankey flow values, timeseries generation) is tested in the e-footprint library's own test suite. Interface tests cover parameter mapping, response structure, and UI behaviour only.