# Conventions — e-footprint-interface

These are the strong preferences and patterns the project follows. They are softer than the constitution: deviations are possible with justification, but defaulting to these preserves consistency.

## Code style

### Python

- **PEP 8** + line length **120**. Don't systematically break lines between parameters; prefer long lines under the limit.
- Follow `.pylintrc` for linting.
- **Type hints** where helpful; not strictly enforced.
- **Prefer double quotes (`"`) for strings**, over single quotes (`'`).
- **Keep functions small.** Raise explicit errors with actionable messages.
- **Comments only when the WHY is non-obvious.** Never comment what the code does — only why it does it that way.

### Django

- **Views are thin adapters.** They map request to use case input, call the use case, format response via the presenter. No business logic in views.
- **Templates are small composable partials.** See `model_builder/templates/model_builder/...` for the pattern.
- **Keep form data typed until rendering.** Preserve native numbers, collections, and identifiers in form configuration; localize or stringify them only where they cross into HTML attributes.
- **Session is authoritative for the current modeling system.** Every request reconstructs `ModelWeb` from the repository.
- **No domain-layer imports of Django, HTMX, or other presentation concerns** (constitution §1.1).

### JavaScript

- **Multi-file features use private modules bundled with esbuild.** Simplified inputs lives in `theme/static/scripts/simplified_inputs/`: `index.js` composes `workspace.js`, `configuration.js` and `bookmarks.js`; inline field saves are declarative HTMX on the editor form. Its CommonJS sources also load directly in Jest. Build with `npm run build:js:dev` locally or `npm run build:js` for production. Keep its IIFE bundle as a synchronous script before `model_builder_main.js`. Use explicit callbacks between these feature modules and DOM events when communicating with other widgets; keep state with its owning module.

- **Feature JavaScript does not anticipate server errors, slow responses or request races.** The server is the source of truth, and its failures stay visible rather than softened: a 4xx/5xx response is presented the way the server renders it, and a 500 that renders nothing is left as an empty or stale target so it gets reported and fixed. Do not keep client copies of server-owned state such as saved values, membership or locks; the rendered fragment is the state. Do not add client state, listeners or fallbacks whose only purpose is to hide a hypothetical failure or to order concurrent requests. HTMX settles synchronously in this project, so `htmx:afterRequest` on an element means its DOM result is final, and nothing should observe swap or settle events to sequence its own request. When an HTMX attribute (`hx-trigger`, `hx-sync`, `hx-disabled-elt`, `hx-indicator`, `hx-vals`, `hx-on`) expresses the need, use it; otherwise accept the edge. Shape a payload in `htmx:configRequest` only where markup cannot express it, such as nameless controls inside another form. Global `htmx:afterSettle` re-initialisation hooks that make any swapped fragment work (tooltips, charts, leader lines, layout) remain allowed because they hold no request state. The only exceptions are data-loss cases the mission names as worth protecting; they are decided in the spec, never added defensively in code.

- **User-initiated requests are sequential.** Every element that issues a navigation or mutation request declares `hx-disabled-elt="button:not(:disabled)"` (Simplified inputs add their workspace inputs, selects and textareas), so one user action completes before the next can start. Never use `hx-sync`, pending flags, queues or replacement rules to arbitrate between user actions; `hx-sync="this:drop"` on a single element is allowed only to dedupe its own duplicate triggers. Background requests (timeseries previews, metadata autosaves, workspace-storage polls, Sankey and lazy loads) stay unlocked and must target only their own region. Some user-initiated elements outside Simplified inputs still lack the lock; adding it there is a separate follow-up.

