# AGENTS — e-footprint-interface

This document orients AI/code agents and new contributors. It explains how the repository works, the main code style guidelines, the core logic and classes, how rendering happens in the web context, and the main technological choices.

## What this repository is

A Django-based web UI for the digital service carbon footprint model [e-footprint](https://github.com/Boavizta/e-footprint). It embeds:
- A Python/Django backend orchestrating sessions, model building, and HTTP views
- A Bootstrap/HTMX frontend for dynamic, partial-page updates and a lightweight SPA feel
- Templates and small JS utilities to render forms, charts, and explainable results

Upstream domain logic (carbon/energy modeling) is provided by the e-footprint Python package and is adapted/wrapped for the web here.


## High-level architecture

- Django project roots:
  - `e_footprint_interface/` — Django project settings, ASGI/WSGI, URL routing, middleware
  - `model_builder/` — App responsible for UI flows, forms, model manipulation, views, and templates
  - `theme/` — Static assets (Bootstrap, SCSS/CSS, icons, scripts) and base templates
  - `tests/` — Python tests (unit/integration); `cypress/` — E2E tests (browser-based)
- External engine: `efootprint` (PyPI / source) — domain classes and computations

Flow in short:
1) User interacts with pages (HTMX requests, forms, buttons) → Django views
2) Views (mostly in `model_builder/views*.py`) mutate/serialize a modeling saved as a dictionary in the user’s session data, under the "system_data" key.
3) `ModelWeb` wraps the domain model and exposes web-friendly `ModelingObjectWeb` accessors. Web-entry code avoids heavy computations; all modeling logic is delegated to `efootprint` domain classes.
4) Templates render partials/sidenav/forms/charts; JS augments UX where needed


## Code style & conventions

- AI agents
  - Favor making all edits on the same file at once rather than step-by-step changes.
  - **Always propose computationally efficient solutions**, especially for data processing and numerical operations:
    - Prefer vectorized NumPy operations over Python loops
    - Use single-pass algorithms (e.g., `np.bincount`) over multiple iterations
    - When presenting solutions, include complexity analysis (e.g., O(n) vs O(n²))
    - Present trade-offs between readability and performance when relevant
    - For critical paths, offer multiple implementation options with pros/cons:
      - Most efficient (may be less readable)
      - Balanced (good performance, maintainable)
      - Most readable (acceptable performance for non-critical code)
- Python
  - Formatter/lint: follow `.pylintrc`; prefer PEP 8; type hints where helpful
  - Keep functions small; raise explicit errors with actionable messages
  - Keep number of lines low; prefer to write long lines while respecting the 120 characters limit, rather than writing each parameter on a new line.
  - **Performance**: For array/data operations, prioritize NumPy vectorization over list comprehensions or loops
- Django
  - Views: thin controllers calling helpers in `model_builder/*_utils.py`
  - Templates: small, composable partials (see `model_builder/templates/model_builder/...`)
  - Keep session data authoritative for the current modeling "system"
- JavaScript
  - Vanilla JS + small helpers only; keep logic minimal; prefer progressive enhancement
  - Use HTMX attributes for partial updates over large custom JS
- Tests
  - Python tests go under `tests/` (and app-specific subfolders)
  - Cypress E2E tests under `cypress/`


## Core logic and main classes

Most of the web-facing orchestration lives in `model_builder/`.

### Key files and their responsibilities

#### ModelWeb - Central orchestrator (`model_builder/web_core/model_web.py`)
`ModelWeb` is the central web wrapper around the e-footprint domain model. It:
- Deserializes session `system_data` via `efootprint.api_utils.json_to_system`
- Wraps the resulting domain `System` into web objects (`wrap_efootprint_object`)
- Exposes typed accessors: `servers`, `services`, `jobs`, `usage_patterns`, `usage_journeys`, etc.
- Serializes back to JSON with or without calculated attributes via `to_json()`
- Maintains a flat index of objects (`flat_efootprint_objs_dict`) for quick lookups
- Provides convenience getters by type or ID and can inject default objects on demand
- Computes daily emissions timeseries aggregating energy and fabrication impacts (`system_emissions`)

#### Class registries
- `model_builder/all_efootprint_classes.py` - `MODELING_OBJECT_CLASSES_DICT` merges e-footprint classes (no extension classes needed anymore)
- `model_builder/efootprint_to_web_mapping.py` - Maps e-footprint class names to web wrappers via `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`

