# Results charts total drifts from the Sankey total: daily series rounded to a fixed decimal step in the display unit

- **Status:** CONFIRMED
- **Confidence:** high. I read the code path and reproduced the drift numerically on the shipped `iot_industrial` example (edge modeling) with efootprint 27.0.0, at both native scale and the reporter's scale (kt, 4,748 days).
- **Reported:** Issue #146 (Clémence Knaebel, 2026-09-29, deployed app). The cumulative emissions chart ends at 9.54 kt and the Sankey shows 9.55 kt for the same model (edge modeling, 2027–2039). The reporter attributes this to `to_rounded_daily_values` rounding each daily value to 5 decimals of the display unit, a 10 kg step in kt. The proposed fix is to keep full precision and round only at display, with a test that daily values sum to `system.total_footprint`. **The hypothesis holds.** Two refinements: (1) the drift is not one-directional. `np.round` rounds to nearest and does not truncate, so the error can go either way. In my reporter-scale simulation the chart came out **16.6 t too high**. (2) The error grows linearly with the number of days instead of averaging out, because modeled daily values repeat. Shipping full float64 precision unrounded is wasteful: digits beyond about 7 significant figures are float32 noise. See the Fix approach.

## Root cause

**Where the rounding happens.**
- `EmissionsCalculationService.calculate_daily_emissions` picks a single display unit from the whole-period total: `best_display_unit(system.total_footprint.sum().value)` (`e-footprint-interface/model_builder/domain/services/emissions_calculation_service.py:90`).
- It converts each hourly category series to that unit and passes it to `to_rounded_daily_values` (`emissions_calculation_service.py:92-116`).
- That function bins the hourly values into daily sums and returns `np.round(daily, rounding_depth).tolist()` with `rounding_depth=5` (`e-footprint-interface/model_builder/domain/entities/web_core/model_web_utils.py:46`, `:78`).
- The step is therefore 1e-5 of the display unit. The unit is chosen so the **total over the whole period** is ≥ 1, while the **daily** value of a category can be several orders of magnitude smaller. At kt the step is 10 kg per value. There are up to 9 categories × n_days values.

**Regression origin.**
- Before commit `479e9a7f` ("Implement unified quantity display plan", 2026-03-26), the same 5-decimal rounding was applied to series in their native unit, kg. That is a 10 mg step, which is harmless. In that era the rounding was a precision *increase*: `71dd0f2d` in V0.4.3 raised it to 5 decimals "to avoid rounding errors".
- `479e9a7f` added `.to(display_unit)` before the rounding (`emissions_calculation_service.py:93-94`). This turned a fixed absolute step into a step that grows with the model's total.

**Why it accumulates instead of averaging out.** Two systematic effects, neither of which needs truncation:

1. **Categories below half a step vanish completely.** On `iot_industrial` (display unit t, 2,222 days), `Servers_and_storage_energy`, `Devices_energy` and `Network_energy` have daily values below 5e-6 t on every day. They are sent as 0 for the entire period. `Devices_manufacturing` is zeroed on 1,127 days. Each of these is a loss of up to step/2 per day.
2. **Daily values repeat, so the per-day rounding error is identical day after day.** Usage patterns are periodic. In my check, `Edge_devices_manufacturing` has only 96 distinct sub-step remainders over 2,222 days, and `Servers_and_storage_manufacturing` in `ai_chatbot` is constant (1 distinct remainder). The same signed error of up to ±step/2 is added every day. The worst-case cumulative error is therefore about 9 × n_days × step/2, not √n.

**Measured** (scratch scripts `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/rounding_check.py` and `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/scale_check.py`):

| Case | Rounded chart sum | Unrounded sum | `total_footprint.sum()` |
|---|---|---|---|
| `ai_chatbot` (t, 1,095 d) | 74.09481 | 74.09971 | 74.09970 |
| `iot_industrial` (t, 2,222 d) | 196.31862 | 196.32420 | 196.32419 |
| `iot_industrial` series tiled to 4,748 d, scaled to 9.551 kt | 9.56758 kt (**+16.6 t**) | 9.55100 kt | — |

