# Edge Legend Fixes — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

---

## Task 1 — Edge-aware bar chart legend (Fix A)

**Status:** Done.

**Goal:** The single-model results bar chart legend hides edge-device items when the edge-modeling toggle is off, and shows them when it is on. State is read at render time.

**Files touched:**
- `theme/static/scripts/result_charts/config.js` — add `isEdge: true` to `Edge_devices_energy` and `Edge_devices_fabrication` entries in `HARDWARE_TYPE_CONFIG`.
- `theme/static/scripts/result_charts/legend.js` — in `splitCapsuleLegendPlugin.afterUpdate()`, filter legend items where `chart.data.datasets[item.datasetIndex]?.isEdge === true` when `!document.body.classList.contains('edge-modeling-on')`, before the usage/fabrication split.

**Tests added/changed:**
- New Jest test file (or extend existing legend tests) in `js_tests/` covering:
  - Edge items are absent from the rebuilt legend when body lacks `edge-modeling-on`.
  - Edge items are present when body has `edge-modeling-on`.
  - Non-edge items are unaffected in both states.

**Acceptance:**
- With edge toggle off: no edge capsules appear in the bar chart legend (Fabrication or Usage sections).
- With edge toggle on: edge capsules appear as before.
- `npm run jest` passes.

**Depends on:** none.

---

## Task 2 — Grouped comparison legend (Fix B)

**Goal:** The comparison paired bar chart legend is replaced with a custom HTML legend that groups items into one row per system, using the real system names, left-aligned.

**Files touched:**
- `model_builder/domain/services/comparison_service.py` — add `"modelAName": comparison.system_a.name` and `"modelBName": comparison.system_b.name` to the `_paired_chart_payload()` return dict.
- `theme/static/scripts/result_charts/comparison_charts.js`:
  - In `buildPairedChartConfig()`: set `legend: { display: false }`.
  - Add `renderPairedLegend(payload, canvasId)`: finds-or-creates `<div id="{canvasId}-legend">` after the canvas; groups `payload.datasets` by `stack`; renders one row per system with the system name label and color-dot items. Falls back to "System A" / "System B" if name fields are absent.
  - Add `destroyPairedLegend(canvasId)`: removes the legend `<div>` by id.
  - In `drawComparisonCharts()`: call `renderPairedLegend(paired, "comparisonPairedChart")` after `renderChart`.
  - In `destroyComparisonCharts()`: call `destroyPairedLegend("comparisonPairedChart")`.

**Tests added/changed:**
- `tests/unit_tests/` — Python unit test asserting `modelAName` and `modelBName` are present and correct in the paired payload returned by `ComparisonService`.
- `js_tests/comparison_charts.test.js` — extend to assert `buildPairedChartConfig` sets `legend.display: false`; add unit test for `renderPairedLegend` asserting: two rows rendered, correct system-name labels, correct number of color items per row, graceful fallback when name fields absent.

**Acceptance:**
- The comparison paired bar chart legend shows two rows, one per system, each labelled with the real model name.
- No mid-row wrapping regardless of the number of active hardware types.
- `npm run jest` passes.
- `poetry run pytest tests/unit_tests` passes.

**Depends on:** none (independent of Task 1).

---

## Task 3 — Design-hub journeys: view-results and compare-models

**Goal:** Document the corrected legend behaviour in the design hub so future contributors have a visual reference for both the results and comparison flows.

**Files touched:**
- `specs/design/journeys/view-results.html` — new journey documenting the results panel: the bar chart, the edge-aware legend, the line chart, the Sankey. Follow `journey-authoring.md` conventions and copy `build-a-model.html`'s style block.
- `specs/design/journeys/compare-models.html` — new journey documenting the comparison dashboard: the KPI strip, the paired bar chart with its grouped per-system legend, the cumulative overlay, and the decomposition bars.
- `specs/design/index.html` — update the `view-results` and `compare-models` cards from "To author" (`.pill.todo`) to "Live" (`.pill.web` or similar), and link to the new files.

**Tests added/changed:**
- None (documentation only).

**Acceptance:**
- Both journey files open in a browser with no network requests (self-contained HTML).
- The design-hub index links to both new files and they load correctly.
- The corrected legend behaviours are visibly documented (screenshots or inline mockups) in each journey.

**Depends on:** Tasks 1 and 2 (authors against the final implemented behaviour).

---

## Ordering rationale

Tasks 1 and 2 are independent behavioural changes on separate pages with separate test files — they can be reviewed and landed in either order (or in parallel PRs). Task 3 is documentation that reflects the shipped behaviour, so it naturally follows both. The three-task shape avoids splitting tightly-coupled units: the `isEdge` flag and the legend filter that reads it share no meaningful pause point, so they stay in Task 1; the backend name fields and the JS that consumes them share no meaningful pause point, so they stay in Task 2.
