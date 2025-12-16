# Frontend Testing Refactoring Plan

## Overview

Migration from Cypress to Playwright (Python API) with improved test organization and shared fixtures between unit and E2E tests.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| E2E Framework | Playwright (Python) | Debug with familiar tools, reuse efootprint classes for model creation |
| JS Unit Tests | Vitest | Modern, fast, ESM-native (replaces Jest) |
| Test Runner | pytest (unified) | Single runner for Python unit + E2E tests |
| Model Creation | Programmatic (Python) | No JSON fixture drift, type-safe, reusable |

---

## Target Architecture

```
tests/
├── conftest.py                    # Root fixtures (shared by unit + e2e)
├── unit/                          # Existing pytest unit tests (unchanged)
│   ├── domain/
│   ├── application/
│   └── adapters/
├── e2e/                           # Playwright E2E tests (new)
│   ├── conftest.py                # E2E-specific fixtures
│   ├── pages/                     # Page Object Models
│   │   ├── __init__.py
│   │   ├── model_builder_page.py
│   │   ├── side_panel_page.py
│   │   ├── result_panel_page.py
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── object_card.py
│   │       ├── dynamic_form.py
│   │       └── timeseries_chart.py
│   ├── test_modeling.py           # Object CRUD operations
│   ├── test_forms.py              # Form behavior, validation
│   ├── test_timeseries.py         # Timeseries inputs, charts
│   ├── test_results.py            # Result panel, calculations
│   ├── test_import_export.py      # JSON import/export
│   └── test_full_journey.py       # Critical path E2E
└── js/                            # JS unit tests (migrated from js_tests/)
    ├── timeseries_utils.test.ts
    ├── usage_pattern_timeseries.test.ts
    ├── select_multiple.test.ts    # New
    └── dynamic_forms.test.ts      # New
```

---

## Test Categories

### 1. Python Unit Tests (pytest) - Existing
- Domain entities, use cases, services
- Fast, no browser needed
- Run on every commit

### 2. E2E Tests (Playwright Python) - New
- Full user journeys through the browser
- HTMX interactions, form submissions, visual verification
- Run on PR merge

### 3. JS Unit Tests (Vitest) - Enhanced
- Pure JS functions (timeseries calculations, array operations)
- Fast feedback loop
- Run on every commit

```
Speed:  Unit (ms) ──────> Integration (s) ──────> E2E (min)
Scope:  Function ──────────> Component ──────────> Full App
```

---

## Cypress to Playwright Test Mapping

| Cypress File | Playwright Equivalent | Priority |
|--------------|----------------------|----------|
| `end-to-end.cy.js` | `test_full_journey.py` | P0 - Critical path |
| `test_forms.cy.js` | `test_forms.py` | P1 |
| `test_timeseries.cy.js` | `test_timeseries.py` | P1 |
| `test_services.cy.js` | `test_modeling.py` | P1 |
| `test_result_panel.cy.js` | `test_results.py` | P1 |
| `test_toolbar_features.cy.js` | `test_import_export.py` | P2 |
| `test_calculated_attributes.cy.js` | `test_results.py` | P2 |
| `test_edge_objects.cy.js` | `test_modeling.py` | P2 |
| `test_model_canva.cy.js` | `test_modeling.py` | P2 |
| `test_calculus_graph.cy.js` | `test_results.py` | P3 |
| `test_select_multiple.cy.js` | `test_forms.py` | P2 |

---

## Shared Fixture Strategy

### Model Creation Fixtures

```python
# tests/conftest.py
@pytest.fixture
def empty_system():
    """A system with no objects."""
    return System(name="Test System")

@pytest.fixture
def system_with_server(empty_system):
    """System with one server (and its required storage)."""
    storage = Storage(name="Test Storage", ...)
    server = Server(name="Test Server", storage=storage, ...)
    empty_system.add_server(server)
    return empty_system

@pytest.fixture
def complete_system():
    """Full system ready for emissions calculation."""
    # Usage journey -> steps -> jobs -> services -> servers
    ...
```

### E2E Session Loading

```python
# tests/e2e/conftest.py
@pytest.fixture
def loaded_model(page, live_server, system_with_server):
    """Load a system into the browser session and navigate to model builder."""
    # Serialize system to JSON
    system_json = system_to_json(system_with_server)

    # Load via import endpoint or session manipulation
    page.goto(f"{live_server.url}/model_builder/")
    # ... load system_json into session

    return system_with_server
```

---

