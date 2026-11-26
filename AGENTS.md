# AGENTS — e-footprint-interface

This file orients agents and contributors. It is intentionally short. Substance lives under `specs/`.

## Read this first

**Always begin any codebase exploration by reading [`specs/architecture/index.html`](specs/architecture/index.html).** Use its task router, then read only the owning detail pages before exploring code. The index maps the Clean Architecture layers and routes to web wrappers, forms/relationships, persistence, workspace, rendering, onboarding, and runtime recovery.

1. **[`specs/architecture/index.html`](specs/architecture/index.html)** — the structural map and task router; follow only the relevant detail pages.
2. **`specs/constitution.md`** — the project's immutable rules. Every change respects them.
3. **`specs/mission.md`** — scope, audience, and eco-design priorities for weighing user value against complexity.
4. The companion library: `../e-footprint/` (or upstream PyPI). The interface assumes familiarity with the library's modeling concepts; when in doubt, read [`../e-footprint/specs/architecture/index.html`](../e-footprint/specs/architecture/index.html).

## Where things live

| If you need... | Read |
|---|---|
| Architecture (Clean Architecture map, web wrappers, dict relationships, timeseries, persistence, render layer) | [`specs/architecture/index.html`](specs/architecture/index.html) |
| Onboarding examples, picker and guided tour | [`specs/architecture/onboarding.html`](specs/architecture/onboarding.html) |
| AI-assisted bootstrap generation, its Web only / Web + edge scope, provider boundary, entry points, active-slot replacement and transient summary | [`specs/architecture/layers-and-wrappers.html#ai-bootstrap`](specs/architecture/layers-and-wrappers.html#ai-bootstrap) · [`specs/architecture/onboarding.html`](specs/architecture/onboarding.html) · [`specs/architecture/workspace.html#ai-bootstrap-slot`](specs/architecture/workspace.html#ai-bootstrap-slot) · [`specs/architecture/rendering.html`](specs/architecture/rendering.html) |
| Simplified-input fields, authoring and per-model configuration | [Catalog](specs/architecture/forms-and-relationships.html#simplified-input-catalog) · [Inline bookmarks and Sources](specs/architecture/forms-and-relationships.html#inline-bookmarks) · [Workspace and Configure exits](specs/architecture/workspace.html#simplified-workspace) · [Focused timeseries](specs/architecture/timeseries.html#focused-simplified-editor) · [Saved-state export](specs/architecture/persistence.html#backend-payloads-and-computation-boundaries) |
| Conditional choice rendering, shared editor repair, and bounded repair notices | `specs/architecture/forms-and-relationships.html` and `specs/architecture/rendering.html` |
| Internal-object inspection panels and canvas-card presence (adapter-owned placement and edit refresh planning) | `specs/architecture/forms-and-relationships.html` and `specs/architecture/rendering.html` |
| Code style, performance preferences, agent behaviour rules | `specs/conventions.md` |
| Testing patterns (unit / integration / E2E layers, fixtures) | `specs/testing.md` |
| Tech stack and version bounds | `specs/tech_stack.md` |
| What's planned and in flight | `specs/roadmap.md` |
| The spec-driven workflow (specify → plan → tasks → implement → archive) and the forms of a feature's files | `specs/workflow.md`, `specs/workflow-formats.md` |
| The comprehension tools (the narrative and plan pages, the map), how they are installed, and what this project gives them | [`comprehension_harness/README.md`](comprehension_harness/README.md), `comprehension.config.json`, `.agents/repository.md` § "The stack" |
| Journeys drawn from a run of a browser test (how to write one, what it runs on, how its page is rendered) | `specs/testing.md` § "Journey tests", `.agents/repository.md` § "The stack" |
| Shared workflow, agent roles, and usage tooling | [`specs/agent-tooling.md`](specs/agent-tooling.md) |
| Visual user-journey docs — the design hub (how the user moves through each flow) | `specs/design/` (start at `index.html`); live unlinked catalogue at `/design` |
| Reference modeling of this interface's own operation (usage sessions, benchmark operations, deployment and traffic assumptions) | `specs/e-footprint-modeling/README.md` |
| UI and design-document copy conventions | `specs/design/writing-style-guide.md` |
| LinkedIn post drafts and captioned demo video scripts | `communications/README.md` and `communications/video/README.md` |
| Active feature work | `specs/features/<feature-name>/` |
| A `plan.html` of the earlier form: source links, one-click reproduction debugging, decision indexes and callouts | `.agents/skills/spec-plan/references/plan-review-links.md`, `.agents/skills/spec-plan/references/plan-decision-callouts.md`, and `tools/vscode-plan-review-links/README.md` |
| Past investigations and dated decisions | `archives/` |

In feature plans, HTML documentation links open in a new browser tab; production source links (including HTML templates) open in VS Code. See the plan-link convention above.

Composite forms expose owner–field pairs through their strategies; wrappers declare nested input owners. See [Forms and relationships](specs/architecture/forms-and-relationships.html#form-adapters).

## Dev commands

```bash
poetry install --with dev
npm install && npm run build:js:dev
poetry run python manage.py migrate
poetry run python manage.py runserver         # http://localhost:8000

# Tests
poetry run pytest --ignore=tests/e2e         # unit + integration, and the comprehension stack's own tests
poetry run pytest tests/e2e -n 4             # E2E (requires running server)
poetry run pytest tests/e2e/journeys         # the journeys, on their own server; then npm run journey:render
npm run jest                                 # JS unit tests
```

## Frontend assets

Simplified-input client modules live in `theme/static/scripts/simplified_inputs/`; rebuild their bundle with `npm run build:js:dev` after editing. See `specs/conventions.md` for module ownership.

Never edit `theme/static/css/bs_main.css` by hand — it is compiled from `theme/static/scss/`. Edit the SCSS source and recompile with `npm run watch` (or a one-shot `npx sass theme/static/scss/main.scss:theme/static/css/bs_main.css --load-path=node_modules/bootstrap/scss`).

For full setup options (full local / hybrid / Docker), see [`INSTALL.md`](INSTALL.md).

## Spec-driven workflow at a glance

Feature work follows five stages, with a person approving between them. `specs/workflow.md` says
what each is for and who approves what.

1. **Specify** — `specs/features/<name>/spec.md`: the problem, the change, the rules no screen shows. Skill: `spec-specify`.
2. **Plan** — the plan is written into the code as pieces (planned calls, planned tests) and a short `plan.md`; the reviewer reads the plan page generated from them and approves it. Skill: `spec-plan`.
3. **Tasks** — the delivery: the pieces cut into lots, with the unit tests of each. Skill: `spec-tasks`.
4. **Implement** — the delivery, lot by lot: each built, checked against the approved plan, reviewed; one lot alone when asked. Skills: `feature-implement`, `task-implement`, `task-review`.
5. **Archive** — the few load-bearing decisions promoted to the reference docs, the feature's marks stripped off the code, the feature folder deleted. Skill: `feature-archive`.

Stages 2 to 4 run on the Python stack of the comprehension tools: the `narrate`, `event`,
`planned` and `built` calls of `model_builder/narrate.py`, and the test declarations and the commands of
`comprehension_harness/python/` (`.agents/repository.md` § "The stack" says how each is spelled).
`model_builder/narrate.py` is this project's copy of the stack's reference file: product code
imports the calls from it, and nothing of the harness.
An older handwritten `plan.html` and its `tasks.md` are ported to the current format before
delivery resumes.

Investigations and ad-hoc design work are exempt; the staged flow is for features that ship.
Conversational bug batches use `bug-fixes` (a diagnostic a bug, and the reproduction that fails today), then `bug-fixes-plan` (the plan in pieces, a section a bug, with its delivery), followed by the implement and archive stages. A batch has no tasks stage.

## Documentation upkeep

Keep explanations in their canonical homes, following `specs/workflow.md` § "Documentation ownership":
execution and recurring patterns in narratives, structuring decisions in architecture, local semantics
beside code. Update the owning explanation when it changes, removing duplication as material is touched.

## Production maintenance workers

Long-running periodic maintenance commands run as dedicated Supervisor programs in `docker/conf/supervisord-prod.conf`.
They perform their first pass immediately, own their repeat interval, remain safe when multiple web scalers overlap, and
log aggregate counts and duration only—never cache keys, session identifiers, or payloads.

## Git commit style

Prefix your commit messages with the relevant tag among [FIX], [REFACTO], [ADD], [REMOVE], [OPTIM], [UPDATE]. The user might specify another tag. Always use brackets and uppercase. Example: `[FIX] Handle missing data in timeseries rendering`.
