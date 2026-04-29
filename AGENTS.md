# AGENTS — e-footprint-interface

This file orients agents and contributors. It is intentionally short. Substance lives under `specs/`.

## Read this first

1. **`specs/constitution.md`** — the project's immutable rules. Every change respects them.
2. **`specs/mission.md`** — what e-footprint-interface is and isn't.
3. The companion library: `../e-footprint/` (or upstream PyPI). The interface assumes familiarity with the library's modeling concepts; when in doubt, read `../e-footprint/specs/architecture.md`.

## Where things live

| If you need... | Read |
|---|---|
| Architecture (Clean Architecture map, web wrappers, dict relationships, timeseries, persistence, render layer) | `specs/architecture.md` |
| Code style, performance preferences, agent behaviour rules | `specs/conventions.md` |
| Testing patterns (unit / integration / E2E layers, fixtures) | `specs/testing.md` |
| Tech stack and version bounds | `specs/tech_stack.md` |
| What's planned and in flight | `specs/roadmap.md` |
| The spec-driven workflow (specify → plan → tasks → implement) | `specs/workflow.md` |
| Active feature work | `specs/features/<feature-name>/` |
| Past investigations and dated decisions | `archives/` |

## Dev commands

```bash
poetry install --with dev
npm install && npm run build:result-charts:dev
poetry run python manage.py migrate
poetry run python manage.py runserver         # http://localhost:8000

# Tests
poetry run pytest tests --ignore=tests/e2e   # unit + integration
poetry run pytest tests/e2e -n 4             # E2E (requires running server)
npm run jest                                 # JS unit tests
```

For full setup options (full local / hybrid / Docker), see [`INSTALL.md`](INSTALL.md).

## Spec-driven workflow at a glance

Feature work follows four stages, each gated by your review:

1. **Specify** — write `specs/features/<name>/spec.md` (problem, scope, success criteria). Skill: `spec-specify`.
2. **Plan** — write `plan.md` (approach, affected modules, risks). Skill: `spec-plan`.
3. **Tasks** — write `tasks.md` (ordered, independently-shippable steps). Skill: `spec-tasks`.
4. **Implement** — execute one task at a time, respecting constitution gates. Skill: `task-implement`.

Investigations and ad-hoc design work are exempt; the four-stage flow is for features that ship.

## Documentation upkeep

When you implement a non-trivial pattern (new web wrapper convention, new HTMX flow, new render strategy, schema migration), update the relevant spec file (`specs/architecture.md`, `specs/conventions.md`, or `specs/testing.md`) — a one-line mention in the right section is enough. The goal is to keep specs accurate so future agents don't rediscover patterns from code.
