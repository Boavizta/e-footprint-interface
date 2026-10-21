# Hourly chart 500 on an empty dict entry: the calculated-attribute dict template sends every non-quantity entry to the hourly-chart button, including the library's intentional `EmptyExplainableObject`, and the chart view has no exception decorator

- **Status:** CONFIRMED
- **Confidence:** high. Reproduced through the real Django view: all chart and explanation links reachable from edit panels on the four shipped introductory examples were crawled. The three reported URLs are the only failures. The library intends these entries to be empty. A rendered simulation of the template fix removes the chart URL and keeps a working formula button.
- **Reported:** found by the Task 6 diagnostician, not reported by a user. `get_explainable_hourly_quantity_chart_and_explanation` raises `AttributeError: 'EmptyExplainableObject' object has no attribute 'plot_aggregation_strategy'` at `explainable_timeseries_utils.py:86` for three `Sensor-local-storage` entries keyed by `Factory-sensors-starting-up`: `unitary_power_per_usage_pattern`, `energy_per_edge_device_per_usage_pattern` and `use_footprint_per_edge_device_per_usage_pattern`. The view is undecorated, so the result is a raw 500. **The hypothesis held**, with one correction. The trigger is not a "(see graph)" link. It is the timeseries-chart icon button that the calculated-attributes accordion renders for each dict entry in the Factory-sensor device panel, because the panel embeds its components' calculated attributes. The "(see graph)" links in explanation lists already handle empty values correctly.

## Root cause

**1. The library returns empty values on purpose.**
- `e-footprint/efootprint/core/hardware/edge/edge_storage.py:170-173`: `EdgeStorage.unitary_power_per_usage_pattern` always returns `EmptyExplainableObject()`. Its docstring says "Currently always empty: storage operating power is considered neglectable."
- The empty value propagates by design:
  - `energy_per_edge_device_per_usage_pattern` (`e-footprint/efootprint/core/hardware/edge/edge_component.py:145-151`) multiplies it by the deployment count and one hour.
  - `use_footprint_per_edge_device_per_usage_pattern` (`edge_component.py:155-161`) multiplies the energy by carbon intensity.
- `EmptyExplainableObject` stays empty under `*`, `to()` and `set_label()` (`e-footprint/efootprint/abstract_modeling_classes/empty_explainable_object.py:28-29, 100-110`). A probe confirmed that each of the three dict entries is an `EmptyExplainableObject`.

**2. An empty value has no time axis and no unit to chart.**
- `EmptyExplainableObject` (`empty_explainable_object.py:7-62`) has no `start_date` and no `plot_aggregation_strategy`.
  - It reports `unit == "dimensionless"` and `magnitude == 0`.
  - `values()` returns `[]`.
- `plot_aggregation_strategy` exists only on `ExplainableHourlyQuantities` and `ExplainableRecurrentQuantities` (`e-footprint/efootprint/abstract_modeling_classes/explainable_hourly_quantities.py:196-199`, `explainable_recurrent_quantities.py:126-129`).
- The library offers no way to say how an empty value should be aggregated. This is consistent: "no value" means there is no series at all.