#### Web wrappers (`model_builder/web_core/`)
Package of web wrappers around e-footprint domain classes:
- `ServerWeb`, `JobWeb`, `UsagePatternWeb`, `EdgeUsagePatternWeb`
- `RecurrentEdgeDeviceNeedWeb` (handles `RecurrentEdgeProcess` and `RecurrentEdgeWorkload`)
- Each web wrapper provides template-friendly properties and form generation logic

#### Views and CRUD (`model_builder/`)
- `addition/...` - Object creation flows
- `edition/...` - Object editing flows
- `views_deletion.py` - Object deletion logic
- `views.py` - Main views and helpers
- `object_creation_and_edition_utils.py` - Core CRUD utilities:
  - `create_efootprint_obj_from_post_data()` - Handles form POST data → efootprint objects
  - `edit_object_in_system()` - Handles object updates via `ModelingUpdate`

#### Form generation system (`model_builder/class_structure.py`)
- `generate_object_creation_structure()` - Creates form structure for object creation
- `generate_dynamic_form()` - **Core form generation logic**:
  - Introspects class `__init__` signatures to determine field types
  - Detects timeseries types (see "Timeseries handling" section below)
  - Generates appropriate form fields based on annotation types
  - Preserves field order, with timeseries fields appearing last
  - Returns form structure + dynamic data for JS interactions

#### Extension mechanism (`model_builder/efootprint_extensions/`)
The extension package allows creating specialized `ExplainableObject` subclasses that enhance e-footprint types:
- **NOT for ModelingObject subclasses** - Use base efootprint classes directly (e.g., `UsagePattern`, `RecurrentEdgeProcess`)
- **FOR ExplainableObject subclasses** - To provide alternative serialization/computation strategies

**Current extensions:**
- `ExplainableStartDate` - Date serialization for forms
- `ExplainableHourlyQuantitiesFromFormInputs` - Timeseries from growth rate inputs (see below)
- `ExplainableRecurrentQuantitiesFromConstant` - Recurrent timeseries from constant values (see below)

### Timeseries handling (important!)

**Old approach (DEPRECATED):** "FromForm" wrapper classes (`UsagePatternFromForm`, `RecurrentEdgeProcessFromForm`, etc.) that computed timeseries in `__init__`.

**Current approach:** Timeseries generation is handled by `ExplainableObject` subclasses registered to the base timeseries types:

#### ExplainableHourlyQuantitiesFromFormInputs
- **Purpose:** Generate hourly timeseries from simple form inputs (start date, duration, initial volume, growth rate)
- **Registration:** Matches JSON with `"form_inputs"` key containing `"type": "growth_based"`
- **Storage:** Stores both form inputs (for editing) AND computed compressed timeseries
- **Lazy evaluation:** Computes timeseries only when `.value` accessed; caches result
- **Usage:** Automatically detected by `generate_dynamic_form()` when `default_values` contains this type

#### ExplainableRecurrentQuantitiesFromConstant
- **Purpose:** Generate 168-element recurrent array from single constant value
- **Registration:** Matches JSON with `"constant_value"` and `"constant_unit"` keys
- **Storage:** Stores constant value (for editing) AND computed recurring_values array
- **Lazy evaluation:** Generates 168-element array when `.value` accessed; caches result
- **Usage:** Automatically detected by `generate_dynamic_form()` when `default_values` contains this type

#### How form generation detects timeseries types:
```python
# In generate_dynamic_form():
if issubclass(annotation, ExplainableHourlyQuantities):
    default = default_values[attr_name]
    if isinstance(default, ExplainableHourlyQuantitiesFromFormInputs):
        input_type = "hourly_quantities_from_growth"  # Editable compound form
    else:
        input_type = "timeseries_input"  # Read-only display

elif issubclass(annotation, ExplainableRecurrentQuantities):
    if isinstance(default, ExplainableRecurrentQuantitiesFromConstant):
        input_type = "recurrent_quantities_from_constant"  # Editable single value
    else:
        input_type = "recurrent_timeseries_input"  # Read-only display
```

#### Form templates for timeseries:
- `side_panels/dynamic_form_fields/hourly_quantities_from_growth.html` - Compound form (start date, duration, volume, growth rate)
- `side_panels/dynamic_form_fields/recurrent_quantities_from_constant.html` - Simple constant value input
- `side_panels/dynamic_form_fields/timeseries_input.html` - Read-only display (base efootprint class)
- `side_panels/dynamic_form_fields/recurrent_timeseries_input.html` - Read-only display (base efootprint class)


