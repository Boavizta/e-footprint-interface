# AGENTS — e-footprint-interface

This document orients AI/code agents and new contributors. It explains how the repository works, the main code style guidelines, the core logic and classes, how rendering happens in the web context, and the main technological choices.

## What this repository is

A Django-based web UI for the e-footprint modeler/engine. It embeds:
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
2) Views (mostly in `model_builder/views*.py`) mutate/serialize a "system" in session
3) `ModelWeb` wraps the domain model and exposes web-friendly accessors
4) Templates render partials/sidenav/forms/charts; JS augments UX where needed


## Code style & conventions

- Python
  - Formatter/lint: follow `.pylintrc`; prefer PEP 8; type hints where helpful
  - Keep functions small; raise explicit errors with actionable messages
  - Web-entry code avoids heavy computations; delegate to `efootprint` domain classes
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
- Git
  - Write concise, purpose-driven commit messages; avoid committing secrets


## Core logic and main classes

Most of the web-facing orchestration lives in `model_builder/`.

Key files:
- `model_builder/model_web.py`
  - `ModelWeb` is the central web wrapper around the e-footprint domain model. It:
    - Deserializes session `system_data` via `efootprint.api_utils.json_to_system`
    - Wraps the resulting domain `System` into web objects (`wrap_efootprint_object`)
    - Exposes typed accessors: `servers`, `services`, `jobs`, `usage_patterns`, `usage_journeys`, etc.
    - Serializes back to JSON with or without calculated attributes via `to_json()`
    - Maintains a flat index of objects (`flat_efootprint_objs_dict`) for quick lookups
    - Provides convenience getters by type or ID and can inject default objects on demand
    - Computes daily emissions timeseries aggregating energy and fabrication impacts (`system_emissions`)
  - Important constants and helpers:
    - `MODELING_OBJECT_CLASSES_DICT` merges e-footprint classes + local extensions
    - `DEFAULT_OBJECTS_CLASS_MAPPING` to seed networks/devices/countries
    - `ATTRIBUTES_TO_SKIP_IN_FORMS` to filter technical attributes out of forms
- `model_builder/modeling_objects_web.py`
  - Web wrappers (`wrap_efootprint_object`, `ExplainableObjectWeb`) that adapt domain objects to template-friendly shapes and provide computed properties for display
- `model_builder/model_builder_utils.py`
  - Utilities for timeseries alignment, rounding, and date-window computations used by charts and summaries
- Views and CRUD layers:
  - `model_builder/addition/views_addition.py`, `model_builder/edition/...`, `model_builder/views_deletion.py`, and `model_builder/views.py` implement the flows to create/edit/delete objects and sections. They return full pages or HTMX partials.
- Extensions:
  - `model_builder/efootprint_extensions/usage_pattern_from_form.py` adds web-only helpers (e.g., create UsagePattern from dynamic form data)

Relevant upstream domain classes (from `efootprint`):
- Modeling objects like `ServerBase`/`Server`, `GPUServer`, `Service` types, `JobBase`, `UsageJourney`, `UsageJourneyStep`, `UsagePattern`, `Network`, `Device`, `Country` and their explainable/calculated quantities (`ExplainableQuantity`, `ExplainableHourlyQuantities`)


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


## Main technological choices

- Backend: Django
  - Rationale: mature, batteries-included, session management, templating, static handling, robust testing
- Domain engine: e-footprint (Python package)
  - Rationale: dedicated carbon/energy modeling with explainability and reproducible calculations
- Frontend: Bootstrap + HTMX + lightweight JS
  - Rationale: simple mental model, server-driven UI with partial updates; avoids heavy SPA complexity
- Testing: pytest/unittest for Python (`tests/`), Cypress for E2E (`cypress/`)
- Packaging: Poetry + `pyproject.toml`; `requirements.txt` maintained for deployment compatibility
- CI: GitHub Actions (`.github/workflows/ci.yml`)
- Deployment: `app.yaml` hints at App Engine-like deployment; see `DEPLOY_TO_PROD.md`


## Typical request lifecycle

1) User action triggers GET/POST (often via HTMX) to a view in `model_builder/…views*.py`
2) View instantiates `ModelWeb(request.session)`
3) View reads/modifies objects through `ModelWeb`/wrappers and saves back to session using `update_system_data_with_up_to_date_calculated_attributes()`
4) View returns a template (full page) or partial (for a DOM swap)


## Development tips

- Start the server: `python manage.py runserver` (see `INSTALL.md` for full setup)
- Tests
  - Python: `pytest` or `python -m pytest`
  - Cypress: `npx cypress open` or `npx cypress run`
- When adding new modeling objects, extend `MODELING_OBJECT_CLASSES_DICT` (usually by importing new classes) and create templates/partials for forms and display
- Keep forms dynamic and DRY by using `side_panels/dynamic_form_fields/*` partials
- For computed/calculated fields, prefer rendering through explainable objects templates so users can understand the provenance


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


## Where to look next

- `README.md` for quick overview
- `INSTALL.md` to run locally
- `tests/` and `cypress/` for behavior examples and expected flows
- `model_builder/model_web.py` and `model_builder/templates/model_builder/` to understand how data becomes UI