## Page Object Model Design

```python
# tests/e2e/pages/model_builder_page.py
class ModelBuilderPage:
    def __init__(self, page: Page):
        self.page = page
        self.side_panel = SidePanelPage(page)

    def goto(self):
        self.page.goto('/model_builder/')

    def get_object_card(self, object_type: str, name: str):
        return ObjectCard(
            self.page.locator(f'div[id^="{object_type}"]').filter(has_text=name)
        )

    def open_create_panel(self, object_type: str):
        self.page.get_by_role('button', name=f'Add {object_type}').click()
        return self.side_panel

# tests/e2e/pages/components/object_card.py
class ObjectCard:
    def __init__(self, locator: Locator):
        self.locator = locator

    def click_edit(self):
        self.locator.get_by_role('button').click()

    def click_delete(self):
        self.locator.get_by_role('button', name='Delete').click()
```

---

## Iterative Migration Plan

### Phase 1: Setup Infrastructure (COMPLETED)
- [x] Install Playwright and pytest-playwright
- [x] Create `tests/e2e/` directory structure
- [x] Create base Page Objects (ModelBuilderPage, SidePanelPage)
- [x] Create E2E conftest with session loading fixture
- [x] Verify one simple test works end-to-end (5 smoke tests passing)

### Phase 2: Migrate Critical Path
- [ ] Migrate `end-to-end.cy.js` to `test_full_journey.py`
- [ ] Ensure CI runs both Cypress and Playwright temporarily
- [ ] Validate equivalent coverage

### Phase 3: Migrate Form Tests
- [ ] Migrate `test_forms.cy.js` to `test_forms.py`
- [ ] Migrate `test_timeseries.cy.js` to `test_timeseries.py`
- [ ] Add Page Object components as needed

### Phase 4: Migrate Object CRUD Tests
- [ ] Migrate `test_services.cy.js` to `test_modeling.py`
- [ ] Migrate `test_edge_objects.cy.js` (merge into test_modeling.py)
- [ ] Migrate `test_model_canva.cy.js` (merge into test_modeling.py)
- [ ] Migrate `test_select_multiple.cy.js` to `test_forms.py`

### Phase 5: Migrate Result Tests
- [ ] Migrate `test_result_panel.cy.js` to `test_results.py`
- [ ] Migrate `test_calculated_attributes.cy.js` (merge into test_results.py)
- [ ] Migrate `test_calculus_graph.cy.js` (merge into test_results.py)

### Phase 6: Migrate Import/Export Tests
- [ ] Migrate `test_toolbar_features.cy.js` to `test_import_export.py`

### Phase 7: Cleanup
- [ ] Remove Cypress dependencies from package.json
- [ ] Remove cypress/ directory
- [ ] Update CI configuration
- [ ] Update CLAUDE.md with new testing instructions

### Phase 8: JS Unit Test Enhancement (Optional, Parallel)
- [ ] Install Vitest, migrate existing Jest tests
- [ ] Add unit tests for `select_multiple.js`
- [ ] Add unit tests for `dynamic_forms.js` (pure logic functions)

---

## CI Configuration

```yaml
# .github/workflows/test.yml (example)
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: poetry install
      - name: Run unit tests
        run: poetry run pytest tests/unit/

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: poetry install
      - name: Install Playwright browsers
        run: playwright install --with-deps chromium
      - name: Run E2E tests
        run: poetry run pytest tests/e2e/ --browser chromium

  js-unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node
        uses: actions/setup-node@v4
      - name: Install dependencies
        run: npm install
      - name: Run JS unit tests
        run: npm run test:unit
```

---

## Success Criteria

- [ ] All 43 Cypress test cases have Playwright equivalents
- [ ] E2E tests use programmatic model creation (no JSON fixtures for most tests)
- [ ] Page Objects cover main UI components
- [ ] Tests run in CI with comparable reliability
- [ ] Debug workflow documented and working
- [ ] Cypress fully removed from project

---

## Commands Reference

```bash
# Run all Python tests (unit + e2e)
poetry run pytest

# Run only E2E tests
poetry run pytest tests/e2e/

# Run E2E tests with headed browser (for debugging)
poetry run pytest tests/e2e/ --headed

# Run specific test with debugger
poetry run pytest tests/e2e/test_forms.py::test_unsaved_changes -s --pdb

# Generate Playwright test code (record mode)
playwright codegen http://localhost:8000/model_builder/

# Run JS unit tests
npm run test:unit
```
