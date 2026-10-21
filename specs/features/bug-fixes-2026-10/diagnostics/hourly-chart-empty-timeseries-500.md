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
- `views.py:573-586`: the view calls `prepare_timeseries_chart_context`.
- `explainable_timeseries_utils.py:65-67`: that function resolves the dict entry as an `ExplainableObjectWeb` that wraps the empty value (`:34-42`), then calls `prepare_hourly_quantity_data`.
- `explainable_timeseries_utils.py:86` reads `ehq.plot_aggregation_strategy` and raises `AttributeError`.

**5. The view has no decorator, so the failure is invisible.**
- `get_explainable_hourly_quantity_chart_and_explanation` (`e-footprint-interface/model_builder/adapters/views/views.py:573-574`) carries only `@time_it`. Its sibling read views are also undecorated: the recurrent chart (`:588`), the EcoLogits explanation (`:603`) and the calculated-attribute explanation (`:616`).
- The unhandled exception goes to `handler500` (`e_footprint_interface/urls.py:22`), which renders the full recovery page.
- `ComputationMemoryMiddleware.process_exception` turns only `ComputationMemoryLimitExceeded` into a modal (`e_footprint_interface/computation_memory_middleware.py:395-403`).
- htmx 2.0.6 does not swap 5xx responses by default, and no global `htmx:responseError` handler exists. `theme/static/scripts/support.js:56` covers only the feedback link.
- The button's hyperscript runs `openCalculatedAttributesChart()`, which only toggles the container's visibility (`theme/static/scripts/calculated_attributes_timeseries.js:52-60`). The user therefore sees an empty or stale chart pane and no error. This breaks constitution §1.4: server failures must stay visible.
- The omission is not deliberate. No client code handles this error, and the chart JS only toggles classes. The decorated pattern is documented in `specs/architecture/runtime-and-recovery.html` ("Decorated views use the standard exception modal; the middleware supplies the same modal only for undecorated routes"). Wrapping the current view in `render_exception_modal_if_error` returns status 500 with `HX-Reswap: none` and the out-of-band modal (probe).

**6. Why tests missed it.**
- `tests/integration/test_calculated_attributes.py:43-49` charts dict entries only after checking `isinstance(value, ExplainableHourlyQuantities)`. Empty entries are skipped.
- No test asserts which link the template renders.

## Reproduction

- `tests/unit_tests/adapters/views/test_views_calculated_attributes.py::test_empty_calculated_dict_entries_render_no_chart_and_fragment_views_never_fail_silently` — Python unit, view boundary (Django test client, `raise_request_exception = False`, `RAISE_EXCEPTIONS` unset); fails on `dev@8f8c63a1`. Fixture `edge_computer_system_data` (same file): an `EdgeComputer.from_defaults` with an `EdgeStorage`, its CPU and RAM components, one `RecurrentEdgeProcess` and one `EdgeUsagePattern`, built programmatically rather than from the iot example. It asserts, in the edge computer's edit panel:
  1. the three empty storage dict entries render no hourly-chart URL and do render their `get_calculated_attribute_explanation/<storage>/<attr>/<usage pattern>` URL;
  2. CPU and RAM chart URLs remain, and every rendered chart URL returns 200;
  3. the empty entry's chart URL, requested directly, returns 200 or the standard exception modal (500, `HX-Reswap: none`, `openModalDialog`);
  4. after another tab loads a different model into the session, the stale hourly-chart, recurrent-chart, explanation and `ask-delete-object` URLs also return the modal, never a raw 500.
  The storage keeps legitimate hourly chart URLs (`cumulative_unitary_storage_need_per_usage_pattern`, `manufacturing_footprint_per_edge_device*`), so the assertion is per empty entry, not "no storage chart URL".
- Assertion failure (`--runxfail`):
  ```
  E   AssertionError: assert '/model_builder/get_explainable_hourly_quantity_chart_and_explanation/4126ddeb-b74/unitary_power_per_usage_pattern/b0cf0ec4-1e0' not in ['/model_builder/get_explainable_hourly_quantity_chart_and_explanation/fd127d9a…', …]
  tests/unit_tests/adapters/views/test_views_calculated_attributes.py:65: AssertionError
  ```
