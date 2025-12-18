# Frontend Testing Refactoring Plan

## Overview

Migration from Cypress to Playwright (Python API) with improved test organization and shared fixtures between unit and E2E tests.

**📊 For detailed gap analysis of what tests remain to be migrated, see [MIGRATION_GAP_ANALYSIS.md](./MIGRATION_GAP_ANALYSIS.md)**

### Current Progress (2025-12-18)

- **Cypress Tests:** 66 test cases across 11 files (1,708 lines)
- **Playwright Tests:** 27 test cases across 11 files (1,304 lines)
  - 16 migration tests + 11 new organizational tests
- **Migration Status:** ~24% complete (16/66 migrations, but 41% when including new tests: 27/66)
- **Remaining Work:** ~50 test cases (accounting for redundancy elimination)

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

### Phase 1: Setup Infrastructure ✅ COMPLETED
- [x] Install Playwright and pytest-playwright
- [x] Create `tests/e2e/` directory structure
- [x] Create base Page Objects (ModelBuilderPage, SidePanelPage)
- [x] Create E2E conftest with session loading fixture
- [x] Verify one simple test works end-to-end (5 smoke tests passing)
- [x] Create new organizational tests (test_servers.py, test_jobs.py, test_usage_patterns.py, test_usage_journeys.py)

### Phase 2: Migrate Critical Path ✅ COMPLETED
- [x] Migrate `end-to-end.cy.js` (test 1/2) to `test_full_journey.py`
- [x] Migrate `test_services.cy.js` (GenAI services) to `test_genai_services.py`
- [ ] Complete `end-to-end.cy.js` (test 2/2) - leader lines and data export validation

### Phase 3: Complete Partially Migrated Tests 🔄 IN PROGRESS
**Priority: HIGH - Complete existing test files**

#### 3.1: Complete `test_toolbar.py` (6 more tests needed)
Remaining from `test_toolbar_features.cy.js`:
- [ ] Import JSON when model already has objects (replaces previous)
- [ ] Import validates file selection and triggers leader line initialization
- [ ] Export validates filename format with UTC timestamp
- [ ] Change system name persists after page reload
- [ ] Import with various model states (empty, partial, complete)
- [ ] Export with calculated attributes

#### 3.2: Complete `test_forms.py` (8 more tests needed)
Remaining from `test_forms.cy.js`:
- [ ] UJS list disabled when no UJS exist, enabled after creation
- [ ] Jobs list not displayed when no jobs exist, displayed after creation
- [ ] Server creation with/without advanced options visibility
- [ ] Units persistence when editing objects
- [ ] Sources displayed in forms with correct values
- [ ] Unsaved changes warning before closing side panel
- [ ] Unsaved changes warning before opening new side panel
- [ ] Form field validation (required fields, data types)

#### 3.3: Complete `test_results.py` (14 more tests needed)
Remaining from `test_result_panel.cy.js`:
- [ ] Error modal when model cannot be calculated
- [ ] Panel swipe up/down gestures on mobile
- [ ] Exception modal for UJ without UJ steps
- [ ] Granularity change updates chart labels (week/month/year)
- [ ] Sources tab display and toggle
- [ ] Sources export with correct filename
- [ ] Model recomputation when editing with result panel open
- [ ] Chart updates after edit
- [ ] Result panel width adjustment during editing
- [ ] Mobile responsive behavior
- [ ] Chart.js integration verification
- [ ] Multiple chart types (bar, pie, line)
- [ ] Export results to various formats
- [ ] Performance with large datasets

#### 3.4: Complete `test_edge_objects.py` (10 more tests needed)
Remaining from `test_edge_objects.cy.js` (642 lines, 15 tests, only 5 migrated):
- [ ] Edit edge device verification
- [ ] Edge device with advanced parameters
- [ ] Verify advanced parameters persistence
- [ ] Complex edge journey with multiple functions
- [ ] Recurrent edge process editing
- [ ] Edge function with multiple processes
- [ ] Delete edge objects cascade behavior
- [ ] Edge device shared across multiple journeys
- [ ] Edge storage management
- [ ] Edge compute resource validation