## Rendering in the web context

- Session-driven state: The current system model is stored in Django session as `system_data` (JSON). Each request reconstructs the domain system via `ModelWeb(session)`.
- HTMX partials: Most UI actions trigger small HTTP requests that replace DOM snippets using templates under `model_builder/templates/model_builder/`. Examples: side panels for add/edit, forms, charts, calculated-attributes panels.
- Templates
  - Base layouts in `theme/templates/` (e.g., `base.html`, `navbar.html`) with Bootstrap styling
  - Feature templates and partials under `model_builder/templates/model_builder/` including:
    - `side_panels/` (add/edit panels, dynamic form fields)
    - `edit/calculated_attributes/` (explainable objects, charts, formula explanations)
    - `usage_pattern/` (timeseries charts/forms)
    - `calculus_graph.html` and `model_builder_main.html` for main canvas and graph rendering
- Frontend assets
  - `theme/static/scripts/` includes small utilities (loading bars, charts, leader lines, hammer utils, dynamic forms)
  - CSS/SCSS in `theme/static/scss` and compiled CSS in `theme/static/css`
- Charts and results
  - Daily emissions series derived by `ModelWeb.system_emissions`; rendered via templates + JS chart helper in `theme/static/scripts/result_charts.js`
  - Explainable attributes rendered with dedicated templates to drill down drivers and formulae


## Typical request lifecycle

1) User action triggers GET/POST (often via HTMX) to a view in `model_builder/…views*.py`
2) View instantiates `ModelWeb(SessionSystemRepository(request.session))`
3) View reads/modifies objects through `ModelWeb`/wrappers and saves back to session using `update_system_data_with_up_to_date_calculated_attributes()`
4) View returns a template (full page) or partial (for a DOM swap)


## Development tips

### Starting the server
- `python manage.py runserver` (see `INSTALL.md` for full setup)

### Running tests
- Python: `pytest` or `python -m pytest`
- Cypress: `npx cypress open` or `npx cypress run`

### Adding new ModelingObject classes
**You should NOT need to create extension classes** - use base efootprint classes directly. The form generation system automatically handles timeseries and other complex types.

If you need to add a base efootprint class to the web interface:
1. Ensure it's in `efootprint.all_classes_in_order.ALL_EFOOTPRINT_CLASSES`
2. Add entry to `model_builder/reference_data/form_type_object.json`
3. Optionally create a web wrapper in `model_builder/web_core/` and add to `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`
4. Run `tests/tests_structure.py` as a script to auto-generate form field entries in `form_fields_reference.json`

### Adding new timeseries generation methods
To add a new way to generate timeseries (e.g., from uploaded CSV):
1. Create new `ExplainableHourlyQuantities` or `ExplainableRecurrentQuantities` subclass in `model_builder/efootprint_extensions/`
2. Register with `@ExplainableHourlyQuantities.register_subclass(lambda d: ...)` using unique JSON key
3. Implement `from_json_dict()`, `to_json()`, `__init__()`, and lazy `@property value`
4. Create form template in `side_panels/dynamic_form_fields/`
5. Update `generate_dynamic_form()` to detect your new type and set appropriate `input_type`
6. Update `create_efootprint_obj_from_post_data()` to handle POST data for your type

### Form development
- Keep forms dynamic and DRY by using `side_panels/dynamic_form_fields/*` partials
- For computed/calculated fields, prefer rendering through explainable objects templates so users can understand the provenance
- Timeseries fields are automatically placed last in forms - don't manually reorder them


## Repository map (selected)

- Django project: `e_footprint_interface/`
- App & logic: `model_builder/`
  - `model_web.py`, `model_builder_utils.py`, `modeling_objects_web.py`
  - `addition/`, `edition/`, `views*.py`, `urls.py`
  - `templates/model_builder/...` partials and pages
- Frontend assets: `theme/static/...`, base templates in `theme/templates/...`
- Tests: `tests/` (Python), `cypress/` (E2E), `js_tests/` (JS)


## Security & data

- Session-only by default; no PII expected. Do not log sensitive info.
- Validate inputs in views; trust computations to the domain engine but validate shape/types at boundaries.