- **Vanilla JS + small helpers only.** Keep logic minimal; prefer progressive enhancement.
- **Use HTMX attributes for partial updates** rather than large custom JS.
- **New standalone scripts wrap their internals in an IIFE and dispatch via `data-action`**; multi-file source modules get that private scope from their bundle. Templates declare intent (`data-action="open-source-editor"`); a delegated listener switches on the action and dispatches to a module-private function. Rationale: keeps `window` clean (no per-widget globals to collide or accidentally expose), survives HTMX swaps with no rebinding (the listener is on `document`), and is compatible with strict CSP later (no inline JS to allow). When separate widgets need to talk, prefer a custom DOM event over a shared global. See `theme/static/scripts/source_metadata.js` for the standalone pattern. Older modules using inline `onclick=` keep working; migrate boy-scout style when you're already touching one.
- **Dismiss/close handlers on HTMX-swapped content use synchronous `onclick`, not hyperscript.** Hyperscript re-processes swapped DOM through its `htmx:load` listener, and `processNode` attaches handlers *asynchronously* — so for a brief window after an HTMX swap the element is visible but its `_="on click …"` handler isn't wired yet, and a click landing there is silently lost (flaky in E2E, a real dead-click window for fast users). A plain `onclick` attribute is wired by the browser at parse time with no such window. The example-picker close button (`onboarding/template_picker.html`) and the modal close (`modals/modal_template.html`) follow this. Hyperscript is fine for content that isn't re-rendered into a swap target, or for actions a user only reaches after the swap has settled.
- **Conditional confirmation depends on live state, not a server-rendered `hx-confirm`.** An `hx-confirm` gated on a server flag (`{% if not model_is_empty %}…`) freezes at render time; if the element outlives the swaps that change that state (e.g. the toolbar reboot button is rendered once but objects are added via inner partial swaps), the attribute goes stale and the confirm silently appears/disappears at the wrong times. Instead, tag the element with `data-confirm-when-model-not-empty="<question>"` and let the single body-delegated `htmx:confirm` listener in `model_builder_main.js` decide at click time, reading emptiness live from the DOM (`.model-builder-card`). Body-delegated (not per-element hyperscript) so it survives swaps with no wiring window (see the rule above). The toolbar reset and the picker cards follow this.
- **UI-only inputs inside form sections must omit the `name` attribute.** `dynamic_forms.js#displayOnlyActiveForm` only flips `required`/`disabled` on `input[name]`/`select[name]`. Nameless controls (e.g. the source editor's custom-source scratch fields) never submit, so marking them required would only block the form — hidden invalid controls can't be focused, which silently aborts HTMX submission.
- **Polymorphic dynamic editors keep drafts in the DOM and submit one normalized payload.** Render each registered
  sub-editor once, use a nameless selector, and disable all controls in inactive panels so their validation and values
  cannot leak into submission. Inherently local list/range interactions use one delegated IIFE module, serialize into a
  single named hidden control, and map authoritative server errors back through stable normalized field paths.
- **Pick the persistence shape that fits the trigger.** For event-driven, no-button widgets (e.g. the confidence badge — a menu pick *is* the save), use the `data-autosave-*` convention: include the partial with `*_autosave_url`, JS POSTs the changed field, and leaves the already-updated widget in place. For Apply-button widgets (e.g. the source editor in the source-table row), wrap them in a real HTMX form (`hx-post hx-swap="none" data-action="source-table-row-edit"`) — Apply writes hidden inputs via the existing `applySourceEditor` and triggers the form's submit; after success, JS updates the row display from those hidden inputs. `_apply_metadata` patches in place either way, so omitted source/comment/confidence keys are preserved.
- **Do not pre-render heavy controls for every table row.** Source-table row editors are fetched on demand with HTMX, and source-table confidence menus are cloned from a single Django-rendered `<template>` on first click. Keep this pattern for repeated controls whose full markup is usually unused.
- **Don't re-implement Bootstrap widget init per module.** `theme/static/scripts/bootstrap_widgets.js` exposes `initBootstrapWidgets(root)` and runs it on `DOMContentLoaded` and `htmx:afterSettle` (scoped to the swap target). New popovers and tooltips show up automatically; per-widget `bootstrap.Popover.getOrCreateInstance(...)` calls in feature modules are duplication. The one exception is `.truncated-text-tooltip`, which needs its own truncation-guard listener and zero-delay config (owned by `model_builder_main.js#initTruncatedTextTooltips`) — `bootstrap_widgets.js` skips that class so the first init wins with the right options. The same module also runs `disposeShownWidgets(target)` on `htmx:beforeSwap`: a shown tip is appended to `<body>` (outside the swap target), so a swap that removes its trigger (e.g. the reset-model button replacing all of `#main-content-block`) would orphan it forever — disposing the instance on the about-to-be-removed trigger removes the tip. Two safeguards keep that dispose from crashing on a trailing interaction event (Bootstrap zeroes every own property on `dispose()`, so a re-entered `_isWithActiveTrigger`/`hide` throws on the nulled `_element`/`_activeTrigger`): tooltips are created with **`animation: false`** so `hide()` is synchronous and never defers its cleanup past the swap, and `hardenAgainstDisposedTipEvents()` (installed once, patches `Tooltip.prototype`, inherited by `Popover`) makes the interaction entry points no-op on a disposed instance. Keep both when adding tooltips — drop the animation and don't bypass the central init.
- **driver.js is the sanctioned tour engine; tour copy lives server-side.** The guided tour (`theme/static/scripts/tour.js`) is the only place driver.js is used — a dependency-free, view-only utility (not an SPA framework). Its step *words* never live in JS: they are authored in `model_builder/adapters/ui_config/tour_steps.py`, resolved through the SSOT placeholder provider, and passed to `tour.js` as a `<script type="application/json">` payload (see [Examples and onboarding → Guided tour](architecture/onboarding.html#guided-tour)). Tour targets use stable `data-tour-target` attributes, not incidental DOM. Vendored libs follow the `external_librairies/` pattern: committed dist file refreshed via `npm run vendor:driver` (part of `npm run build`).

### Tests

- Python tests under `tests/` (and app-specific subfolders).
- Playwright E2E tests under `tests/e2e/`.

## Performance preferences

For data and array operations:

- **Prefer vectorized NumPy operations over Python loops.**
- **Use single-pass algorithms** (e.g., `np.bincount`) over multiple iterations.
- **When proposing solutions, include complexity analysis** (e.g., O(n) vs O(n²)) for non-trivial data paths.
- **Trade-offs between readability and performance** should be made explicit in PR descriptions when relevant.

## Editing patterns

- **Make all edits on the same file at once** rather than step-by-step changes.
- **Use programmatic tools for systematic textual work across many files.** For renames, global substitutions, or dropping a pattern everywhere, batch the change with `sed -i ''` or `grep -l … | xargs sed -i ''` rather than a serial Read+Edit loop per file. Per-file Edit is for heterogeneous changes (each file needs a different edit) or when you need to inspect surrounding context before replacing. Verify with `grep` after the bulk replacement that no stale references remain.
- **Never paper over a bug** (constitution §3.1). If you discover an unrelated bug while working on a task — a stale card after mutation, a missing form attribute, a brittle assertion — fix it on the spot or surface it explicitly. Never `page.reload()` to hide it, no defensive branch to tolerate it, no renamed assertion to avoid triggering it.

## Documentation upkeep

- If you notice that the AGENTS.md or specs/ files are missing important information that would allow for less context gathering in developments, propose improvements.
- Whenever you implement or change a non-trivial pattern (new web wrapper convention, new HTMX flow, new render strategy, schema migration), proactively check whether the owning [architecture page](architecture/index.html), `conventions.md`, or `testing.md` should be updated and propose the changes.

## Form field metadata suffixes

Five reserved suffixes are recognised by `form_data_parser.parse_form_data` **before** the generic `__` → `form_inputs` branch:

- `__confidence` — `"low"` / `"medium"` / `"high"` or empty (→ `None`)
- `__comment` — free-form text or empty (→ `None`)
- `__source_id` — id of an existing `Source`; empty means custom entry
- `__source_name` — source name (used when id is absent or unknown to mint a new `Source`)
- `__source_link` — source URL (optional, paired with `__source_name`)

These map into `parsed[attr]["confidence"]`, `parsed[attr]["comment"]`, and `parsed[attr]["source"]["id/name/link"]`. Checking them before the generic branch prevents them from landing in `form_inputs`.

## Test conventions

See `testing.md` for the full testing guide. Highlights:

- Use `create_mod_obj_mock` from `tests.utils` instead of raw `MagicMock` when mocking `ModelingObject` subclasses; prefer real `ExplainableObject` / `ExplainableQuantity` instances when possible.
- Build E2E fixtures with efootprint classes and `from_defaults()`, not JSON files.
- Use `click_and_wait_for_htmx()` for HTMX-triggered E2E clicks; don't write raw Playwright clicks for HTMX flows.
- Form data parsing happens in `adapters/forms/`, never in domain. The domain receives parsed dicts.

## Flakiness

If a test fails on the first run but passes on retry, **flag it explicitly** to the developer as a flaky test rather than silently re-running. Flaky tests are bugs.