### Phase 4: Migrate Timeseries Tests 🆕 NOT STARTED
**Priority: HIGH - Core functionality**

Create `test_timeseries.py` from `test_timeseries.cy.js` (217 lines, 10 tests):
- [ ] Open usage pattern form multiple times, chart always displayed
- [ ] Canvas context validation for chart rendering
- [ ] Timeseries generation with various growth rates
- [ ] Timeseries validation - correct number of elements
- [ ] Modeling duration validation (min/max bounds)
- [ ] Modeling duration unit changes (day/month/year)
- [ ] Error messages for invalid duration values
- [ ] Edit UP with month timeframe validates max correctly
- [ ] Chart not displayed on mobile (viewport: iphone-x)
- [ ] Chart not displayed on tablet (viewport: ipad-mini)

**Note:** This is critical for timeseries form functionality and should be prioritized.

### Phase 5: Migrate Select Multiple Tests 🆕 NOT STARTED
**Priority: MEDIUM - Form interaction**

Merge into `test_forms.py` from `test_select_multiple.cy.js` (32 lines, 11 tests):
- [ ] Add job to UsageJourneyStep via select multiple
- [ ] Remove job from UsageJourneyStep
- [ ] Remove last job from UsageJourneyStep
- [ ] Multiple selection UI behavior
- [ ] Select multiple with pre-existing selections
- [ ] Validation when no items available to select
- [ ] Select multiple ordering/positioning
- [ ] Add/remove animations and transitions
- [ ] Keyboard navigation in select multiple
- [ ] Select multiple with large lists (performance)
- [ ] Select all/deselect all functionality

### Phase 6: Migrate Model Canva Tests 🆕 NOT STARTED
**Priority: MEDIUM - UI behavior**

Distribute tests from `test_model_canva.cy.js` (64 lines, 6 tests):
- [ ] Error when creating job without servers → `test_forms.py`
- [ ] Edit UJ name preserves UJS → `test_usage_journeys.py`
- [ ] Create job on empty UJS, verify positioning → `test_jobs.py`
- [ ] Add job button placement and visibility → `test_jobs.py`
- [ ] Job ordering in collapsed accordion → `test_jobs.py`
- [ ] Multiple jobs positioning verification → `test_jobs.py`

### Phase 7: Migrate Calculated Attributes & Graph Tests 🆕 NOT STARTED
**Priority: LOW - Advanced features**

#### 7.1: Merge into `test_results.py` from `test_calculated_attributes.cy.js` (25 lines, 1 test):
- [ ] Navigate between calculated attributes tabs
- [ ] Chart updates when switching attributes
- [ ] Formula display for calculated attributes
- [ ] Ancestors and children navigation in attribute tree

#### 7.2: Create `test_calculus_graph.py` from `test_calculus_graph.cy.js` (59 lines, 4 tests):
- [ ] Simple calculus graph opens in iframe
- [ ] Complex calculus graph with multiple usage patterns
- [ ] Verify vis.js network graph rendering
- [ ] Calculus graph for various attribute types
- [ ] Graph interactivity (zoom, pan, node selection)

### Phase 8: Cleanup 📦 PENDING
- [ ] Verify all 90 Cypress test cases have Playwright equivalents
- [ ] Run full Playwright suite and ensure reliability
- [ ] Remove Cypress dependencies from package.json
- [ ] Remove cypress/ directory and fixtures
- [ ] Update CI configuration (remove Cypress, add Playwright)
- [ ] Update CLAUDE.md with new testing instructions
- [ ] Document Playwright debugging workflow
- [ ] Create migration documentation for future reference

### Phase 9: JS Unit Test Enhancement (Optional, Parallel)
- [ ] Install Vitest, migrate existing Jest tests
- [ ] Add unit tests for `select_multiple.js`
- [ ] Add unit tests for `dynamic_forms.js` (pure logic functions)
- [ ] Add unit tests for timeseries calculation functions
- [ ] Add unit tests for chart utilities

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
