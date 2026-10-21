# Recurrent constant value reads as a weekly total: the unit box gives no time reference

- **Status:** CONFIRMED
- **Confidence:** high. The library code and the shared template were read directly; the storage field
  uses the same template, so it has the same gap.
- **Reported:** GitHub #150 (Clémence Knaebel, 2026-10-01, deployed app). The "Recurrent volume per edge
  device" form shows "occurrence" and "This constant value will be repeated over the entire canonical week
  (168 hours)", which reads as a weekly total, although 1 occurrence means 1 job per hour (168 per week).
  The report proposed per-field "/ hour" suffixes (occurrence / hour, GB / hour) and no change for CPU,
  RAM and workload. It also asked to confirm the storage rate. Confirmed: see below. The settled fix is
  simpler than the per-field suffix (see Decisions).

## Root cause

- Each of the 168 recurrent values is the amount (or level) for that hour. The library replays them
  hour by hour: `e-footprint/efootprint/abstract_modeling_classes/explainable_recurrent_quantities.py:135`
  (`generate_hourly_quantities_over_timespan`), called from
  `e-footprint/efootprint/core/usage/edge/recurrent_server_need.py:82` and
  `e-footprint/efootprint/core/usage/edge/recurrent_edge_component_need.py:109`. The library descriptions
  say "Hourly …" (`recurrent_server_need.py:34-36`), but the stored unit has no time dimension
  (`occurrence`, `GB_stored`, `cpu_core`…).
- Every recurrent field's constant editor renders the same template:
  `e-footprint-interface/model_builder/templates/model_builder/side_panels/dynamic_form_fields/recurrent_quantities_from_constant.html`.
  The readonly unit box (lines 19-24) shows only the stored unit, and the helper text (lines 28-30) says the
  value "will be repeated over the entire canonical week (168 hours)". Nothing on screen says the value
  applies per hour, so a weekly-total reading is natural. Entering a weekly total gives results 168 times
  too high, and no validation can catch it.
- Storage: `RecurrentEdgeProcess.recurrent_storage_needed` and `RecurrentEdgeStorageNeed.recurrent_need`
  go through the same template with a `GB_stored` unit, so they have the same gap.

## Fix approach

Interface-only, display-only. In the constant editor, the unit box reads `<unit> each hour`. The words
"each hour" are a separate, non-submitted element inside the same visual box. The helper text becomes
"All hours of the canonical week (168 hours) will use this value." "Each hour" reads correctly for both
amounts ("1 occurrence each hour", "2 GB_stored each hour") and levels ("2 cpu_core each hour", "0.5
concurrent each hour"), so no per-field logic is needed.

Box structure: an `<input>` cannot contain other elements. So the existing border, background and
rounded-end classes move to a wrapper (for example a `div` in the input group). The wrapper holds the
existing readonly `__constant_unit` input, made borderless and transparent, followed by a `span` "each
hour". Keep the input's `name`/`id`/`value` unchanged: the form parser posts it as `constant_unit`, and the
component-need add form updates it by id when the component changes
(`model_builder/templates/model_builder/side_panels/add/add_recurrent_edge_component_need.html:31-40`).
The quarter-width class (`w-25`) may need widening so "GB_stored each hour" fits.

Alternatives rejected:
- **Per-hour rate units in the library** (`occurrence / hour`, multiply by one hour when expanding). This
  needs a schema migration and a major version, and it would break the library-wide convention that an
  hourly timeseries value is the amount in its hour slot (web-side hourly series are in `occurrence`
  too).
- **"/ hour" only on fields whose unit aggregates by sum** (`get_plot_aggregation_strategy`). This
  misclassifies storage: `GB_stored` aggregates by mean because the same unit is used for stored levels,
  so the storage rate would get no suffix.
- **Per-field flag** listing the per-hour fields. This works but needs per-field and per-component
  logic; the uniform "each hour" suffix makes it unnecessary.

## Files to touch

- `e-footprint-interface/model_builder/templates/model_builder/side_panels/dynamic_form_fields/recurrent_quantities_from_constant.html`:
  wrapper + "each hour" span around the unit input (lines 19-24); new helper text (lines 28-30).
- `e-footprint-interface/CHANGELOG.md`: `## [Unreleased]` fix entry referencing #150.

## Tests

- `tests/e2e/objects/test_edge_objects.py` (near line 411, which already asserts the unit input value
  `cpu_core`): the "each hour" text is visible beside the unit, and the input value is still `cpu_core`.
  After selecting a storage component, the unit value changes and "each hour" stays.
- A rendered-form unit or integration test, wherever the constant template is rendered today. Assert the
  new helper text and that no form field named `…__constant_unit` contains "each hour".
- Existing posts of `__constant_unit` (`tests/unit_tests/adapters/forms/test_form_data_parser.py:377`,
  `tests/integration/test_edge_objects.py:282`) must pass unchanged.

## Acceptance criteria

- Every recurrent constant editor shows `<unit> each hour` in one visual unit box, for example
  "occurrence each hour" for the recurrent volume per edge device and "GB_stored each hour" for storage.
- The helper text reads "All hours of the canonical week (168 hours) will use this value."
- Saved values and posted units are unchanged; results are identical.
- In the recurrent-edge-component-need add form, changing the component still updates the unit, and
  "each hour" stays beside it.

## Risks and side effects

- Purely presentational; no payload, schema or library change.
- The weekly-pattern editor is intentionally unchanged. Its values are set on hour ranges, so the
  per-hour reading is already explicit.

## Flags

- None: interface-only, no migration, no serialization change.

## Decisions

- 2026-10-21: keep raw pint unit notation (for example `GB_stored`); no friendlier display labels.
- 2026-10-21: fix in the interface only; the library keeps its units and timeseries generation.
- 2026-10-21: uniform "each hour" suffix after the unit for all recurrent constant fields, inside the
  unit box, not submitted. New helper text: "All hours of the canonical week (168 hours) will use this
  value."
- 2026-10-21: no change to the weekly-pattern editor (not ambiguous today).