- Traceback of the raw 500 behind that chart URL (trimmed, innermost last; `raise_request_exception = True`):
  ```
  django/core/handlers/base.py:197 _get_response
  e-footprint/efootprint/utils/tools.py:66 wrapper                      (@time_it, the only decorator)
  model_builder/adapters/views/views.py:577 get_explainable_hourly_quantity_chart_and_explanation
  model_builder/domain/entities/web_core/explainable_timeseries_utils.py:67 prepare_timeseries_chart_context
  model_builder/domain/entities/web_core/explainable_timeseries_utils.py:86 prepare_hourly_quantity_data
  AttributeError: 'EmptyExplainableObject' object has no attribute 'plot_aggregation_strategy'
  ```
  With exceptions not re-raised, the response is `500`, `HX-Reswap` absent, `HX-Trigger-After-Settle` absent, body is the `handler500` recovery page.
- Watch:
  - `sub_item.class_as_snake_str` at `model_builder/domain/entities/web_abstract_modeling_classes/object_linked_to_modeling_obj_web.py:72` → `'empty_explainable_object'` for each of the three storage dict entries (`type(sub_item.efootprint_object).__name__ == 'EmptyExplainableObject'`)
  - `sub_item.class_as_snake_str == "explainable_quantity"` at `model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_object_dict.html:24` → `False`, so line 27 includes `explainable_hourly_quantities.html`
  - `{% url 'get_explainable_hourly_quantity_chart_and_explanation_from_dict' … %}` at `model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_hourly_quantities.html:13` → `/model_builder/get_explainable_hourly_quantity_chart_and_explanation/<storage id>/unitary_power_per_usage_pattern/<usage pattern id>`, with no formula button (no `get_calculated_attribute_explanation` URL for the entry)
  - `ehq.plot_aggregation_strategy` at `model_builder/domain/entities/web_core/explainable_timeseries_utils.py:86` → `AttributeError` on `EmptyExplainableObject`
  - decorators on `get_explainable_hourly_quantity_chart_and_explanation` at `model_builder/adapters/views/views.py:573` → `@time_it` only; response `500`, `HX-Reswap` `None`. Same for `ask_delete_object` at `model_builder/adapters/views/views_deletion.py:14`: the stale id raises `KeyError` at `model_builder/domain/entities/web_core/model_web.py:289` → raw `500`
