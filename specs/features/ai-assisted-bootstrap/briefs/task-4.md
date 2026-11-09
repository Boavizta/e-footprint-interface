# Task 4 — Retire the PoC and complete delivery

Written 2026-11-09 against e-footprint-interface `1b2ea43740f76b1edcf7f345ed922582d2142bc4`; library reference `afc60887fa05c34d18d5969a45276bb08d3dace0`.
Plan: [retirement](../plan.html#retire), [delivery](../plan.html#delivery). Task: [4](../tasks.md#task-4--retire-the-poc-and-complete-delivery).
Status: under review.

## Start here

- [ai_sandbox/edit.py](../../../../ai_sandbox/edit.py), [edit prompt](../../../../ai_sandbox/prompts/edit_prompt.md), [floating assistant template](../../../../model_builder/templates/model_builder/components/ai_assistant.html), [PoC tests](../../../../tests/integration/test_ai_assistant.py): explicit removals after replacement coverage exists.
- `AI_ASSISTANT_ENABLED`, `ai_assistant_model`, old URL/context imports — [settings](../../../../e_footprint_interface/settings.py), [context processors](../../../../model_builder/adapters/context_processors.py), [URLs](../../../../model_builder/urls.py), [old view](../../../../model_builder/adapters/views/views_ai_assistant.py): baseline locations; Task 2 should already replace most of them.
- [Sandbox guide](../../../../ai_sandbox/README.md), [INSTALL](../../../../INSTALL.md), [CHANGELOG](../../../../CHANGELOG.md), [release process](../../../../RELEASE_PROCESS.md), [constitution](../../../constitution.md): delivery/runtime boundaries.
- [Architecture index](../../../architecture/index.html), [onboarding](../../../architecture/onboarding.html), [rendering](../../../architecture/rendering.html), [layers](../../../architecture/layers-and-wrappers.html), [workspace](../../../architecture/workspace.html), [build-a-model journey](../../../design/journeys/build-a-model.html), [testing guide](../../../testing.md): durable documentation owners.

## Change along the code path

After Tasks 1–3 and focused checks, delete edit/read-back implementation, edit prompt, floating template and obsolete edit-only tests. Finish removing old route/context/model-selector/session writes and remaining import-path mutation from production. Retain shared generation tests, offline evaluation/replay/structural scoring and other-provider development comparisons. No copied old-code directory or disabled fallback.

Record the final relevant PoC revision before deletion in the sandbox guide, with a clear Git recovery pointer. Baseline `1b2ea43740f76b1edcf7f345ed922582d2142bc4` contains the original experiment; if extraction updated its imports, also record the last relevant implementation revision. Keep feature working sets in place: explicit archive happens later after delivery/checks, not automatically here.

Document shared generation/provider ownership, active-only reset/install, one-response summary disposal, both entry points and tour suppression, explicit fixed view buttons and Configure behavior. Add a concise ownership route in AGENTS.md/CLAUDE.md (check whether CLAUDE.md is an alias before editing). Explain the isolated browser fixture in the testing guide. Update installation and sandbox commands for runtime flag/key, fixed Flash model, 45-second provider bound/no retry, shared prompt/snapshot and developer-only refresh. Consolidate the production beta replacement in one Unreleased changelog entry; omit planning/testing/tooling-only prose. Keep roadmap order edge bootstrap → async unchanged.

## Earlier tasks

Task 1 has moved generation/catalog/prompt ownership and adapted CLI imports/Flash dispatch. Task 2 replaces the view/context/routes and removes the live floating include; Task 3 delivers entry/view controls and isolated E2E. Delete superseded code only after those replacements and their coverage are present. Do not reintroduce a second provider or DSL during cleanup.

## Reuse

Use existing release/dependency process, library serialization and normal editor tests. [Sequential deletion coverage](../../../../tests/e2e/objects/test_jobs.py) exercises two job removals; preserve it independently of removing AI edit tests. Existing `tests/integration/test_ai_bootstrap.py` owns shared generation/manual-edit round trips; new adapter tests own HTTP/session checks.

## Invariants and traps

Audit active code separately from historical specs/changelog/Git recovery references: do not rewrite historical experiment evidence just to eliminate every text match. Production imports must work without `anthropic`, `openai` or sandbox scripts being importable. A successful full development installation does not establish runtime dependency completeness. Preserve pre-existing dependency changes; published sources are required before main/deployment, with no companion-library implementation or schema migration planned.

## Validation

Run the full gates after focused tests pass, once per final changed state; investigate failures rather than masking/retrying them silently. Use the intended installed efootprint version (published baseline 27.0.1), built frontend assets and normal local server for existing E2E. The new AI module must override its base URL and use fake inference.

```sh
poetry run pytest tests --ignore=tests/e2e
npm run jest -- --runInBand
poetry run pytest tests/e2e -n 4 --base-url http://localhost:8000
poetry run python -m ai_sandbox.run --help
```

Inspect parsed `pyproject.toml` and `poetry.lock`: Mistral in runtime group, other provider SDKs development-only, efootprint from PyPI rather than path/directory. At preparation no dedicated dependency-source test was found; perform the explicit parsed-file check rather than citing a nonexistent test. Confirm package imports and loading of prompt/sizing snapshot in an isolated runtime-only dependency installation, without altering the development environment. Exercise the adapter there only with a stubbed SDK, never real inference. Repeat offline CLI fixture dry-run/replay into temporary output. Check final imports/references with `rg` for old route/flag/session keys, top-level DSL imports, sandbox production imports and `sys.path` mutation; check both new POSTs unavailable with flag/key absent and old route absent.

No deployment, enablement or paid API call is needed to pass these checks. Missing credentials are not a test blocker. Any missing runtime-install environment or failing required gate must be reported under the task list's classification; never mark delivery complete without its required evidence.

## Out of scope

PoC feature archival, deployment/configuration writes, new inference benchmarks/concurrency experiments, removing independent editor regressions, dependency upgrades unrelated to the SDK group, and follow-up edge/async work.

## Unverified

Full gates, runtime-only imports and offline CLI replay are implementation-time checks and have not been run in preparation. No plan amendment is needed for this mapped cleanup.
