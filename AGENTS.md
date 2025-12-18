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
│   │   ├── web_core/          # Core entities (ModelWeb, ServerWeb, JobWeb, etc.)
│   │   ├── web_builders/      # Builder-specific entities (ExternalApiWeb, etc.)
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
│   ├── presenters/            # HtmxPresenter (formats responses)
│   ├── repositories/          # SessionSystemRepository
│   ├── forms/                 # Form parsing (form_data_parser.py) and generation (strategies)
│   └── ui_config/             # UI configuration providers
├── templates/                 # Django templates
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
  - Cypress E2E tests under `cypress/`


## Core logic and main classes

### Key files and their responsibilities

#### ModelWeb - Central orchestrator (`domain/entities/web_core/model_web.py`)
`ModelWeb` is the central web wrapper around the e-footprint domain model. It:
- Deserializes session `system_data` via `efootprint.api_utils.json_to_system`
- Wraps the resulting domain `System` into web objects (`wrap_efootprint_object`)
- Exposes typed accessors: `servers`, `services`, `jobs`, `usage_patterns`, `usage_journeys`, etc.
- Serializes back to JSON with or without calculated attributes via `to_json()`
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
Package of web wrappers around e-footprint domain classes. Each web wrapper provides template-friendly properties and form generation logic

#### Adapters
- `adapters/views/` - HTTP views (thin adapters calling use cases)
- `adapters/presenters/htmx_presenter.py` - Formats use case outputs as HTMX responses
- `adapters/repositories/session_system_repository.py` - Loads/saves system from Django session
- `adapters/forms/form_data_parser.py` - Parses HTTP form data before passing to use cases
- `adapters/forms/form_field_generator.py` - Form field generation utilities
- `adapters/ui_config/` - Provides UI configuration (class labels, field metadata)

#### Object factory (`domain/object_factory.py`)
- `create_efootprint_obj_from_parsed_data()` - Creates efootprint objects from pre-parsed form data
- `edit_object_from_parsed_data()` - Handles object updates via `ModelingUpdate`

#### Extension mechanism (`domain/entities/efootprint_extensions/`)
Specialized `ExplainableObject` subclasses that enhance e-footprint types:
- `ExplainableStartDate` - Date serialization for forms
- `ExplainableHourlyQuantitiesFromFormInputs` - Timeseries from growth rate inputs
- `ExplainableRecurrentQuantitiesFromConstant` - Recurrent timeseries from constant values


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


## Rendering in the web context

- Session-driven state: The current system model is stored in Django session as `system_data` (JSON). Each request reconstructs the domain system via `ModelWeb(repository)`.
- HTMX partials: Most UI actions trigger small HTTP requests that replace DOM snippets using templates under `model_builder/templates/model_builder/`.
- Templates
  - Base layouts in `theme/templates/` (e.g., `base.html`, `navbar.html`) with Bootstrap styling
  - Feature templates and partials under `model_builder/templates/model_builder/`
- Frontend assets
  - `theme/static/scripts/` includes small utilities (loading bars, charts, leader lines)
  - CSS/SCSS in `theme/static/scss` and compiled CSS in `theme/static/css`


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
- Python: `poetry run pytest` or `python -m pytest`
- Cypress: `npx cypress open` or `npx cypress run`

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


## Coding agents instructions

Don’t run and debug tests proactively, unless explicitly asked. After creating a new test or making significant, already tested, refactoring, pause and let me run the tests.