- With rounding removed, the chart data matches the library total to float32 precision (relative difference about 1e-7). This confirms the reporter's "disabled rounding gives 9.551 kt".
- At kt scale the per-category drift is several tonnes: `Edge_devices_manufacturing` −8.2 t, `Edge_devices_energy` −6.6 t, `Servers_and_storage_manufacturing` −3.3 t. A 10–20 t error is enough to flip the 3-significant-figure display (9.54 vs 9.55 kt).

**Consumers of `window.emissions`** (all affected, none recompute from the library):
- `ModelWeb.system_emissions` is memoized per `ModelWeb` instance only (`e-footprint-interface/model_builder/domain/entities/web_core/model_web.py:97`, `:471-479`). It is serialized inline into the page as `window.emissions = {{ model_web.system_emissions|safe }}` (`e-footprint-interface/model_builder/templates/model_builder/result/result_panel.html:108`).
- Both result charts read it: the yearly/monthly bar chart and the cumulative line chart. `buildChartData` re-sums the daily values per month or year (`sumDailyValuesByDisplayGranularity`, `e-footprint-interface/theme/static/scripts/timeseries_utils.js:1-21`). For the line chart it then takes a running sum (`cumulativeSumFromArray`, `timeseries_utils.js:23-32`), wired at `e-footprint-interface/theme/static/scripts/result_charts/chart.js:52-66`. The cumulative end-point is the plain sum of the rounded daily values, so it carries the full drift.
- Tooltips format the category and section totals through `formatEmissionsQuantity` (`e-footprint-interface/theme/static/scripts/result_charts/tooltip.js:46`, `:81`, `:88`). That function picks a magnitude-aware unit and rounds to 3 significant figures (`e-footprint-interface/theme/static/scripts/result_charts/display.js:50-60`, `:73-88`). Display rounding is already in place. The server rounding is what makes small categories show **0** in tooltips: the #106 symptom, reintroduced by data quantization rather than formatting.
- Y-axis ticks use Chart.js defaults (`e-footprint-interface/theme/static/scripts/result_charts/config.js:163-174`). They are unaffected by input precision.

**Not affected:**
- **Sankey.** It uses the library's `ImpactRepartitionSankey` and its `total_system_value` (`e-footprint-interface/model_builder/adapters/views/sankey_views.py:14`, `:172-173`). This is the canonical total.
- **Comparison dashboard.** It aggregates library hourly footprints by year in kg (`e-footprint-interface/model_builder/domain/services/comparison_service.py:425-447`).
- **Exports** (JSON, sources XLSX). They do not touch these series.
- **Persisted or cached payloads.** No cache, repository or serialization stores `system_emissions`. A grep of `model_builder/adapters` and `e_footprint_interface` finds no emissions payload cache.

**Second caller of the same helper.** `prepare_hourly_quantity_data` (calculated-attribute charts) uses `to_rounded_daily_values` with a unit chosen from the daily-scale value (`best_display_unit(24 * ehq.value)`) (`e-footprint-interface/model_builder/domain/entities/web_core/explainable_timeseries_utils.py:86-106`). Its step is about 1e-5 of a typical daily value, so the issue is immaterial there. Its sum aggregate already comes from the library (`ehq.sum()`, `:111`).

**Library ownership (constitution §1.3).**
- The library owns the total (`ExplainableHourlyQuantities.sum`, float32 accumulation, `e-footprint/efootprint/abstract_modeling_classes/explainable_hourly_quantities.py:230-231`) and the per-category hourly footprints.
- It offers no public daily aggregation or transport-rounding helper. `_round_array_to_sig_figs` is private and tied to display (`e-footprint/efootprint/utils/display.py:69`). `format_quantity_for_display` re-chooses the unit per array (`display.py:84-94`), which breaks the shared-unit contract.
- Daily binning for chart transport is presentation shaping and stays in the interface. The fix must make it faithful to the library total, not replace that total.
- Separately, the draft `results-analysis` feature plans to retire `EmissionsCalculationService` in favor of library-delivered daily projections (`e-footprint-interface/specs/features/results-analysis/plan.html:31-36`, `:160-161`). That feature is not started. This bug should be fixed now.