- Debug recipe: break at `tests/unit_tests/adapters/views/test_views_calculated_attributes.py:62` (after the panel request) and inspect `panel`/`chart_urls`; unmasked run: `poetry run pytest tests/unit_tests/adapters/views/test_views_calculated_attributes.py --runxfail -x`. To see the view raise, set `client.raise_request_exception = True` or run with `RAISE_EXCEPTIONS=1`.
- Discrimination: a scratch plugin (`/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/a41b7a33-6432-494e-94e6-03d14dee464c/scratchpad/task9/fix_plugin.py`) that adds the dynamic include through a scratch template dir and wraps the four read views and `ask_delete_object` in `render_exception_modal_if_error`, then reloads the URLconf, makes the test pass under `--runxfail`. The template change alone still fails (raw 500 on the empty entry's direct chart URL). The decorators alone still fail (chart URL rendered). Leaving out only `ask_delete_object` still fails on the stale `ask-delete-object` URL.
- S5 coverage: on `dev`, the reachable raw-500 paths without monkeypatching are stale object ids, which raise `KeyError` at `model_web.py:289` in the four read views and in `ask_delete_object`. The test covers them through a stale page, except the EcoLogits explanation, because an edge model holds no EcoLogits URL. The remaining S5 views have no reproducible defect on `dev`:
  - `get_calculus_graph` returns its own 404 for a missing key.
  - `source_table_row_editor` returns 404 for stale or unknown ids and attributes.
  - `open_help_drawer` returns 404 for an unknown class.
  - `source_table`, `sankey_form`, `sankey_cards` and `sankey_delete_card` returned 200 on the probed inputs.
  - `display_calculus_graph` raises on a stale id, but it is a `target="_blank"` full page (`components/calculus_graph_link.html`), which the task may exempt.
  Their decoration is hardening; it relies on the decorator's existing modal tests.

## Fix approach

1. **Template (the root fix).** In `explainable_object_dict.html:23-29`, replace the two-way branch with the dynamic include already used at `calculated_attributes_section.html:15`:
   `{% include "model_builder/side_panels/edit/calculated_attributes/"|add:sub_item.class_as_snake_str|add:".html" with item=sub_item %}`.
   - Empty entries then render "no value", the formula button and the calculus-graph link, with no chart button. This matches the top-level and "(see graph)" behavior.
   - Quantity and hourly entries render exactly as today.
   - A rendered simulation on `Sensor-local-storage.energy_per_edge_device_per_usage_pattern` emitted no chart URL and a working `get_calculated_attribute_explanation_from_dict` button.
2. **Decorator (§1.4).** Add `@render_exception_modal_if_error` to `get_explainable_hourly_quantity_chart_and_explanation`. For consistency, also add it to the sibling panel-fragment read views `get_explainable_recurrent_quantity_chart_and_explanation`, `get_eco_logits_calculated_attribute_explanation` and `get_calculated_attribute_explanation` (`views.py:588, 603, 616`), placed above `@time_it` as at `views.py:423-424`. A future failure on any of these then shows the standard modal over an untouched canvas instead of an invisible failed swap.

**Rejected alternatives:**
- **Make `prepare_hourly_quantity_data` chart empty values as an all-zero series.** The interface would have to invent a start date, a length and a unit that the library deliberately leaves out. The library owns the meaning, and "no value" is not a dated series in a physical unit (§1.3). This would also be a defensive branch for a route the UI should never offer (§3.1).
- **Add `plot_aggregation_strategy` or a time axis to `EmptyExplainableObject` in the library.** This creates a cross-repo dependency for display behavior the interface already handles elsewhere. An empty value has no unit from which to derive a strategy.
- **Add only the decorator.** Clicking would then show an error modal for a well-defined library state. The "no value" pattern used everywhere else is the correct UX.
- **Add an explicit `{% elif sub_item.class_as_snake_str == "empty_explainable_object" %}` branch.** This works but keeps a hand-maintained branch list. The dynamic include is the established pattern and needs no list.

## Files to touch

- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_object_dict.html`: dynamic include by `sub_item.class_as_snake_str` (`:23-29`).
- `e-footprint-interface/model_builder/adapters/views/views.py`: add `@render_exception_modal_if_error` to the hourly chart view (`:573`) and its calculated-attribute siblings (`:588, :603, :616`). Import it from `model_builder.adapters.views.exception_handling`.
- `e-footprint-interface/tests/unit_tests/adapters/views/test_views_calculated_attributes.py`: remove the reproduction's expected-failure marker (see Tests).
- `e-footprint-interface/CHANGELOG.md`: `## [Unreleased]` fix entry.

## Tests

- The reproduction (`tests/unit_tests/adapters/views/test_views_calculated_attributes.py::test_empty_calculated_dict_entries_render_no_chart_and_fragment_views_never_fail_silently`) is the task's only test. Remove its expected-failure marker. It covers the template dispatch, the rendered-link sweep for the panel, the direct empty-entry chart URL, and the stale-page modal for the hourly chart, recurrent chart, explanation and `ask_delete_object` views.
- No monkeypatched decorator test and no URLconf decoration test: the optional URLconf test is dropped, as no new public contract is named. The S5 views with no reproducible defect on `dev` rely on the reproduction and on the decorator's existing modal tests (`tests/unit_tests/adapters/views/test_views_addition.py`, `test_views_edition.py`, `test_sankey_views.py`).
- Task 10 appends its reproduction to the same file and reuses the `edge_computer_system_data` fixture.
- No integration or E2E test: this is display-only routing, covered at the view boundary.

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
