# Tech stack — e-footprint-interface

## Language and runtime

- **Python ≥ 3.12** (declared in `pyproject.toml` as `^3.12`).
- **Poetry** for Python dependency management.
- **Node.js** + **npm** for the asset pipeline (Bootstrap compilation, JS bundling for the result charts).

## Backend

| Library | Why | Version |
|---|---|---|
| **Django** | Web framework. Views are thin adapters in Clean Architecture. | `^5.0` |
| **efootprint** | The modeling engine. Wrapped by `ModelWeb`. | `20.0.2` (pinned, PyPI) |
| **django-environ** | Settings via env vars. | `^0` |
| **psycopg2-binary** | PostgreSQL driver (production). | `^2.9` |
| **django-bootstrap5** | Bootstrap 5 form rendering. | `^24.3` |
| **django-browser-reload** | Auto-reload during dev. | `^1.12.1` |
| **gunicorn** | WSGI server in production. | `^23` |
| **redis** | Session/cache backend (production). | `^5.0` |
| **openpyxl** | xlsx export of source tables. | `^3` |
| **orjson** | Fast JSON for system snapshots. | `^3.11` |

## Frontend

- **HTMX** — partial-update interactivity model (constitution §1.4). No SPA framework.
- **Bootstrap 5** — UI components.
- **Vanilla JavaScript** — small utilities (loading bars, leader lines, charts wiring). No frontend framework.
- **SCSS** under `theme/static/scss/`, compiled to `theme/static/css/` via `npm run watch`.
- **Webpack** bundling for the result charts (`theme/static/scripts/result_charts/` → `theme/static/bundles/`).

## Persistence

- **SQLite** for full-local development (Option 1 in `INSTALL.md`).
- **PostgreSQL** for hybrid local development (Option 2) and production.
- **Django session** is authoritative for the current modeling state. The session is backed by Redis in production, file-based in dev.
- **Modeling system data** is JSON-serialized via `efootprint.api_utils.system_to_json` and stored in the session (or in the `InMemorySystemRepository` for tests).

## Testing

- **pytest** for Python tests. Layers: `tests/unit_tests`, `tests/integration`, `tests/e2e`.
- **Playwright** + **pytest-playwright** for end-to-end browser tests (Chromium by default).
- **Jest** + **jsdom** for JavaScript unit tests.
- **InMemorySystemRepository** for layer-isolated integration tests (no Django, no browser).

## Hosting and deployment

- **Clever Cloud** — PostgreSQL + Docker. Two environments: PreProd (`dev.e-footprint.boavizta.org`) and Production (`e-footprint.boavizta.org`).
- **Docker** — container images built from `Dockerfile`. Local dev can also run a full Docker stack via `docker-compose.yml`.
- **Traefik** — reverse proxy in the local Docker setup.

## Tooling

- **Pylint** for linting; follow `.pylintrc`.
- **PEP 8** + line length **120**. Prefer double quotes for strings.
- **mkdocs** is **not** used in this repo (the library has its own mkdocs site).

## Distribution

- License: **Apache-2.0**.
- Source: https://github.com/Boavizta/e-footprint-interface.

## Versioning policy

- Semantic versioning: `MAJOR.MINOR.PATCH`.
- A schema change in `interface_config` (top-level UI state in cached JSON) requires an `efootprint_interface_version` bump and a migration handler in `version_upgrade_handlers.py`.
- New features without schema impact are `MINOR`.
- Bug fixes are `PATCH`.

## Out of scope

- Replacing Django, HTMX, Bootstrap, or Playwright (constitution §4).
- SPA migration (constitution §4).
- i18n.
