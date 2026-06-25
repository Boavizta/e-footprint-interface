# Compare view as a resident sibling — Tasks

**Status:** Tasks — under review.
**Spec:** none (technical optimization, no functional change). **Plan:** [`plan.html`](plan.html).

## Task 1 — Resident comparison view (the perf win)

**Status:** Done.

**Goal:** Make the comparison dashboard an in-flow resident sibling of the canvases instead of a `#main-content-block` replacement, so dismissing Compare is a client-side reveal — no `/model_builder/` reload, no bare `ModelWeb` json-load. **Unsaved-edit UX is left exactly as today** in this task: opening Compare still closes/discards the open side panel and is still gated by the existing `/compare/` guard. This isolates the performance change from the UX rework (Task 2) and ships a clean, surprise-free milestone.

**Files touched:**
- `theme/templates/model_builder/model_builder_main.html` — add an empty `#comparison-view` block as a flow sibling below the tab strip (starts `d-none`); make the toolbar + `#model-builder-page` toggleable.
- `model_builder/templates/model_builder/compare/dashboard.html` — drop the `{% include model_tab_strip … on_dashboard=True %}` (the one builder strip stays live above).
- `model_builder/templates/model_builder/components/model_tab_strip.html` — ⇄Compare tab → `hx-target="#comparison-view"` (keep `#compare-tab` id as the JS hide/show hook); model tabs drop the `skip_chrome` hx-val and the `on_dashboard` highlight branches; remove the now-dead `on_dashboard` parameter.
- `theme/static/scripts/model_comparison.js` — `openCompareView` (hide toolbar + canvas region `d-none`, hide ⇄Compare tab, clear active-model highlight, **close side panel / help drawer / results** as today, tear down leader lines); in `switchToSlot`, dismiss the comparison view (un-hide builder, rebuild lines) **before** the `previousSlot === slot` early-return; delete the canvas-absent reload branch; rewire the `htmx:afterSwap` teardown to key off the `#comparison-view` swap.
- `theme/static/scripts/result_charts/comparison_charts.js` (+ `drawComparisonCharts`) — track the three `Chart` instances; expose `destroyComparisonCharts()`; call it when the comparison view is dismissed.
- `model_builder/adapters/views/views_workspace.py` — `switch_model`: remove the `skip_chrome` branch (always OOB the shared chrome), update docstring. `compare`: the `not compare_enabled` fallback returns an empty/no-op response, **not** a full builder (would nest a builder inside `#comparison-view`).
- `theme/static/scss/custom.scss` — `#comparison-view` sizing in the flex parent; reveal the shared strip on mobile while `.comparing` (the `flex-nowrap overflow-x-auto` treatment), recompile `bs_main.css` via the SCSS pipeline.
- `theme/templates/base.html` — remove the dead `{% elif dashboard %}` full-page branch; confirm no view passes `dashboard=True` to a full-page render.
- `specs/architecture.md` — update “Two resident canvases” + “Comparison dashboard” (resident in-flow sibling toggled with the canvases; `skip_chrome` and the canvas-absent reload removed).
- `CHANGELOG.md` — entry.

**Tests added/changed:**
- `tests/.../jest` — `destroyComparisonCharts()` unit; `switchToSlot` reveal-from-comparison-view branch (DOM fixture: resident canvas + open comparison view → dismiss reveals the canvas, no reload).
- `tests/integration/...` — `switch_model` always emits shared-chrome OOB (no `skip_chrome` path); `compare` not-enabled fallback returns the no-op response, not a builder.
- `tests/e2e/...` — Compare → click a model tab returns to the builder with **no `/model_builder/` reload** (assert the network call is absent / canvas element identity preserved); reopen Compare shows fresh values after editing a model; mobile dismiss via the revealed strip.

**Acceptance:**
- Opening Compare keeps the builder DOM resident; dismissing to a model is client-side (no `/model_builder/` GET in the network log).
- Comparison charts are `.destroy()`-ed on dismiss (no duplicate/leak on reopen).
- Exactly one tab strip in the DOM; ⇄Compare hidden while comparing; the two fixed-width model tabs both fit on a phone.
- Unsaved-edit behavior is unchanged from today (opening Compare with a modified panel still warns via the existing guard and closes the panel).
- `pytest` (unit/integration/e2e) + `npm run jest` green.

**Depends on:** none.

---

## Task 2 — Non-destructive Compare + dismiss-before-warn

**Goal:** Layer the panel-preservation UX on the now-resident builder: opening Compare no longer discards the side panel (it survives hidden), returning to the same model resumes it intact, and a cross-slot dismiss tears the dashboard down first so the unsaved-changes warning is anchored on the edited model rather than shown over the comparison.

**Files touched:**
- `theme/static/scripts/model_comparison.js` — `openCompareView` stops closing the side panel / help drawer / results (preserve them hidden). Add a **capture-phase** model-tab click handler (when the comparison view is open): `dismissCompareView()` first (reveal the previously-active model + its open panel, rebuild lines); **same slot** → `preventDefault` (no POST, panel resumes, no warning); **other slot** → let the `/switch-model/` POST proceed so the unsaved modal lands over the now-revealed edited model.
- `theme/static/scripts/side_panel_utils.js` — remove `/compare/` from `PANEL_DISCARDING_PATHS`.
- `specs/architecture.md` — update the `PANEL_DISCARDING_PATHS` line (`{switch-model, +add}` — drop `compare`); note Compare is now non-destructive.
- `CHANGELOG.md` — entry.

**Tests added/changed:**
- `tests/.../jest` — capture handler: same-slot click `preventDefault`s and resumes the panel; other-slot click tears down the view then lets the request through.
- `tests/integration/...` — `/compare/` absent from `PANEL_DISCARDING_PATHS` (the path-set assertion test).
- `tests/e2e/...` — opening Compare with a modified panel does **not** warn and the panel survives; same-slot dismiss resumes the panel without a warning; cross-slot dismiss shows the unsaved modal **over the revealed edited model**, where Continue re-fires the switch and Cancel anchors on that model.

**Acceptance:**
- Opening Compare no longer warns or discards; the side panel survives hidden behind the comparison view.
- Same-slot return resumes the panel intact — no warning, no `/switch-model/` POST.
- Cross-slot dismiss reveals the edited model first, then shows the unsaved modal; Continue switches, Cancel leaves the user on that model with the comparison dismissed.
- `pytest` + `npm run jest` green.

**Depends on:** Task 1.

---

## Ordering rationale

The split is at a real behavioural pause point — **perf mechanism** vs **unsaved-edit UX rework** — not a layer/directory boundary. Task 1 lands the entire residency change (template target, JS toggle, chart teardown, server tweaks, scss, strip unification, dead-branch removal) while deliberately **preserving today's unsaved-edit behavior** (open Compare closes the panel, `/compare/` stays guarded). That makes Task 1 a clean, shippable milestone: the full performance win with zero surprise to the discard UX, and no spurious-warning intermediate state.

Task 2 then changes one interaction on purpose — opening Compare becomes non-destructive — which is exactly why `/compare/` can leave the guard, the same-slot resume becomes client-side, and the cross-slot warning moves behind the dashboard teardown. The only overlap is `openCompareView`'s panel handling, which Task 2 rewrites; that's a deliberate behavioural evolution, not throwaway scaffolding (Task 1's conservative close is the correct pairing for a still-guarded `/compare/`).

Everything within each task is tightly coupled — the `#comparison-view` target, the JS that toggles it, and the chart teardown have no behavioural pause point between them, so they stay in one commit. Both tasks leave all suites green. Task 2 depends on Task 1 (sequential, not parallel).
