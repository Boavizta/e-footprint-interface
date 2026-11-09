# AI-assisted bootstrap — tasks

Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: Run A complete on 2026-11-09. Implementation, per-task and cumulative reviews, and plan consolidation are complete; no implementation blocker remains.

## Implementation runs

| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A | Production fresh web bootstrap for either active modeling, stable view controls, and retired PoC UI/editing | [1](#task-1--extract-shared-generation-provider-and-metrics), [2](#task-2--install-the-fresh-start-and-generation-lifecycle), [3](#task-3--connect-entry-points-and-stable-view-controls), [4](#task-4--retire-the-poc-and-complete-delivery) | Authorized on 2026-11-09. No live inference or concurrency experiment required. |

## Overview

| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| 1 | Shared, Django-free generation and bounded Mistral adapter; deterministic cost/impact estimates; evaluation uses shared code | [Generation](plan.html#generation-call), [provider](plan.html#mistral-call), [metrics](plan.html#metrics) | e-footprint-interface | standard |
| 2 | Start clears only the active modeling; Generate installs a complete graph once or retains the description on failure; temporary input/summary panels | [Start](plan.html#confirm-start), [installation](plan.html#installation), [summary](plan.html#report) | e-footprint-interface | standard |
| 3 | Toolbar and Examples enter the same flow; active-only confirmation, first-run suppression, stable explicit view choices and browser coverage | [Entry and views](plan.html#entry), [verification](plan.html#delivery) | e-footprint-interface | standard |
| 4 | Obsolete experiment removed, useful CLI retained, durable documentation updated and repository gates completed | [Retirement](plan.html#retire), [delivery](plan.html#delivery) | e-footprint-interface | easy |

## Task 1 — Extract shared generation, provider and metrics

Goal: Establish the generation boundary with its first consumers and tests, preserving the useful evaluation workflow.

Status: complete

Brief: [briefs/task-1.md](briefs/task-1.md)

Plan: [Application operation](plan.html#generation-call) · [Mistral request](plan.html#mistral-call) · [Metrics](plan.html#metrics) · [CLI](plan.html#retire)

Repository: e-footprint-interface only.

Files touched:

- New `model_builder/application/ai_bootstrap/{__init__.py,service.py,metrics.py}` and `model_builder/adapters/ai_provider.py`.
- Move `ai_sandbox/dsl.py`, production portions of `ai_sandbox/catalogs.py`, `catalogs/boavizta_instance_specs.json`, and `prompts/system_prompt.md` into the application package; retain a developer-only snapshot refresh tool.
- `ai_sandbox/{run.py,providers.py,report.py}` and necessary package initializers; `pyproject.toml`, `poetry.lock`.
- Adjust imports in the still-live PoC view, edit helper and tests to consume moved definitions until their replacement/removal in Tasks 2/4; no duplicate DSL or import-path shim.
- New `tests/integration/test_ai_bootstrap.py`, `tests/unit_tests/application/test_ai_bootstrap_service.py`, `tests/unit_tests/application/test_ai_bootstrap_metrics.py`, `tests/unit_tests/adapters/test_ai_provider.py`; adapt the existing PoC test imports/date expectation.

Tests: Stubbed service/SDK/metric contracts; handwritten answer → real library objects → compute/export/reload → representative ordinary edit; offline CLI dry-run and replay in a temporary output directory.

Acceptance:

- `generate(description, complete)` calls once; `build_answer(text)` is shared with evaluation/replay. Application code imports neither Django, adapters nor sandbox tooling.
- Parsing tolerates existing fence/prose wrapping and reports ignored extras; duplicate declaration keys, bad references and invalid constructions fail locally. Preserve sourced comments, shared objects and editable timeseries, with the approved one-year horizon starting 2027-01-01.
- Production adapter fixes Flash/JSON/low effort/16,000 tokens/45,000 ms/no retries, handles text chunks and missing usage, and produces content-free errors. Non-success/truncated completions cannot reach construction.
- Cost uses the dated rate card and unknown-cache caveat; impact explicitly uses unscaled `mistralai / zai-glm-5-3`, preserves scalar/range kg values, and becomes unavailable on missing/invalid evidence without invalidating the modeling.
- Flash evaluation delegates to the same adapter; other development providers and report/replay behavior remain usable. Moves leave no broken PoC imports in the intermediate revision. Mistral is a runtime dependency.

Depends on: none.

Implementation: standard — the builders and provider call already exist; the remaining work is extraction, explicit contracts and ordinary adapter/estimator integration.

## Task 2 — Install the fresh-start and generation lifecycle

Goal: Deliver the backend operation and both side panels, with active-slot isolation and preparation before persistence.

Status: complete

Brief: [briefs/task-2.md](briefs/task-2.md)

Plan: [Confirmation/reset](plan.html#confirm-start) · [Description](plan.html#input-panel) · [Generation](plan.html#generate) · [Summary](plan.html#report)

Repository: e-footprint-interface only.

Files touched:

- Replace `model_builder/adapters/views/views_ai_assistant.py` with `views_ai_bootstrap.py`; update `views.py`, `model_builder/urls.py`, `model_builder/adapters/context_processors.py`, `e_footprint_interface/settings.py`, and Task 1's shared availability helper.
- `model_builder/templates/model_builder/model_builder_main.html`; new `side_panels/ai_bootstrap_input.html` and `side_panels/ai_bootstrap_summary.html`.
- New `tests/unit_tests/adapters/views/test_views_ai_bootstrap.py`; extend load/reset/import regressions in their existing view/workspace suites. Move retained Django-client generation assertions out of the PoC integration file and remove cases for the replaced HTTP contract.

Tests: Real Django client/session with fake provider; success/failure matrix, both actual active slots, sibling state/settings preservation, ID collisions, availability/POST-only boundaries, content escaping and privacy assertions; existing load/import/reset regressions.

Acceptance:

- Start resets only the active slot through scratch + existing load helper, replaces UI settings explicitly, makes IDs distinct, suppresses the picker, selects Modeling, closes Results and shows input. It accepts replacement of an edge modeling independently of edge-control visibility.
- Generate rejects blank input and a non-empty saved target before inference. It prepares, validates completeness and persists the generated graph once; provider, parse, schema, construction, computation and size rejections leave the saved scratch graph/settings intact and retain the escaped description with fixed visible feedback.
- Unavailable entries/views share flag-plus-key availability; both POSTs return 404 when unavailable. No submitted model selection or AI editing route remains active.
- Success renders the read-only summary with qualified metrics, substitutions/ignored fields, ordered review instructions and collapsed selectable prompt. The close cross is its only explicit dismissal; there is no form/Save action, raw-answer viewer or reopening route.
- Prompt, raw answer and call metrics are response-local; logs contain no submitted/generated content or arbitrary exception strings. Session/model/export/browser storage contain no AI generation report. Metric failure preserves successful generation.
- Existing load helper callers retain upgrade/import/distinctification/save behavior after preparation is extracted; no new storage transaction or rollback framework.

Depends on: Task 1's service/contracts, provider and metrics.

Implementation: standard — preparation and save already have established owners; the approved flow composes those helpers with explicit failure branches and normal response rendering.

## Task 3 — Connect entry points and stable view controls

Goal: Make the flow discoverable from both entry points and verify the actual HTMX/browser lifecycle.

Status: complete

Brief: [briefs/task-3.md](briefs/task-3.md)

Plan: [View controls](plan.html#view-controls) · [Confirmation](plan.html#confirm-start) · [Picker/tour](plan.html#picker-entry) · [Browser verification](plan.html#delivery)

Repository: e-footprint-interface only.

Files touched:

- `model_builder/templates/model_builder/upload_download_reboot_model_tooltips.html`, `onboarding/template_picker.html`, `model_builder/adapters/presenters/example_picker_presenter.py`.
- `theme/static/scripts/{model_builder_main.js,onboarding_first_run.js,simplified_inputs/workspace.js}`; `theme/static/scss/_simplified_inputs.scss`; rebuilt Simplified bundle/maps and `theme/static/css/bs_main.css{,.map}`.
- `js_tests/{build_fixtures.py,model_builder_main.test.js,onboarding_first_run.test.js,simplified_inputs.test.js}`; picker presenter tests.
- New `tests/e2e/test_ai_bootstrap.py`; `tests/e2e/pages/model_builder_page.py` and affected toolbar/Simplified/onboarding/weekly-pattern browser tests and page objects.

Tests: Jest using production-template fixtures; focused isolated-server Playwright workflows with fake inference; existing onboarding, toolbar, comparison, edge and Simplified regressions.

Acceptance:

- Modeling actions groups AI start (Beta), file opening and reset; Examples appends a presentational Start from prompt card. Both Start actions use the same POST/target/lock/confirmation and appear only when available.
- Confirmation checks the active resident canvas even while hidden in Simplified inputs. Cancel sends no request and preserves picker/model/drafts; an empty active canvas with a populated sibling needs no warning. Dirty Configure blocks until resolved and the user repeats the action.
- Modeling/Simplified inputs are fixed-label explicit destinations with pressed states; reselecting the active view is a no-op. Preserve per-slot view memory, Configure exits and normal panel discard behavior. Reserved edge-control width keeps both view positions stable.
- AI input/summary consume the existing first-run flag without auto-running/deferred tour; ordinary scratch/example onboarding and manual Help tour still work.
- Real-browser coverage holds and forwards a Generate request to the in-process fake-provider server, proves disabled controls/no duplicate call, installs the graph with Results closed, and proves summary disposal on close/edit/reload while the graph remains editable. Cover picker cancellation and stable view-button positions in focused workflows.

Depends on: Tasks 1–2; built frontend assets for browser checks.

Implementation: standard — reuse delegated confirmation, workspace guards and first-run storage; remaining work is ordinary template/JS integration and an isolated browser fixture using installed pytest-django support.

## Task 4 — Retire the PoC and complete delivery

Goal: Remove the superseded experiment, document the delivered boundaries, and finish required verification.

Status: complete

Brief: [briefs/task-4.md](briefs/task-4.md)

Plan: [Retirement](plan.html#retire) · [Delivery gates](plan.html#delivery)

Repository: e-footprint-interface only.

Files touched:

- Delete `ai_sandbox/edit.py`, `ai_sandbox/prompts/edit_prompt.md`, `model_builder/templates/model_builder/components/ai_assistant.html` and remaining edit/read-back-only content of `tests/integration/test_ai_assistant.py` (remove the file once retained coverage is relocated).
- Remove any remaining obsolete PoC imports/context/selector/session writes; finish `ai_sandbox/README.md`, `INSTALL.md` and the shared CLI refresh/import documentation.
- `specs/architecture/{layers-and-wrappers,rendering,onboarding,workspace}.html`, `specs/design/journeys/build-a-model.html`, and `specs/testing.md` for the isolated browser harness; concise bootstrap ownership route in `AGENTS.md` / its `CLAUDE.md` alias; one consolidated production `CHANGELOG.md` entry.
- This working set's task status and consequential implementation decisions in the plan, through the normal implementation workflow.

Tests: Runtime-only dependency/import smoke in an isolated environment; retained generation CLI dry-run/replay; full Python unit/integration and E2E suites, Jest, JS/SCSS builds, dependency-source check, and obsolete-reference audit.

Acceptance:

- Production requests never import sandbox tooling or mutate `sys.path`; no old route, UI, model-selector state writes or AI edit/read-back code remains. Other-provider evaluation remains developer-only.
- Record the final relevant pre-removal PoC Git revision in the existing sandbox guide; Git is the recovery mechanism, without copied/disabled old code. Do not archive feature documents during implementation.
- Durable docs describe ownership, active-slot replacement, transient summary and explicit view choices; installation documents default-off flag/key/fixed model/timeout without publishing secrets. The changelog covers production behavior only.
- Required gates pass against the intended library build; unresolved failures or genuinely missing environment evidence remain visible and classified below. Preserve independent ordinary-editor regressions, including nested-job then top-level-journey deletion.

Depends on: Tasks 1–3 and their focused checks; remove obsolete edit tests only after retaining generation/manual-edit coverage.

Implementation: easy — replacement behavior and tests are delivered by predecessors; the remaining changes are mapped removals, documentation updates and established delivery checks.

## Outstanding follow-up prerequisites

No implementation or review blocker remains. These actions are outside Run A.

| Check | Classification | Environment / required evidence |
|---|---|---|
| Deployment configuration | Blocks deployment only | Enable `AI_BOOTSTRAP_ENABLED` and server Mistral key through the normal deployment process. Actual deployment/enablement is outside this run. |
| PoC archive | After delivery, separate explicit action | Delivery and required checks must exist first. Preserve the PoC working set until the archive workflow is explicitly invoked; follow-ups stay edge bootstrap, then async I/O. |

Preparation baseline (2026-11-09): interface `1b2ea43740f76b1edcf7f345ed922582d2142bc4`; companion library `afc60887fa05c34d18d5969a45276bb08d3dace0` (reference only, no edits planned). Code pointers and predecessor contracts checked; product code, shared application state and the approved plan remain unchanged. Application tests, builds and inference have not been run during task preparation.

Implementation baseline (2026-11-09): interface `497fe2c77209e03877c7a0a5a62f3fa6db8c429a`; companion library `afc60887fa05c34d18d5969a45276bb08d3dace0`. Both repositories were clean when Run A began.