**3. Only one interface template routes empty entries to the chart.**
- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_object_dict.html:23-29` branches on one case only. `explainable_quantity` entries go to `explainable_quantity.html`. Everything else goes to `explainable_hourly_quantities.html`, which unconditionally renders the hourly-chart button (`explainable_hourly_quantities.html:11-24`).
- An `empty_explainable_object` dict entry therefore gets a button that calls `get_explainable_hourly_quantity_chart_and_explanation_from_dict`.
- Every other interface path already handles empty values:
  - **Top-level calculated attributes** dispatch dynamically by `class_as_snake_str` (`calculated_attributes_section.html:14-16`). Empty values use `empty_explainable_object.html`, which extends `explainable_object_template.html`. That template shows a disabled "no value" input, the formula button and the calculus-graph link, with no chart (`explainable_object_template.html:11-26`).
  - **"(see graph)" in Input Variables and Direct children** (`components/ancestor_or_child_list_element.html:16-46`) renders a chart link only for `explainable_hourly_quantities` and `explainable_recurrent_quantities`. Empty values fall through to `= {{ elt.efootprint_object }}`, so they show "= no value". The `energy_per_…` explanation shows `b: unitary power per usage pattern in Sensor local storage = no value`.
  - **Formula explanation and calculus graph:** `get_calculated_attribute_explanation_from_dict` and `display-calculus-graph-from-dict` both return 200 for all three empty entries (probe).

**4. The crash path.**
- `views.py:569-582`: the view calls `prepare_timeseries_chart_context`.
- `explainable_timeseries_utils.py:65-67`: that function resolves the dict entry as an `ExplainableObjectWeb` that wraps the empty value (`:34-42`), then calls `prepare_hourly_quantity_data`.
- `explainable_timeseries_utils.py:86` reads `ehq.plot_aggregation_strategy` and raises `AttributeError`.

**5. The view has no decorator, so the failure is invisible.**
- `get_explainable_hourly_quantity_chart_and_explanation` (`e-footprint-interface/model_builder/adapters/views/views.py:569-570`) carries only `@time_it`. Its sibling read views are also undecorated: the recurrent chart (`:584`), the EcoLogits explanation (`:599`) and the calculated-attribute explanation (`:612`).
- The unhandled exception goes to `handler500` (`e_footprint_interface/urls.py:22`), which renders the full recovery page.
- `ComputationMemoryMiddleware.process_exception` turns only `ComputationMemoryLimitExceeded` into a modal (`e_footprint_interface/computation_memory_middleware.py:395-403`).
- htmx 2.0.6 does not swap 5xx responses by default, and no global `htmx:responseError` handler exists. `theme/static/scripts/support.js:56` covers only the feedback link.
- The button's hyperscript runs `openCalculatedAttributesChart()`, which only toggles the container's visibility (`theme/static/scripts/calculated_attributes_timeseries.js:52-60`). The user therefore sees an empty or stale chart pane and no error. This breaks constitution §1.4: server failures must stay visible.
- The omission is not deliberate. No client code handles this error, and the chart JS only toggles classes. The decorated pattern is documented in `specs/architecture/runtime-and-recovery.html` ("Decorated views use the standard exception modal; the middleware supplies the same modal only for undecorated routes"). Wrapping the current view in `render_exception_modal_if_error` returns status 500 with `HX-Reswap: none` and the out-of-band modal (probe).

**6. Why tests missed it.**
- `tests/integration/test_calculated_attributes.py:43-49` charts dict entries only after checking `isinstance(value, ExplainableHourlyQuantities)`. Empty entries are skipped.
- No test asserts which link the template renders.

## Fix approach

1. **Template (the root fix).** In `explainable_object_dict.html:23-29`, replace the two-way branch with the dynamic include already used at `calculated_attributes_section.html:15`:
   `{% include "model_builder/side_panels/edit/calculated_attributes/"|add:sub_item.class_as_snake_str|add:".html" with item=sub_item %}`.
   - Empty entries then render "no value", the formula button and the calculus-graph link, with no chart button. This matches the top-level and "(see graph)" behavior.
   - Quantity and hourly entries render exactly as today.
   - A rendered simulation on `Sensor-local-storage.energy_per_edge_device_per_usage_pattern` emitted no chart URL and a working `get_calculated_attribute_explanation_from_dict` button.
2. **Decorator (§1.4).** Add `@render_exception_modal_if_error` to `get_explainable_hourly_quantity_chart_and_explanation`. For consistency, also add it to the sibling panel-fragment read views `get_explainable_recurrent_quantity_chart_and_explanation`, `get_eco_logits_calculated_attribute_explanation` and `get_calculated_attribute_explanation` (`views.py:584, 599, 612`), placed above `@time_it` as at `views.py:419-420`. A future failure on any of these then shows the standard modal over an untouched canvas instead of an invisible failed swap.

**Rejected alternatives:**
- **Make `prepare_hourly_quantity_data` chart empty values as an all-zero series.** The interface would have to invent a start date, a length and a unit that the library deliberately leaves out. The library owns the meaning, and "no value" is not a dated series in a physical unit (§1.3). This would also be a defensive branch for a route the UI should never offer (§3.1).
- **Add `plot_aggregation_strategy` or a time axis to `EmptyExplainableObject` in the library.** This creates a cross-repo dependency for display behavior the interface already handles elsewhere. An empty value has no unit from which to derive a strategy.
- **Add only the decorator.** Clicking would then show an error modal for a well-defined library state. The "no value" pattern used everywhere else is the correct UX.
- **Add an explicit `{% elif sub_item.class_as_snake_str == "empty_explainable_object" %}` branch.** This works but keeps a hand-maintained branch list. The dynamic include is the established pattern and needs no list.

## Files to touch

- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_object_dict.html`: dynamic include by `sub_item.class_as_snake_str` (`:23-29`).
- `e-footprint-interface/model_builder/adapters/views/views.py`: add `@render_exception_modal_if_error` to the hourly chart view (`:569`) and its calculated-attribute siblings (`:584, :599, :612`). Import it from `model_builder.adapters.views.exception_handling`.
- `e-footprint-interface/tests/unit_tests/adapters/views/`: new regression tests (see Tests).
- `e-footprint-interface/CHANGELOG.md`: `## [Unreleased]` fix entry.

## Tests

- **View/template regression** (new, `tests/unit_tests/adapters/views/test_views_calculated_attributes.py`, Django test client):
  1. Load `iot_industrial`.
  2. `GET /model_builder/open-edit-object-panel/Factory-sensor/`.
  3. Assert the body contains no `get_explainable_hourly_quantity_chart_and_explanation/Sensor-local-storage/` URL.
  4. Assert it does contain `get_calculated_attribute_explanation/Sensor-local-storage/energy_per_edge_device_per_usage_pattern/Factory-sensors-starting-up`.
  5. Assert the CPU and RAM hourly dict entries still render their chart URL.
  - This test fails before the template fix.
