# AGENTS — e-footprint-interface

This file orients agents and contributors. It is intentionally short. Substance lives under `specs/`.

## Read this first

**Always begin any codebase exploration by reading [`specs/architecture/index.html`](specs/architecture/index.html).** Use its task router, then read only the owning detail pages before exploring code. The index maps the Clean Architecture layers and routes to web wrappers, forms/relationships, persistence, workspace, rendering, onboarding, and runtime recovery.

1. **[`specs/architecture/index.html`](specs/architecture/index.html)** — the structural map and task router; follow only the relevant detail pages.
2. **`specs/constitution.md`** — the project's immutable rules. Every change respects them.
3. **`specs/mission.md`** — what e-footprint-interface is and isn't.
4. The companion library: `../e-footprint/` (or upstream PyPI). The interface assumes familiarity with the library's modeling concepts; when in doubt, read [`../e-footprint/specs/architecture/index.html`](../e-footprint/specs/architecture/index.html).

## Where things live

| If you need... | Read |
|---|---|
| Architecture (Clean Architecture map, web wrappers, dict relationships, timeseries, persistence, render layer) | [`specs/architecture/index.html`](specs/architecture/index.html) |
| Onboarding examples, picker and guided tour | [`specs/architecture/onboarding.html`](specs/architecture/onboarding.html) |
| Simplified-input fields, authoring and per-model configuration | [Catalog](specs/architecture/forms-and-relationships.html#simplified-input-catalog) · [Inline bookmarks and Sources](specs/architecture/forms-and-relationships.html#inline-bookmarks) · [Workspace and Configure exits](specs/architecture/workspace.html#simplified-workspace) · [Persistence](specs/architecture/persistence.html) |
| Code style, performance preferences, agent behaviour rules | `specs/conventions.md` |
| Testing patterns (unit / integration / E2E layers, fixtures) | `specs/testing.md` |
| Tech stack and version bounds | `specs/tech_stack.md` |
| What's planned and in flight | `specs/roadmap.md` |
| The spec-driven workflow (specify → plan → tasks → implement) | `specs/workflow.md` |
| Shared workflow, agent roles, and usage tooling | [`specs/agent-tooling.md`](specs/agent-tooling.md) |
| Visual user-journey docs — the design hub (how the user moves through each flow) | `specs/design/` (start at `index.html`); live unlinked catalogue at `/design` |
| Reference modeling of this interface's own operation (usage sessions, benchmark operations, deployment and traffic assumptions) | `specs/e-footprint-modeling/README.md` |
| UI and design-document copy conventions | `specs/design/writing-style-guide.md` |
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

## Styles

Never edit `theme/static/css/bs_main.css` by hand — it is compiled from `theme/static/scss/`. Edit the SCSS source and recompile with `npm run watch` (or a one-shot `npx sass theme/static/scss/main.scss:theme/static/css/bs_main.css --load-path=node_modules/bootstrap/scss`).

For full setup options (full local / hybrid / Docker), see [`INSTALL.md`](INSTALL.md).

## Spec-driven workflow at a glance

Feature work follows four stages. Review the spec, plan and tasks before implementation;
an authorized `feature-implement` run then completes implementation and reviews autonomously,
recording only consequential decisions in context in the plan.

1. **Specify** — write `specs/features/<name>/spec.html` (problem, scope, success criteria). Skill: `spec-specify`.
2. **Plan** — write `plan.html` (approach, affected modules, risks). Skill: `spec-plan`.
3. **Tasks** — write `tasks.md` (ordered, independently-shippable steps). Skill: `spec-tasks`.
4. **Implement** — execute one task at a time, respecting constitution gates. Skill: `task-implement`.

Investigations and ad-hoc design work are exempt; the four-stage flow is for features that ship.
Conversational bug batches use `bug-fixes`: diagnostics plus `tasks.md`, followed by the normal implement/review/archive stages.
`feature-implement` also follows the active experiment linked from [`.agents/repository.md`](.agents/repository.md), using the library's shared five-feature observation record.

## Documentation upkeep

When you implement a non-trivial pattern (new web wrapper convention, new HTMX flow, new render strategy, schema migration), update the owning architecture detail page (routed from [`specs/architecture/index.html`](specs/architecture/index.html)), `specs/conventions.md`, or `specs/testing.md` — a one-line mention in the right section is enough. The goal is to keep specs accurate so future agents don't rediscover patterns from code.

## Production maintenance workers

Long-running periodic maintenance commands run as dedicated Supervisor programs in `docker/conf/supervisord-prod.conf`.
They perform their first pass immediately, own their repeat interval, remain safe when multiple web scalers overlap, and
log aggregate counts and duration only—never cache keys, session identifiers, or payloads.

## Git commit style

Prefix your commit messages with the relevant tag among [FIX], [REFACTO], [ADD], [REMOVE], [OPTIM], [UPDATE]. The user might specify another tag. Always use brackets and uppercase. Example: `[FIX] Handle missing data in timeseries rendering`.
