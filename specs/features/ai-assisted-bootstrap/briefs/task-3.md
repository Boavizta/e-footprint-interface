# Task 3 — Connect entry points and stable view controls

Written 2026-11-09 against e-footprint-interface `1b2ea43740f76b1edcf7f345ed922582d2142bc4`; library reference `afc60887fa05c34d18d5969a45276bb08d3dace0`.
Plan: [entry/views](../plan.html#entry), [browser verification](../plan.html#delivery). Task: [3](../tasks.md#task-3--connect-entry-points-and-stable-view-controls).
Status: approved for Run A on 2026-11-09.

## Start here

- [Toolbar](../../../../model_builder/templates/model_builder/upload_download_reboot_model_tooltips.html), `build_picker_groups` — [picker presenter](../../../../model_builder/adapters/presenters/example_picker_presenter.py), [picker template](../../../../model_builder/templates/model_builder/onboarding/template_picker.html): real entry markup and context.
- Delegated `htmx:confirm` listener — [model_builder_main.js](../../../../theme/static/scripts/model_builder_main.js); active-slot/canvas markers — [model tab strip](../../../../model_builder/templates/model_builder/components/model_tab_strip.html) and [builder template](../../../../model_builder/templates/model_builder/model_builder_main.html).
- `createWorkspace` / `setBaseView` / `loadView` / `registerWorkspace` — [workspace.js](../../../../theme/static/scripts/simplified_inputs/workspace.js); `handleBuilderEntry` — [onboarding_first_run.js](../../../../theme/static/scripts/onboarding_first_run.js).
- Simplified-view edge wrapper rule — [_simplified_inputs.scss](../../../../theme/static/scss/_simplified_inputs.scss); `switchToSlot` — [model_comparison.js](../../../../theme/static/scripts/model_comparison.js); `PANEL_DISCARDING_PATHS` — [side_panel_utils.js](../../../../theme/static/scripts/side_panel_utils.js).
- `ModelBuilderPage.open_simplified_inputs` — [page object](../../../../tests/e2e/pages/model_builder_page.py); `model_builder_page` — [E2E fixtures](../../../../tests/e2e/conftest.py); named template cases — [build_fixtures.py](../../../../js_tests/build_fixtures.py).

## Change along the code path

Group Start with AI (Beta), Open a file and Reset in Modeling actions; retain existing file/reset endpoints and export/help/comparison behavior. Add a presentational prompt card to the scratch/file group when available, outside the domain catalog. Put its explicit AI branch before the normal load-example branch. Both entry buttons POST Task 2's Start URL into `#main-content-block` using the standard button lock and same destructive warning. Do not remove the picker on click: cancellation preserves it; successful whole-builder replacement removes it.

Scope the existing confirmation listener's card query to `[data-model-canvas]` matching `#model-tab-strip[data-active-slot]`, even when Simplified inputs hides that canvas. Keep existing file/workspace warning text. Start's own destructive warning covers ordinary side-panel drafts; do not add another `PANEL_DISCARDING_PATHS` entry. Existing Configure capture guards block, then the user resolves Save/Discard/Stay and repeats Start; never replay intent.

Replace the inversion button with explicit Modeling and Simplified inputs actions, fixed labels, pressed/active states and workspace-control markers. Update `setBaseView` rather than introducing another view owner. Selecting the current view does nothing; selecting Simplified from Modeling uses existing saved-view loading and side-panel discard confirmation. Preserve slot memory, Configure exits and initialization. Keep view buttons in a non-shrinking group; reserve the edge control wrapper's width and hide its contents with visibility in Simplified mode. Scroll arrows remain hidden there.

Recognize Task 2's AI panel marker in `handleBuilderEntry`: consume the existing seen flag and return without emitting the tour event. Do not queue a tour or add storage keys. Scratch/example automatic onboarding and Help replay remain unchanged.

## Earlier tasks

Task 1 supplies fakeable provider/service contracts. Task 2 supplies Start/Generate URLs, availability context, request-only input/summary panels and marker, fixed failure rendering and installed graph. Browser tests must drive these real views/save/render paths, injecting only inference, not replacing HTTP responses with prebuilt success HTML.

## Reuse

Use production template fixtures for changed controls in Jest. Reuse `ModelBuilderPage`, `SidePanelPage`, `click_and_wait_for_htmx` and `wait_for_htmx_idle`; extend page-object methods for AI entry/generation/review. Installed pytest-django's `live_server` serves static files and runs in the test process, so monkeypatching the provider works without test-only product endpoints.

## Invariants and traps

The old `data-action="simplified-mode"` means toggle, so search every caller and map its actual destination; a global blind rename would break “return to Modeling” tests. Verified consumers include `tests/e2e/test_simplified_inputs.py`, `test_weekly_pattern_builder.py`, the page object and `js_tests/simplified_inputs.test.js`. Toolbar regrouping also affects existing toolbar/onboarding selectors. Rebuild source bundles and CSS/maps; never edit compiled CSS manually. Preserve the existing inherited HTMX lock rather than adding queues or pending flags.

## Validation

Extend the three planned Jest files and picker presenter tests, rendering named toolbar cases from real templates. Assert active-only confirmation (both slots, hidden canvas, cancel/no request), explicit destinations/no-op/pressed state, Configure blocking and slot restoration, and seen-without-event AI entry versus normal onboarding.

Add `tests/e2e/test_ai_bootstrap.py` with module-local fixtures overriding `base_url` to `live_server.url`. Enable bootstrap with a dummy key, inject fake `complete_mistral` at Task 2's view lookup, use transactional test-session DB and per-test/per-worker cache locations. Use shared in-process LocMem caches for both system aliases to avoid a real Redis URL or uncreated DatabaseCache table; restore settings/clear isolated caches at teardown. Use plain static storage for templates and pytest-django's static serving. Scope these overrides to this module, preserving existing server-based E2E setup elsewhere.

Drive a populated modeling → cancel/confirm Start → description → Generate → summary → ordinary edit/close/reload. Hold Generate using Playwright route interception; while held, assert existing disabled controls and no duplicate request, then forward to the actual fake-provider live server. Check escaped/selectable collapsed prompt, Results closed, graph editable after disposal, and no summary reconstruction on reload. Reload is an explicit lifecycle assertion, never a repair for stale UI. Use distinct focused workflows/contexts for close/edit/reload outcomes. Cover Examples cancellation/entry and first-run suppression, using `onboarding_first_run` to bypass the shared fixture's default suppression. Compare both view buttons' bounding boxes before/after view switching; preserve edge/help/export/comparison flows. Keep slot/error permutations in Python view tests.

```sh
npm run build:simplified-inputs:dev
npx sass theme/static/scss/main.scss:theme/static/css/bs_main.css --load-path=node_modules/bootstrap/scss
npm run jest -- --runInBand
poetry run pytest tests/e2e/test_ai_bootstrap.py -n 0
poetry run pytest tests/e2e/test_onboarding.py tests/e2e/test_toolbar.py tests/e2e/test_simplified_inputs.py tests/e2e/test_weekly_pattern_builder.py tests/e2e/test_model_comparison.py tests/e2e/test_edge_modeling_toggle.py -n 0 --base-url http://localhost:8000
```

The new module needs installed Playwright/browser and built assets, but no external server or real key. Existing modules in the final command require the normal local server. Run stateful checks sequentially; report first-fail/retry-pass flakiness explicitly.

## Out of scope

Wider toolbar/navigation redesign, async/background inference, intent replay, new storage flags, provider-selection UI and browser permutations already owned by adapter tests.

## Unverified

The isolated fixture's setup/teardown and actual HTMX lock/layout behavior must be proven in the new browser module. Installed pytest-django support was inspected; no browser server or application tests were started during preparation.