- **Rendered-link sweep** (same file): for that panel, request every rendered `get_explainable_hourly_quantity_chart_and_explanation…` URL and assert 200. This locks in the invariant that every chart link the UI renders resolves.
- **Decorator regression** (same file): with `RAISE_EXCEPTIONS` unset, monkeypatch `prepare_hourly_quantity_data` (as imported in `views.py`) to raise. `GET` a valid chart URL and assert status 500, `HX-Reswap: none`, the exception modal markup and the `openModalDialog` trigger. Follow the conventions in `test_exception_handling.py`.
- **Optional integration hardening:** extend `tests/integration/test_calculated_attributes.py:43-49` so that an `EmptyExplainableObject` dict entry asserts the explanation path (`compute_literal_formula_and_ancestors_mapped_to_symbols_list`) works and the hourly preparer is not called. This is low value once the view test exists.
- No E2E test is needed. This is display-only routing, covered at view level.

## Acceptance criteria

- In the iot_industrial Factory-sensor panel, the Sensor local storage dict entries "Unitary power per usage pattern", "Energy per edge device per usage pattern" and "Use footprint per edge device per usage pattern" show "Factory sensors starting up:" with a disabled "no value" field, a formula button and a calculus-graph link, and no timeseries-chart button.
- Clicking the formula button opens the Input Variables / Formula / Direct children explanation (200).
- Every hourly-chart link rendered on the four introductory examples (ecommerce, ai_chatbot, genai_video, iot_industrial) returns 200. Today 632 chart and explanation URLs are reachable from openable panels, 431 of them hourly charts, with exactly three failures.
- An unexpected exception in any calculated-attribute chart or explanation view shows the standard exception modal (HTTP 500, `HX-Reswap: none`) instead of an invisible failed request.

## Risks and side effects

- With the dynamic include, an empty dict entry uses `explainable_object_template.html`. Its collapse id is `collapse-calculated_attributes-{{ attr_name }}` and does not include the key or container (`explainable_object_template.html:29`, `components/get_calculated_attribute_explanation_button.html:8,14`). Dict quantity entries already share this behavior.
  - The bug exists today: the Factory-sensor panel already contains `id="collapse-calculated_attributes-carbon_footprint_manufacturing"` three times, once each for CPU, RAM and storage.
  - In the iot example the newly rendered empty entries are unique (the CPU and RAM entries are hourly), so this fix adds no collision there.
  - This is a separate low-severity bug and is out of scope. Fixing it would mean keying the id by `item.web_id`. Flagged under §3.1.
- The dynamic include requires a template for every `class_as_snake_str` a dict value can take. In current library dicts the value types are quantity, hourly and empty, and all three templates exist. A future dict value type without a template would fail loudly at render, which is acceptable and matches the top-level section.
- Decorating the three sibling views changes only their failure presentation. Successful responses are unchanged, and `RAISE_EXCEPTIONS=1` still raises.

## Flags

- **Invariant:** the interface must not render a chart affordance for an `EmptyExplainableObject`. Template dispatch by `class_as_snake_str` owns this. The chart preparers must not gain an empty-value branch.
- **Cross-repo:** none. The library's empty storage power is intentional (`edge_storage.py:170-173`).
- **Migration/serialization:** none.
- **Sweep coverage gap:** the edit panels of `Sensor-local-storage` and the edge component needs currently fail with `KeyError` before rendering. That is the sibling `check-can-delete-keyerror` diagnostic (`modeling_object_web.py:390`). The sweep reached their dict entries only through the parent device panel. Once that fix lands, the same entries also render in the component's own panel through the same template, so this fix covers them as well. Rerun the sweep after both fixes land.
- **Not reachable, by design:** the System, Device, Network and Country panels also raise `KeyError` (`form_field_generator.py:238` → `efootprint_to_web_mapping.py:111`). The UI never links to them (`ancestor_or_child_list_element.html:4`), so they are not part of this bug.
- **Validation is local only:** shipped examples, Django test client, `RAISE_EXCEPTIONS` unset for the decorator check. Scratch harnesses: `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/hourly/test_hourly_sweep.py` and `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/hourly/test_hourly_fix_probe.py`, both run with `--ds e_footprint_interface.settings --rootdir .` from the interface root.

## Decisions

- 2026-10-21: the expected UX is the existing "no value" pattern (no chart affordance), not an empty or zero chart. This matches top-level calculated attributes and "(see graph)" lists, and respects library ownership of what "empty" means.
- 2026-10-21 (supervisor default per constitution §1.4): all four calculated-attribute read views get `render_exception_modal_if_error` (`views.py:569, 584, 599, 612`), not only the hourly chart view.
