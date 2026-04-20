# AGENTS — e-footprint-interface

This document orients AI/code agents and new contributors. It explains how the repository works, the main code style guidelines, the core logic and classes, how rendering happens in the web context, and the main technological choices.

## What this repository is

A Django-based web UI for the digital service carbon footprint model [e-footprint](https://github.com/Boavizta/e-footprint). It embeds:
- A Python/Django backend orchestrating sessions, model building, and HTTP views
- A Bootstrap/HTMX frontend for dynamic, partial-page updates and a lightweight SPA feel
- Templates and small JS utilities to render forms, charts, and explainable results

Upstream domain logic (carbon/energy modeling) is provided by the e-footprint Python package and is adapted/wrapped for the web here.


## High-level architecture (Clean Architecture)

The codebase follows Clean Architecture principles with clear separation of concerns:

```
model_builder/
├── domain/                    # Business logic, no Django dependencies
│   ├── entities/              # Web wrappers around efootprint objects
│   │   ├── web_core/          # Core entities (ModelWeb, ServerWeb, JobWeb, EdgeDeviceGroupWeb, etc.)
│   │   ├── web_builders/      # Builder-specific entities (ExternalAPIWeb, etc.)
│   │   ├── web_abstract_modeling_classes/  # Base classes (ModelingObjectWeb)
│   │   └── efootprint_extensions/  # ExplainableObject extensions
│   ├── services/              # Domain services (EmissionsCalculationService, etc.)
│   ├── interfaces/            # Repository interfaces (ISystemRepository)
│   ├── object_factory.py      # Object creation/editing logic
│   ├── all_efootprint_classes.py
│   └── efootprint_to_web_mapping.py
├── application/
│   └── use_cases/             # CreateObjectUseCase, EditObjectUseCase, DeleteObjectUseCase
├── adapters/
│   ├── views/                 # HTTP views (thin adapters)
│   │   ├── views.py           # Main views (upload/download, model builder page)
│   │   ├── views_creation.py  # Object creation views
│   │   ├── views_edition.py   # Object editing + link-existing panel views
│   │   ├── views_dict_mutation.py  # Dict-based relationship mutations (count/link/unlink)
│   │   └── sankey_views.py    # Sankey diagram views
│   ├── presenters/            # HtmxPresenter (formats responses)
│   ├── repositories/          # SessionSystemRepository, InMemorySystemRepository
│   ├── forms/                 # Form parsing (form_data_parser.py) and generation (form_field_generator.py)
│   └── ui_config/             # UI configuration providers
├── templates/                 # Django templates
├── version_upgrade_handlers.py  # Schema migration handlers for interface_config
└── domain/reference_data/     # JSON configs (default data)
```

### Flow
1. User action → View (adapter)
2. View maps request → Use Case input
3. Use Case orchestrates domain logic
4. Presenter formats output → HTTP response


## Code style & conventions

- AI agents
  - Favor making all edits on the same file at once rather than step-by-step changes.
  - **Never paper over a bug.** If you discover a bug while working on an unrelated task (e.g. the edit
    panel missing a `name` attribute, a creation flow not refreshing a sibling list, a stale card after
    mutation), do not work around it in test code or production code — no `page.reload()` to hide it,
    no defensive branch to tolerate it, no renamed assertion to avoid triggering it. Stop and either
    (a) fix it on the spot with a short comment if the fix is straightforward and in scope, or
    (b) surface it to the developer and ask how to proceed. Quality over convenience, always.
  - **Always propose computationally efficient solutions**, especially for data processing and numerical operations:
    - Prefer vectorized NumPy operations over Python loops
    - Use single-pass algorithms (e.g., `np.bincount`) over multiple iterations
    - When presenting solutions, include complexity analysis (e.g., O(n) vs O(n²))
    - Present trade-offs between readability and performance when relevant
- Python
  - Formatter/lint: follow `.pylintrc`; prefer PEP 8; type hints where helpful
  - Keep functions small; raise explicit errors with actionable messages
  - Keep number of lines low; prefer to write long lines while respecting the 120 characters limit
  - **Performance**: For array/data operations, prioritize NumPy vectorization over list comprehensions or loops
  - Prefer using double quotes `"` for strings, over single quotes `'`
- Django
  - Views: thin adapters that delegate to use cases and presenters
  - Templates: small, composable partials (see `model_builder/templates/model_builder/...`)
  - Keep session data authoritative for the current modeling "system"
- JavaScript
  - Vanilla JS + small helpers only; keep logic minimal; prefer progressive enhancement
  - Use HTMX attributes for partial updates over large custom JS
- Tests
  - Python tests go under `tests/` (and app-specific subfolders)
  - Playwright E2E tests under `tests/e2e/`


## Core logic and main classes

### Key files and their responsibilities

#### ModelWeb - Central orchestrator (`domain/entities/web_core/model_web.py`)
`ModelWeb` is the central web wrapper around the e-footprint domain model. It:
- Deserializes session `system_data` via `efootprint.api_utils.json_to_system`
- Wraps the resulting domain `System` into web objects (`wrap_efootprint_object`)
- Exposes typed accessors: `servers`, `services`, `jobs`, `usage_patterns`, `usage_journeys`, `edge_device_groups`, `ungrouped_edge_devices`, etc.
- Serializes back to JSON with or without calculated attributes via `to_json()`
- Persists to cache via `persist_to_cache()` (serializes system + merges `interface_config` via repository)
- Maintains a flat index of objects (`flat_efootprint_objs_dict`) for quick lookups

#### Use Cases (`application/use_cases/`)
- `CreateObjectUseCase` - Object creation with hooks pattern (`pre_create`, `post_create`, etc.)
- `EditObjectUseCase` - Object editing with `pre_edit` hook
- `DeleteObjectUseCase` - Object deletion with `can_delete`, `pre_delete` hooks

#### Domain Services (`domain/services/`)
- `ObjectLinkingService` - Parent-child linking logic
- `EditService` - Handles object editing with cascade cleanup
- `SystemValidationService` - Validates system completeness
- `EmissionsCalculationService` - Calculates daily emissions timeseries

#### Class registries (`domain/`)
- `all_efootprint_classes.py` - `MODELING_OBJECT_CLASSES_DICT` merges e-footprint classes
- `efootprint_to_web_mapping.py` - Maps e-footprint class names to web wrappers

#### Web wrappers (`domain/entities/web_core/`)
Package of web wrappers around e-footprint domain classes. Each web wrapper provides template-friendly properties and form generation logic. Notable wrappers:
- `EdgeDeviceGroupWeb` — uses `attributes_to_skip_in_forms` to exclude dict attributes from standard form generation (they use a dedicated `dict_count` widget instead)
- `EdgeGroupMemberMixin` — shared behavior for objects that can be members of edge device groups (pre_delete hooks to remove dict references before deletion)

#### Adapters
- `adapters/views/` - HTTP views (thin adapters calling use cases)
  - `views_dict_mutation.py` - Dedicated endpoints for dict-based relationship mutations (see "Dict-based relationships" below)
  - `views_edition.py` - Includes `open_link_existing_panel` for linking existing child objects
- `adapters/presenters/htmx_presenter.py` - Formats use case outputs as HTMX responses
- `adapters/repositories/session_system_repository.py` - Loads/saves system from Django session. Also holds `interface_config` in RAM and merges it on `save_data()`
- `adapters/forms/form_data_parser.py` - Parses HTTP form data before passing to use cases
- `adapters/forms/form_field_generator.py` - Form field generation utilities. Includes `generate_select_multiple_field()` as a standalone reusable function
- `adapters/ui_config/` - Provides UI configuration (class labels, field metadata)

#### Object factory (`domain/object_factory.py`)
- `create_efootprint_obj_from_parsed_data()` - Creates efootprint objects from pre-parsed form data. Supports both list-based (`List[ChildType]`) and dict-based (`ExplainableObjectDict`) constructor parameters
- `edit_object_from_parsed_data()` - Handles object updates via `ModelingUpdate`

#### Extension mechanism (`domain/entities/efootprint_extensions/`)
Specialized `ExplainableObject` subclasses that enhance e-footprint types:
- `ExplainableStartDate` - Date serialization for forms
- `ExplainableHourlyQuantitiesFromFormInputs` - Timeseries from growth rate inputs
- `ExplainableRecurrentQuantitiesFromConstant` - Recurrent timeseries from constant values


### Creation prerequisites and disabled UX

Web classes that have prerequisites for creation define a `can_create(cls, model_web) -> bool` classmethod. It returns `True` when allowed, `False` when blocked. `get_creation_prerequisites` delegates to `can_create` and raises a generic error if blocked (last line of defence — the UI should have disabled the button before this point).

`ModelWeb._build_creation_constraints()` iterates all registered web classes, deduplicates by MRO defining class, and returns a dict keyed by the defining class name (e.g. `"JobWeb"`, `"UsagePatternWeb"`, `"EdgeUsagePatternWeb"`, `"RecurrentServerNeedWeb"`, `"RecurrentEdgeDeviceNeedBaseWeb"`), plus a `"__results__"` sentinel entry from `SystemValidationService`. Values are `{"enabled": bool, "disabled": bool}` for class-based entries; the `__results__` entry additionally carries `reason` (live validation-error text). Static disabled-button tooltips live in `CONSTRAINT_MESSAGES` and are resolved at render time via the `constraint_tooltip` template filter — the domain never imports from adapters. This dict is stored at `model_web.creation_constraints` and recomputed after every mutation.

**Constraint diff on mutation.** `ModelingObjectWeb.create_side_effects`, `edit_side_effects`, and `delete_side_effects` are instance methods (no args beyond `self`). They read `self.model_web` and delegate to the shared `self._recompute_constraints_and_emit_regions()` helper, which diffs old vs. new constraints and, when any flip:
- Emits two OOB regions: `model_canvas` (re-renders `#model-canva` contents via `innerHTML`) and `results_buttons` (updates `#btn-open-panel-result` and `#show-results-toolbar-btn` via `outerHTML`)
- Sets `model_web.constraint_changes` to a list of `(key, "locked"|"unlocked")` tuples

Subclasses that override a `*_side_effects` hook (e.g. `EdgeDeviceGroupWeb`) must call `super()` first and then extend the returned region list, or the diff-based regions will be lost.

**Toast notifications and tooltips.** `HtmxPresenter._constraint_toast_messages()` reads `model_web.constraint_changes`, looks up messages in `adapters/ui_config/constraint_messages.py` (`CONSTRAINT_MESSAGES`), and passes them as `constraint_messages` in the `displayToastAndHighlightObjects` event. The JS handler appends them to the action toast (e.g. "Server has been saved! — You can now add jobs"). `initModelBuilderMain` is added to `HX-Trigger-After-Settle` when the `model_canvas` OOB is emitted, to reinitialize Bootstrap tooltips, sortable lists, and leaderlines after the canvas swap. Each `CONSTRAINT_MESSAGES` entry has three keys: `"unlocked"` (toast when enabled), `"locked"` (toast when disabled), and `"tooltip"` (text shown on the disabled button). The keyset of `CONSTRAINT_MESSAGES` must match the keyset of `creation_constraints`; `tests/unit_tests/adapters/ui_config/test_constraint_messages_consistency.py` enforces this invariant.

**Template integration.** `add_object_button.html` and `add_child_button.html` accept `disabled` and `disabled_reason` — disabled renders a non-interactive button with a Bootstrap tooltip. `child_sections` on `ModelingObjectWeb` exposes `constraint_key` (the defining-class name) for each section, and templates resolve the tooltip copy with `{{ section.constraint_key|constraint_tooltip }}`. The `__results__` entry is looked up in templates via the generic `get_item` filter (Django rejects the `__` prefix in dot syntax). For the Results buttons (`results_bar_button.html`, `show_results_toolbar_button.html`) the disabled-state tooltip uses the live `reason` string rather than the static copy, because validation errors are dynamic.


### Timeseries handling (important!)

**Current approach:** Timeseries generation is handled by `ExplainableObject` subclasses registered to the base timeseries types:

#### ExplainableHourlyQuantitiesFromFormInputs
- **Purpose:** Generate hourly timeseries from simple form inputs (start date, duration, initial volume, growth rate)
- **Registration:** Matches JSON with `"form_inputs"` key containing `"type": "growth_based"`
- **Storage:** Stores both form inputs (for editing) AND computed compressed timeseries
- **Lazy evaluation:** Computes timeseries only when `.value` accessed; caches result

#### ExplainableRecurrentQuantitiesFromConstant
- **Purpose:** Generate 168-element recurrent array from single constant value
- **Registration:** Matches JSON with `"constant_value"` and `"constant_unit"` keys
- **Storage:** Stores constant value (for editing) AND computed recurring_values array
- **Lazy evaluation:** Generates 168-element array when `.value` accessed; caches result


### Persistence and interface_config

The repository layer manages two concerns:
1. **System data** — the efootprint model (serialized via `ModelWeb.to_json()`)
2. **Interface config** — UI-only state (e.g., Sankey diagram settings) stored as a top-level `interface_config` key in the cached JSON

**Key principle:** `ModelWeb` stays pure efootprint domain — it never sees or touches `interface_config`. The repository owns it.

- `SessionSystemRepository` holds `_interface_config` in RAM, populated lazily on first read
- `save_data()` merges `_interface_config` and `efootprint_interface_version` into the JSON before writing
- `persist_to_cache()` on `ModelWeb` calls `to_json()` then `repository.save_data()`
- `version_upgrade_handlers.py` provides migration infrastructure for `interface_config` schema changes across versions

The `interface_config` is included in JSON exports (download) and restored on imports (upload), enabling Sankey settings to survive export/import cycles.


### Relationship types

#### List-based children (standard pattern)
Most parent-child relationships use `List[ChildType]` constructor parameters. Managed via:
- `select_multiple` widget in forms (add/remove by selecting from available objects)
- `edit_object` endpoint for mutations
- `child_sections` property on `ModelingObjectWeb` provides structured access with `linkable_existing_count`

#### Dict-based relationships (`ExplainableObjectDict`)
Edge device groups use dict-based relationships where each entry is `{object: count}`:
- `EdgeDeviceGroup.sub_group_counts` — maps sub-groups to counts
- `EdgeDeviceGroup.edge_device_counts` — maps devices to counts

These require dedicated mutation endpoints in `views_dict_mutation.py`:
- `POST /update-dict-count/<parent_id>/<key_id>/` — update count
- `POST /unlink-dict-entry/<parent_id>/<key_id>/` — remove entry
- `POST /link-dict-entry/<parent_id>/<key_id>/` — add entry with count=1

The `dict_count` form widget (`dict_count.html` + `dict_count.js`) provides per-entry count inputs. Cycle prevention for nested groups is enforced at the view layer by excluding the group itself and all its ancestors from the sub-group picker.

#### "Link existing" flow
When linkable objects of a child type exist, an "Link existing" button appears alongside "Add new" in object cards. It opens a focused side panel (`open_link_existing_panel` in `views_edition.py`) showing only a `select_multiple` field, submitting to the existing `edit_object` endpoint. The `generate_select_multiple_field()` function in `form_field_generator.py` is a standalone reusable helper for building this widget.


### Composite form field metadata

Composite form widgets (e.g., `hourly_quantities_from_growth`) can carry per-class metadata for their subfields. Instead of template conditionals like `{% if object_type == "UsagePattern" %}`, declare a class attribute on the web wrapper:

```python
# On the web wrapper base class — provides safe defaults
hourly_quantities_from_growth_ui_config = {"initial_volume": {"label": "Initial volume", "tooltip": None}}

# On a specific subclass — overrides with class-specific wording
hourly_quantities_from_growth_ui_config = {"initial_volume": {"label": "Custom label", "tooltip": "Help text"}}
```

The form generator injects this as `field["subfields"]` so templates can render it generically.


## Rendering in the web context

- Session-driven state: The current system model is stored in Django session as `system_data` (JSON). Each request reconstructs the domain system via `ModelWeb(repository)`.
- HTMX partials: Most UI actions trigger small HTTP requests that replace DOM snippets using templates under `model_builder/templates/model_builder/`.
- Templates
  - Base layouts in `theme/templates/` (e.g., `base.html`, `navbar.html`) with Bootstrap styling
  - Feature templates and partials under `model_builder/templates/model_builder/`
  - Save button is centralized in `side_panel_structure.html` as a `{% block save_button %}` default
- Frontend assets
  - `theme/static/scripts/` includes small utilities (loading bars, charts, leader lines)
  - CSS/SCSS in `theme/static/scss` and compiled CSS in `theme/static/css`

### Layout model
The page layout uses **flexbox** (`flex: 1 1 0; min-height: 0;` on nested containers) — not computed CSS variable heights. The browser auto-distributes remaining space. Do not reintroduce height variables like `--model-height` or `--model-canva-calculated-height`; they were intentionally removed. Hiding/showing elements (navbar, toolbar) automatically reclaims/consumes space with zero JS height manipulation.

### HTMX accordion state preservation
When OOB card swaps re-render a card, accordion open/close state is preserved automatically via `restoreAccordionStateInFragment` in `model_builder_main.js`. This handler intercepts `htmx:beforeSwap`, snapshots all currently-open accordions, modifies the incoming HTML to restore their state, then lets HTMX insert the corrected fragment. Any new OOB card swap benefits from this — no per-feature wiring needed. Do not add competing accordion-restore logic.

### Leaderline target resolution
Leaderlines use a "deepest visible anchor" pattern for target-side resolution: if the target element is hidden inside a collapsed accordion, the line ends on the nearest visible `.leaderline-anchor` ancestor instead. Lines are rebuilt broadly on `shown.bs.collapse` / `hidden.bs.collapse` events. Source-side semantics are unchanged.

### Truncated-text tooltip pattern
Any element with `.truncated-text-tooltip` + `text-truncate min-w-0` + Bootstrap tooltip attrs gets a tooltip that fires when either (a) the text is visually truncated, or (b) the visible text differs from the tooltip text. The latter covers shortened/compact labels (e.g. `add_child_button.html` with `compact=True` inside labeled sections, where the button shows "Add" / "Link existing" but the tooltip reveals the full child type). Initialized by `initTruncatedTextTooltips` in `model_builder_main.js` and re-run on `htmx:afterSettle` for swapped fragments.


## Typical request lifecycle

1) User action triggers GET/POST (often via HTMX) to a view in `adapters/views/`
2) View creates use case input from request
3) Use case executes business logic via `ModelWeb` and domain services
4) Presenter formats output as HTTP response with HTMX triggers
5) View returns response (full page or partial for DOM swap)