## Fix approach

**Recommended:** in `to_rounded_daily_values`, replace fixed-decimal rounding with **per-value significant-figure rounding**, 6 significant figures (vectorized NumPy, O(n_hours)). Keep everything else unchanged: the shared display unit, the payload shape and the JS.

**Why this is enough:**
- The source hourly arrays are float32, cast at `model_web_utils.py:31`, so they carry about 7 significant digits. 6 significant figures therefore loses essentially nothing real.
- It bounds the error of *any* sum (month, year or cumulative) at ≤ 5e-7 × Σ|v|, whatever the period length or repetition pattern.
- Small categories keep their magnitude, which removes the "0" tooltips.
- It avoids the 17-digit float64 noise that dropping the rounding entirely would ship.

**Measured at the reporter's scale** (9 series × 4,748 days, raw JSON, uncompressed):

| Option | Payload | Error on total |
|---|---|---|
| Today, 5 decimals | 259 KB | −16.6 t at kt scale |
| 6 sig figs (recommended) | 436 KB, +68 % | 19 kg (2e-6 relative) |
| 5 sig figs | 409 KB | 56 kg |
| 7 sig figs | 461 KB | ≈1 kg |
| No rounding (reporter's literal proposal) | 736 KB, +184 % | exact |

The embedded payload is compressible, but Django adds no GZip middleware (`e-footprint-interface/e_footprint_interface/settings.py:58-69`). Whether the production proxy compresses is unverified. Gzip figures from the tiled synthetic case are unrepresentative and are not cited.

Implement it as a small local helper (`decimals = sig_figs - 1 - floor(log10|v|)` on non-zero values, as the library's private helper does). Renaming the `rounding_depth` parameter to `sig_figs` is fine: there are no external callers. The calculated-attribute chart caller inherits the same policy harmlessly.

**Rejected alternatives:**
- **Drop rounding entirely** (the issue's literal fix). It is correct, but it nearly triples the payload with float32 noise digits, against the mission's frugality on transfers (`e-footprint-interface/specs/mission.md:17-32`).
- **Round the cumulative sum and send its differences** (error diffusion at the current 10 kg step). Payload is unchanged (259 KB) and the total is exact, but sub-step categories stay quantized. A 2.9 kg/month category shows as 0 or 10 kg per month bar (measured monthly error up to 7.3 kg), so the #106-style misleading tooltip remains. It also adds a non-obvious trick to the code.
- **Decimals scaled to period length or total** (for example 9 decimals at 4,748 days: 370 KB, 0.7 kg error). This is an ad hoc formula and still zeroes tiny categories.
- **Fix only the cumulative end-point by injecting the library total.** This creates two truths: the bars and the line would disagree.
- **Wait for `results-analysis`**. That feature is draft and unscheduled, and the bug is user-visible now.

## Files to touch
- `e-footprint-interface/model_builder/domain/entities/web_core/model_web_utils.py` — `to_rounded_daily_values` (`:46-78`): significant-figure rounding (default 6) instead of `np.round(daily, rounding_depth)`. Update the docstring.
- `e-footprint-interface/tests/unit_tests/domain/entities/web_core/test_model_web_utils.py` — adapt `test_to_rounded_daily_values_respects_aggregation_strategy` (`:50-62`, currently passes `rounding_depth=1`) and add the regression cases below.
- `e-footprint-interface/tests/unit_tests/domain/entities/web_core/test_model_web.py` — add a long-period regression next to `test_system_emissions` (`:77`). Existing expectations ([1, 0], [0, 1.1], …) remain valid.
- `e-footprint-interface/CHANGELOG.md` — Fixed entry referencing #146.
- `e-footprint-interface/specs/architecture/layers-and-wrappers.html` — optional one-liner at `:81`: chart daily series are rounded to significant figures, so sums stay faithful to the library total.

No `emissions_calculation_service.py`, JS, template or library change is needed.

## Tests
- **Unit (`test_model_web_utils.py`).**
  - A series in a large unit with a constant sub-step value (for example 2e-6 kt/day for 4,748 days) returns non-zero daily values.
  - Its sum matches the unrounded sum within relative 1e-5.
  - Exact zeros stay 0.
  - Mean aggregation still works.
- **Unit (`test_model_web.py` or `tests/unit_tests/domain/services/`, matching existing placement).**
  - Build a `SystemWithFootprints` stand-in in the style of the existing `test_system_emissions` fixture. Use about 4,748 days of hourly kg data: one dominant category of about 2 t/day, plus one repeated small category of about 2 kg/day and one constant mid-size category whose daily value sits off the 1e-5 kt grid.
  - `display_unit == "kt"`.
  - The sum of all `values` matches `total_footprint.sum()` converted to kt within relative 1e-5. The library sum accumulates in float32.
  - The small category's sum is > 0.
  - This fails on the current code: the small category vanishes, about 9.5 t on about 9.5 kt, 1e-3 relative.
- **Integration (`tests/integration/test_modeling_integration.py`, next to `:120`).**
  - For each introductory example, the summed `system_emissions["values"]` matches `system.total_footprint.sum()` in the display unit within relative 1e-5.
  - Current code fails this on `ai_chatbot` (6.6e-5) and `iot_industrial` (2.8e-5).
- **JS.** No change. `js_tests/result_chart_display.test.js` already covers 3-significant-figure display rounding. Run `npm run jest` once to confirm.

## Acceptance criteria
- For any model, the cumulative chart's final point (all categories stacked) equals the Sankey/library total at the displayed 3-significant-figure precision. The reporter's model shows 9.55 kt on both.
- Categories with small but non-zero emissions show non-zero values in the bar chart tooltips. No "0" appears where the library has emissions.
- `window.emissions` keeps its shape (`dates`, `values`, `display_unit`) and its shared display unit.
- Payload growth is bounded by significant-figure rounding (about +68 % raw at the reporter's scale), not unbounded float64 repr.

## Risks and side effects
- **Payload.** The result page's inline JSON grows by about 70 % for long, large-unit models: about 260 KB to about 440 KB at 9 series × 4,748 days. This is the deliberate precision-vs-transfer trade-off; see Decisions.
- The calculated-attribute charts (`explainable_timeseries_utils.py:106`) switch to the same significant-figure policy. Values in long tails get more digits, and the visible effect is negligible. Their `mean` aggregate (`:108-109`) becomes marginally more precise.
- Very small non-zero values may serialize in exponent notation (`2e-06`). `JSON.parse` and Chart.js handle this natively.
- The library total itself is float32-accumulated (`explainable_hourly_quantities.py:231`). Tests must use a relative tolerance, not equality.

## Flags
- **Invariants:** constitution §1.3 is respected. The library total stays canonical, and the interface only bins and rounds for transport. No modeling logic moves.
- **Serialization/cache:** none. `system_emissions` is computed per request and memoized only on the `ModelWeb` instance. There are no cache keys, no persisted payload and no migration.
- **Cross-repo:** none required. Interface-only. Exposing the library's private `_round_array_to_sig_figs` publicly was considered and is not needed for a few lines of NumPy.
- **Local-only validation:** the reporter's exact model is not available locally. Validation uses the introductory examples and a synthetic kt-scale system. Production payload compression is unverified.
- **Future:** `results-analysis` (draft) plans to retire `EmissionsCalculationService`. The regression test (daily sums ≈ library total) should carry over to whatever replaces it.

## Decisions
- 2026-10-21, user decision: `to_rounded_daily_values` rounds each daily value to 6 significant figures, vectorized in NumPy. This accepts about +68 % raw inline payload at long, large-unit scale in exchange for sums faithful to the library total and non-zero small categories. Rejected: error diffusion and full precision.
- 2026-10-21: the regression test (daily values sum ≈ library `total_footprint.sum()` within relative 1e-5, small categories non-zero) must carry over to whatever replaces `EmissionsCalculationService` in the `results-analysis` feature.
