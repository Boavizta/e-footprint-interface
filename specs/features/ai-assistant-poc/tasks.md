# AI assistant proof of concept — tasks
Spec: [spec.html](spec.html) · Plan: [plan.html](plan.html)
Status: run A delivered 2026-10-29 (tasks 1-4 done, global review done); final range `e7ade421..f0cac452` plus the
plan guide and status commits. Outstanding: the deployment gate and the browser smoke below.

Hackathon proof of concept: three tasks, one run, simplest code that works. Task 3 is the plan's cut line and can be
dropped from the run without touching tasks 1 and 2.

## Implementation runs
| Run | Delivered milestone | Tasks in execution order | Prerequisites |
|---|---|---|---|
| A | Flagged assistant on the dev app: generate on an empty model, edit on a non-empty one, feedback line, log line | 1 → 2 → 3 | None. The dev-app flag and keys are a deployment gate (below), not a prerequisite. |

## Overview
| Task | Delivered behavior | Plan section | Repository | Implementation |
|---|---|---|---|---|
| 1 | Generate path end to end behind `AI_ASSISTANT_ENABLED`: box, route, view, feedback metrics, log line, refusals, changelog | [1.2](plan.html#box) · [1.3](plan.html#generate) · [1.5](plan.html#feedback) | e-footprint-interface | standard |
| 2 | Builder refactor into field tables and per-object builders, plus `system_to_dsl` read-back with its round-trip test | [1.1](plan.html#shared) · [1.4](plan.html#edit) (read-back) | e-footprint-interface | standard |
| 3 | Edit path: edit prompt addendum, `apply_edits`, the non-empty branch of the view, README paragraph | [1.4](plan.html#edit) | e-footprint-interface | hard |
| 4 | Box refinement requested by the user on 2026-10-29: visible only on the modeling view (hidden in the simplified-inputs workspace and while the results panel is open), collapsible and open by default | [1.2](plan.html#box) | e-footprint-interface | easy |

## Plan amendments
[Amendment index in the plan](plan.html#plan-updates). All three were accepted on 2026-10-29 and are integrated in the
plan and spec; no task is provisional.
- [PLAN-UPDATE-01](plan.html#plan-update-01) edits mutate the live library model through the sandbox builders — task 3.
- [PLAN-UPDATE-02](plan.html#plan-update-02) no open questions in the generation feedback — task 1.
- [PLAN-UPDATE-03](plan.html#plan-update-03) zai-glm-5-3-flash first in `DEFAULT_MODELS`, preselected — task 1.

## Task 1 — Generate path end to end
Goal: with the flag on, the builder page shows the assistant box; posting a description on an empty model replaces it
with the generated model and shows the metrics line, the note and the raw answer; failures, edge models and the flag
being off behave as the spec says. The non-empty branch answers "Editing is not available in this build" until task 3.
Status: done — reviewed range `e7ade421..7fbeac3e`
Brief: [briefs/task-1.md](briefs/task-1.md)
Repository: e-footprint-interface
Files touched: `ai_sandbox/providers.py` (DEFAULT_MODELS order), `ai_sandbox/dsl.py` and `ai_sandbox/run.py` (move
`parse_json` and `validate_tolerating_extras`), `e_footprint_interface/settings.py`,
`model_builder/adapters/context_processors.py`, `model_builder/urls.py`, `model_builder/adapters/views/views.py`
(`extra_context`), new `model_builder/adapters/views/views_ai_assistant.py`, new
`model_builder/templates/model_builder/components/ai_assistant.html`,
`model_builder/templates/model_builder/model_builder_main.html`, `CHANGELOG.md`, new
`tests/integration/test_ai_assistant.py`.
Tests: verification map rows 1, 3, 4, 5 with `complete` monkeypatched; `run.py --dry-run` on the handwritten case still
passes after the helper move.
Acceptance: `poetry run pytest tests --ignore=tests/e2e` green with the flag off by default; with the settings fixture
turning the flag on, the four view tests pass without any provider call; the first option of the select is
zai-glm-5-3-flash.
Depends on: none.
Implementation: standard — ordinary Django wiring shaped on `load_example`, with the sandbox stages called in sequence;
the only judgment is the EcoLogits footprint line and the failure branch.

## Task 2 — Builder tables and read-back
Goal: `dsl.py` exposes the DSL-to-library mapping as field tables and one builder per object kind (behavior unchanged),
and new `ai_sandbox/edit.py` reads a hydrated `ModelWeb` back into the DSL vocabulary.
Status: done — reviewed range `7fbeac3e..2a5a7862`
Brief: [briefs/task-2.md](briefs/task-2.md)
Repository: e-footprint-interface
Files touched: `ai_sandbox/dsl.py`, new `ai_sandbox/edit.py` (`system_to_dsl` only), `tests/integration/test_ai_assistant.py`.
Tests: verification map row 6 (round trip within 1 %); `run.py --dry-run` on the handwritten case gives the same
total as before the refactor (17044.4 kg).
Acceptance: the dry run is unchanged; the round-trip test passes; `build_system` is the only public builder entry point
the CLI uses.
Depends on: task 1 (helper move already done; otherwise independent).
Implementation: standard — a mechanical refactor of one function plus a mirror read-back whose lossy mapping is spelled
out in the plan; the read-back needs ordinary judgment on web wrappers versus library objects.

## Task 3 — Edit path
Goal: on a non-empty model, the request is sent with the current model's DSL, the answer's changed, added and removed
objects are applied to the live library model, and the session is persisted once at the end; any failure leaves the
model untouched.
Status: done — reviewed range `2a5a7862..20aac1a0` (includes the pre-existing defect fix `0ac6b40c`, see
[IMPL-DECISION-02](plan.html#impl-decision-02); edit semantics in [IMPL-DECISION-03](plan.html#impl-decision-03) and
[IMPL-DECISION-04](plan.html#impl-decision-04))
Brief: [briefs/task-3.md]
Supervisor decisions from the task 2 review (leads in [handoffs/task-2.md](handoffs/task-2.md)): never read live values through
`ExplainableQuantity.to()` (in-place conversion); a volume edit keeps the current `start_date` and modeling duration; a step
re-list refuses when a surviving job's weight is fractional; a journey re-list keeps each surviving step's weight; jobs read
back without `server`/`genai_api` are opaque (re-listable, not editable).(briefs/task-3.md)
Repository: e-footprint-interface
Files touched: `ai_sandbox/edit.py` (`apply_edits`), new `ai_sandbox/prompts/edit_prompt.md`,
`model_builder/adapters/views/views_ai_assistant.py` (non-empty branch, `EDIT_PROMPT`), `ai_sandbox/README.md`,
`tests/integration/test_ai_assistant.py`.
Tests: verification map row 2 (volume doubled, job added and re-listed, job removed, hand-set lifespan and ids intact).
Acceptance: row 2 passes; a fake answer that references an unknown job leaves the session payload identical and renders
the error; no provider call in tests.
Depends on: tasks 1 and 2.
Implementation: hard — `apply_edits` sequences coupled mutations on the hydrated reactive library model (new objects
registered in `ModelWeb`'s dicts, weighted-dict re-listing, paired provider/instance updates in one `ModelingUpdate`,
delete internals without persistence) and two of those mechanisms are unconfirmed in the plan.

## Task 4 — Box only on the modeling view, collapsible
Goal: the assistant box is hidden while the simplified-inputs workspace is shown (`body[data-base-view="simplified"]`)
and while the results panel is open (a sibling rule on the panel's existing inline-height open signal; no JS); the box
is a native `details` element, open by default, so it can be collapsed to its title line.
Status: done — reviewed range `19b1ef3e..f0cac452`, see [IMPL-DECISION-05](plan.html#impl-decision-05)
Repository: e-footprint-interface
Files touched: `model_builder/templates/model_builder/components/ai_assistant.html`.
Acceptance: `poetry run pytest tests --ignore=tests/e2e` green; browser check of the three states on the dev app.
Depends on: task 1.
Implementation: easy — CSS rules on existing page state and a `details` wrapper.

## Gates and prerequisites
- Deployment only: `AI_ASSISTANT_ENABLED=1` and the three provider keys set on the dev app.
- Checked 2026-10-29 from the repo: the dev deployment installs the dev dependency group. `Dockerfile` runs a plain
  `poetry install`, the dev group is not optional, the lock holds anthropic, openai and mistralai, and `.dockerignore`
  keeps `ai_sandbox/` in the image (its untracked `runs/` folder never reaches a git-built image). Only a build override
  in the Clever Cloud console could change that; `specs/tech_stack.md` says images are built from `Dockerfile`.
- After the run: a browser smoke of both paths on the dev app with a real model; the box's bottom offset against the
  results band is tuned there.
- No E2E test; the unit and integration suite is the gate: `poetry run pytest tests --ignore=tests/e2e`.
- At archive: spec §5 "Providers" still says the three SDKs become runtime dependencies; the approved plan keeps them in the
  dev group (checked against the Dockerfile above). Touch the spec line if the spec is kept.