## Development tips

### Starting the server
- `python manage.py runserver` (see `INSTALL.md` for full setup)

### Running tests
- For best speed, run unit/integration tests first, then E2E in parallel:
  1. `poetry run pytest tests --ignore=tests/e2e`
  2. `poetry run pytest tests/e2e -n 4 --base-url http://localhost:8000` (requires running server)
- Jest: `npm run jest`
- **Flakiness:** If a test fails on the first run but passes on retry, flag it explicitly to the user as a flaky test rather than silently re-running.

### Adding new ModelingObject classes
**You should NOT need to create extension classes** - use base efootprint classes directly.

If you need to add a base efootprint class to the web interface:
1. Ensure it's in `efootprint.all_classes_in_order.ALL_EFOOTPRINT_CLASSES`
2. Add entry to `model_builder/reference_data/form_type_object.json`
3. Optionally create a web wrapper in `domain/entities/web_core/` and add to `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`
4. Run `tests/tests_structure.py` as a script to auto-generate form field entries

### Adding new timeseries generation methods
To add a new way to generate timeseries (e.g., from uploaded CSV):
1. Create new `ExplainableObject` subclass in `domain/entities/efootprint_extensions/`
2. Register with `@ExplainableHourlyQuantities.register_subclass(lambda d: ...)` using unique JSON key
3. Implement `from_json_dict()`, `to_json()`, `__init__()`, and lazy `@property value`
4. Create form template in `side_panels/dynamic_form_fields/`
5. Update `generate_dynamic_form()` to detect your new type


## Security & data

- Session-only by default; no PII expected. Do not log sensitive info.
- Validate inputs in views; trust computations to the domain engine but validate shape/types at boundaries.
