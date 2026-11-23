# Repository-specific workflow guidance — e-footprint-interface

This file is this repository's own: no synchronization writes it. The skills under
`.agents/skills/` and the roles under `.agents/roles/` are written for any project and read what
is particular to this one here. `AGENTS.md` stays the entry point and wins where the two differ.

## Documents

- **Rules**: `specs/constitution.md` (§1 the engineering principles, §2 the quality gates, §3 the
  agent-facing rules), `specs/conventions.md`, `specs/testing.md`. They are authoritative; no
  skill weakens a gate.
- **Architecture**: `specs/architecture/index.html` is the entry point. Read the index, then only
  the owning pages. Use its task router and the actual page names; never invent a documentation
  path.
- **Feature shaping**: apply
  [the mission's eco-design and feature priorities](../specs/mission.md#eco-design-and-feature-choices)
  before fixing scope. Prefer lean capabilities and negligible extra user effort over complex
  convenience machinery; preserve saved-state correctness, and assess runtime and resource costs
  separately.
- **A feature folder** is `specs/features/<feature>/`. What is in flight: `specs/roadmap.md`
  § "Active streams", which names each folder and its stage. Re-touch its entry at each stage.
- **Parked work**: a topic folder under `specs/backlog/` (its `README.md` says what a topic
  holds), or a horizon of `specs/roadmap.md`.
- **Tooling**: `specs/agent-tooling.md` (the shared files and their synchronization, the roles'
  adapters, the usage ledger).

## The stack

The Python stack of the comprehension harness is written to its contract
(`comprehension_harness/stack.md`), and `comprehension.config.json` names its commands. One flow
is narrated, the AI-assisted bootstrap (`tests/narratives/test_ai_bootstrap.py`); the others
have no narrative yet. The same flow has the one journey drawn from a run, *Start a modeling
with AI* (`tests/e2e/journeys/test_start_a_modeling_with_ai.py`). A feature in flight on `plan.html` and `tasks.md` is finished by hand or
ported; a bug batch keeps its own form (`bug-fixes`, `bug-fixes-plan`).

| The method says | Here |
|---|---|
| The three calls | `from model_builder.narrate import narrate, event, planned`, always by name. The file is this project's copy of `comprehension_harness/python/narrate.py`, held identical by a test and never edited here. Standard library only, so `domain/` and `application/` import it; inert unless a test run installed the collector. The sentence is a literal string and the watch a lambda, `narrate("…", lambda: {"count": n})`: the index refuses anything Python would compute in production |
| A place that changes, a place that goes, a shell | `planned("<feature>#<slug>", "<sentence>")` on existing code; `planned.remove(…)` in a function that goes; a shell is a new function whose whole body, under an optional docstring, is the `planned` call then `raise NotImplementedError("planned: <feature>#<slug>")`. One call a line |
| Evidence of a bug, and what a place should see | `planned.evidence("<feature>#<slug>", "<what is seen here today>", lambda: {…}, expect={…})`, on the line the bug shows at; `expect=` on a `planned(…)` call too. `expect` is a literal dict, a key of the watch each: the index reads it from the source |
| A call in a template | `{% load narrate %}` of `model_builder/templatetags/narrate.py`, then one tag a line: `{% narrate "…" key=value %}`, `{% event "…" %}`, `{% planned "<feature>#<slug>" "…" key=value expect key="literal" %}`, `{% evidence "<feature>#<slug>" "…" key=value expect key="literal" %}`. The pairs are the watch; the tag renders nothing. On a template line that runs, a site is a tag, never a comment |
| A reproduction | `@reproduces("<feature>#<slug>: <title> [<rule>]")` of `declare.py` on a written test that fails today: a run expects the failure, strictly. Built, it becomes `@titled("…")` under the same title. It observes, then asserts once at its end |
| A planned test | `@planned_test("<feature>#<slug>: <title> [<rule>]")` of `comprehension_harness/python/declare.py` on a test function with an empty body: skipped by a run, listed by the plan |
| A written test of a plan | The same title under `@titled("…")` once the body is written: `@planned_test` refuses a body. A test with neither is titled by its function's name, and a parametrized case adds pytest's `[case]` |
| A narrative, its reference case | A test class under `@narrative("<title>")` of the same `declare.py`, in a file under `tests/narratives/`; `@narrative.mechanism("<title>")` for a mechanism. Its summary is the first paragraph of the class docstring. Its reference case is its first test, or the one marked `@canonical`; a reference case is not parametrized |
| What each test crossed | `comprehension_harness/python/collector.py`, a pytest plugin `tests/conftest.py` loads for every run, under pytest-xdist too: one story file a test file under `node_modules/.cache/comprehension_harness/stories/` |
| The source index, the test titles, the watch | `source_index.py`, `titles.py` and `watch.py` of `comprehension_harness/python/`: the three commands of the configuration, standard library only, run as `python3 -m comprehension_harness.python.<name>`. The index reads the Python files of the product folders; a JavaScript file has no site and no stand |
| A symbol in a sentence | A name the index can place: an import of the file, a local of the function, a top-level declaration. A method or a dotted name stays plain: name its class. A backticked name shaped like a declaration (`CamelCase`, or words joined by `_`) that the index cannot place fails `--check`, so a dict key, a field or a method is written without backticks |
| A journey | A test class under `@journey("<name>", who=…, wants=…, now=…)` of `comprehension_harness/python/journey.py`, in a file under `tests/e2e/journeys/`; `screen(page, "<id>", why="…")` at each screen reached, once what makes it reached has been waited for. Its first test is the reference run, the others its variants. It is served by pytest-django's `live_server`, with the fixtures of `tests/e2e/journeys/conftest.py` (`specs/testing.md` § "Journey tests") |
| A planned screen, a case to write | On a flow that has a journey: `screen(…, planned={"feature": "<feature>", "mockup": "specs/features/<feature>/mockups/<screen>.html", "what": "…"})`, the mockup an edited copy of today's capture, and `@planned_case("<feature>", "<screen>", "<title>")` on a test of the class with an empty body. Written, the case keeps its title under `@titled("<title>")` |
| A flow with no journey yet | Its feature's spec is its `spec.md`, and what changes on screen is described against the hand-drawn journey under `specs/design/journeys/`. A journey is written for a flow when a feature changes its screens |
| The tier of a test | Where its file stands: narrative under `tests/narratives/`, browser under `tests/e2e/`, unit otherwise (`tests/unit_tests/`, `tests/integration/`, `js_tests/`) |
| Product code | `model_builder/`, `e_footprint_interface/`, `theme/` |
| The proposed migration of a plan | None is drawn. A change of a Django model is a piece like another, and its migration file is committed with it (constitution §2.5) |

## Commands

| For | Run |
|---|---|
| The map | `npm run map -- <verb> …` (the `code-map` skill) |
| The pages, once; the check | `npm run comprehension:render`; `npx tsx comprehension_harness/render.ts --check` |
| The pages served, with the answer buttons | `npm run comprehension` |
| The approval, on the reviewer's word only | `npx tsx comprehension_harness/render.ts --approve <feature>` |
| The archive gate | `npx tsx comprehension_harness/render.ts --check --archive <feature>` |
| The Python tests that need no browser | `poetry run pytest --ignore=tests/e2e` (`tests/` and the stack's own tests, by `testpaths`) |
| The tests of what changed | `poetry run pytest <test files>` |
| The browser tests | `poetry run pytest tests/e2e -n 4`, against `poetry run python manage.py runserver` on `http://localhost:8000`. `tests/e2e/test_ai_bootstrap.py` starts its own server and runs before the rest (`specs/testing.md` § "AI bootstrap browser harness"); the journeys under `tests/e2e/journeys/` are skipped by a parallel run |
| The JavaScript tests | `npm run jest`; `npm run build:js:dev` first after an edit under `theme/static/scripts/` |
| The comprehension tools' own tests | `npx vitest run comprehension_harness` |
| The Python stack's tests | `poetry run pytest comprehension_harness/python/tests` |
| The narrative tests | `poetry run pytest tests/narratives` |
| The journeys, then their pages and the spec pages | `poetry run pytest tests/e2e/journeys`, in one process and with no server started apart, then `npm run journey:render`: `specs/design/journeys-generated/<journey>.html` and `specs/features/<feature>/spec.html` |
| The review-link extension's routes | `node --test tools/vscode-plan-review-links/extension.test.js` |
| The links of a `plan.html` | `python3 .agents/skills/feature-implement/scripts/vscode_review_links.py <plan.html> --in-place` |
| The ledger | `python3 ai-usage/usage.py collect`, then `python3 ai-usage/usage.py report --owner e-footprint-interface --feature <feature> [--run <x>]` |

Fixtures and environment setup: `specs/testing.md`.

## Gates

- **An edit of a plan or a doc**: the check. Nothing of the product runs for a document.
- **A piece's commit**: the test files of what it changed; `npm run jest` when a script changed.
- **A lot**: `poetry run pytest --ignore=tests/e2e` and `npm run jest` once, before its last
  commit, and the browser tests of each flow it changes.
- **The end of a run**: the full pytest suite (unit, integration, browser) and jest
  (constitution §2.2, §2.3).
- **A Django model changed**: its migration file is committed (§2.5).
- **Production code delivered**: one consolidated entry under `## [Unreleased]` of `CHANGELOG.md`
  in each repository whose production code changed, written at the end of the run. Production
  changes only: no spec, plan, tooling or test (§2.6).
- **`pyproject.toml` and `poetry.lock`** name `efootprint` from PyPI before a commit reaches
  `main` (§2.4). An edit of them that was there before the work is preserved; the published pin
  is restored deliberately, never as a side effect.
- **Never**: a production service used for validation, a hook skipped with `--no-verify` (§3.2),
  a failing test passed by a retry. A test that fails once and passes on a second run is flagged
  as flaky to the user (`specs/testing.md` § "Flakiness").
- A reviewer's fix is verified narrowly: the test files of what it touched.
- A commit stages its files by name, and its message opens with a tag of `AGENTS.md` § "Git
  commit style".

## Planning checks

For each interaction a plan follows, say which of these it touches:

- **Constitution §1**: the dependency direction (no Django import in `domain/` or
  `application/`), the repository pattern, the library as the truth of modeling (`ModelWeb`
  exposes it and never re-implements it), HTMX first with a server failure shown as the server
  renders it. A change in how one of them is enforced is a point to confirm, never a side effect.
- **The paths a boundary crosses**: when parsing, validation or rendering moves, the supported
  create, edit, preview, import and export paths all follow.
- **Saved state**: session persistence, and the shape of the saved JSON. A change of that shape
  names its upgrade handler and the test that holds it.
- **HTMX**: which partials and out-of-band swaps a response carries, and what the page shows
  when the response is an error.
- **The library**: a change that needs one there is planned there, in `e-footprint`'s own plan
  of the feature, with its own baseline, commit range and approval. This plan points at it
  (`## Planned elsewhere`) and relies on it; test against the intended library checkout. No
  guard here against what the library should fix.
- **A request with no response is out of scope.** It belongs to the parked
  `specs/backlog/network-interruption-message/problem.md`. Work scoped to HTTP responses adds no
  message specific to a timeout or an abort, no reload or retry per field, and no test that
  would establish a no-response policy. It preserves the existing generic request handling and
  surfaces a regression it causes; new network-interruption behaviour waits for an approved
  feature that promotes that backlog item.

## Lots

What belongs in one lot here:

- A change of a Django model with its migration.
- A change of the saved JSON's shape with its upgrade handler.

What is kept apart: a change in the library is no lot here. It is delivered by the library's
own plan, and a lot that consumes it says so in its reason. Nothing else is particular to this
project: the rules of `spec-tasks` apply.

## Review surfaces

- **FULL**: domain and application boundaries, repositories and session persistence, migrations
  and serialization, authentication and security, the ownership of form parsing or validation,
  HTMX and out-of-band state transitions, a contract between the library and the interface.
- **LIGHT** is open to small display-only templates and styles, copy, docs and tests. A path
  alone does not make a lot hard to implement.
- The size test counts source only: `-- . ':!tests' ':!js_tests' ':!specs' ':!*.md'`.
- **Added to the checklist**: integration coverage of a newly consumed public API. If the diff
  calls a public method, property or dict attribute of a `ModelingObject` subclass that no
  existing test path reached, say whether the relevant integration fixture has an assertion that
  touches the new call site. `run_test_materialize_all_cached_properties` already covers a new
  `cached_property`; this catches the rest: a plain `@property`, a method, a dict lookup, a new
  shape of behaviour on an existing API (`specs/testing.md` § "Coverage rule for new efootprint
  API consumption").

## Autonomy

Granted to a run with nobody there: everything local. The suites, a local development server
for the browser tests, local commits.

Never without the user's word for that instance: anything in production (a deployment, a
production database or service), a paid inference call (the AI bootstrap tests run on a local
fake), a force push, a branch deletion or a hard reset (constitution §3.3), a change of the
`efootprint` pin.

## Sub-agents and the ledger

- A role's model and effort are pinned in its runtime adapter, `.claude/agents/<role>.md` or
  `.codex/agents/<role>.toml`, and named nowhere else (`specs/agent-tooling.md` § "Agent roles").
- A spawn is labelled `<feature>--impl-lot-<lot>`, `--review-lot-<lot>`, `--review-global`,
  `--gate-full`, `<lot>` being the lot's slug; for a bug batch `--impl-task-<n>`,
  `--review-task-<n>`, `--diag-<bug>` and `--plan-review-guide`. The ledger reads the feature and
  the role from a lot's label, and the task from a task's.
- In Claude Code the label opens the spawn's description, and a spawn takes no name: a named
  agent inherits the session's effort and loses its own. Under Codex, bind the session
  (`specs/agent-tooling.md` § "Attribute current work").
- A stateful test suite and the application database are never shared between parallel agents.

## Archive

- **Where durable insight goes**: the owning page of `specs/architecture/`,
  `specs/conventions.md`, `specs/testing.md`, and the user-journey pages under `specs/design/`.
- **`CHANGELOG.md` and the roadmap stay accurate**: the feature leaves `specs/roadmap.md`
  § "Active streams".
- **Unfinished work** goes to a topic folder of `specs/backlog/` or to a horizon of the roadmap.
- **Never retired with a feature**: a test of a Django migration or of a serialization upgrade.
- A feature that changed both repositories is archived in each, its plan with its code.
