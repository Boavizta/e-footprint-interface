# Formula buttons open the wrong explanation in multi-object edit panels: per-attribute collapse ids are keyed by attribute name only, so same-named calculated attributes of different objects in one panel share an id

- **Status:** CONFIRMED
- **Confidence:** high. The real panel was rendered through the Django client for all four introductory examples and for a programmatic `EdgeComputer.from_defaults` system. The click behavior was reproduced with Playwright against the local server (`http://localhost:8000`). A probe confirmed that `item.web_id` is unique for every item rendered in the affected panels.
- **Reported:** found by the Task 9 diagnostician, not reported by a user. The report said the Factory-sensor panel (iot_industrial) contains `collapse-calculated_attributes-carbon_footprint_manufacturing` three times (CPU, RAM, storage) and that formula buttons can open the wrong section. **The hypothesis held**, with one correction. Bootstrap does not resolve `data-bs-target` to the first match: it toggles **every** match. HTMX `hx-target` is the selector that resolves to the first match. Together they cause the misbehavior below.

## Root cause

**1. The id and its targets use only the attribute name.**
- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_object_template.html:29` renders `<div class="collapse" id="collapse-calculated_attributes-{{ item.attr_name_in_mod_obj_container }}">`.
- The formula button targets the same string three times: `hx-target`, `data-bs-target` and `aria-controls` (`components/get_calculated_attribute_explanation_button.html:8,14,16`). The EcoLogits override repeats it (`eco_logits_explainable_quantity.html:7,13,15`).
- The disabled value input and its label have the same flaw: `id="calculated_attributes-{{ attr }}"` and `for=` (`explainable_object_template.html:3,15`, `explainable_quantity.html:6`, `eco_logits_explainable_quantity.html:23`). This is a lower-severity duplicate that only breaks label association.

**2. Several panels render more than one object's calculated attributes.** Each attribute name is unique within one object, but not across objects:
- `EdgeComputerWeb.calculated_attributes_values` concatenates the CPU component, the RAM component and the device itself into **one** section (`model_builder/domain/entities/web_builders/hardware/edge/edge_computer_web.py:19-22`).
- Its `edit_template` is `server_edit.html` (`edge_computer_web.py:11`), which includes a second section for the storage (`model_builder/templates/model_builder/side_panels/server/server_edit.html:7-10`). `ServerWeb` and its subclasses (`model_builder/domain/entities/web_core/hardware/server_web.py:17`) also render server + storage this way.
- `EdgeApplianceWeb` concatenates the appliance component and the device (`edge_appliance_web.py:11-16`).
- `ExternalAPIWeb` concatenates the API and its server (`services/external_api_web.py:24-26`).
- Each section loops over the items and includes the per-class template (`side_panels/edit/calculated_attributes_section.html:14-16`). No object identity reaches the id.

**3. One dict can also collide with itself.** `explainable_object_dict.html:23-29` renders every quantity entry of one dict through `explainable_quantity.html`. All entries share the dict's `attr_name_in_mod_obj_container`, so they share one collapse id.
- No current example dict holds `ExplainableQuantity` values. A probe of every calculated dict in the four examples found only hourly and empty values.
- After Task 9, empty entries also render through `explainable_object_template.html`. A model with two or more edge usage patterns would then repeat `collapse-calculated_attributes-unitary_power_per_usage_pattern` (and the `energy_…`/`use_footprint_…` ids) once per pattern inside one storage dict. This is derived from the template code; it was not rendered, because the shipped iot example has a single edge usage pattern.

**4. Measured duplicates.** The probe matched real `id="…"` attributes only, not `data-*-id`. Edit panels of the four examples:

| Panel | Duplicate id | Count | Owners |
|---|---|---|---|
| iot_industrial `Factory sensor` (EdgeComputer) | `collapse-calculated_attributes-carbon_footprint_manufacturing` and `calculated_attributes-carbon_footprint_manufacturing` | 3 each | `Factory-sensor-CPU`, `Factory-sensor-RAM` (EdgeComputer section), `Sensor-local-storage` (EdgeStorage section) |
| iot_industrial `Sensor data server`; ecommerce `Web application server` and `Product database server`; ai_chatbot `Chat web application server`; genai_video CDN server (all BoaviztaCloudServer) | same two ids | 2 each | server and its storage |

- A programmatic `EdgeComputer.from_defaults` + `EdgeStorage.from_defaults` system reproduces the 3x duplicate. The builder is the same as `_build_basic_edge_no_server` in `tests/integration/test_results_views_smoke.py:93-110`.
- A plain `Server.from_defaults` panel (`minimal_system`) has none, because `carbon_footprint_manufacturing` is calculated only on the Boavizta builder.
- These are the only duplicate ids in those panels.

**5. User-visible effect (verified in Chromium against localhost:8000, iot_industrial, Factory-sensor panel, EdgeComputer section open).**
- HTMX resolves `hx-target` to the **first** match. Bootstrap 5.3.3 (`theme/static/scripts/external_librairies/bootstrap.bundle.min.js:2`) toggles **all** matches: the collapse data-API handler loops over `SelectorEngine.getMultipleElementsFromSelector(this)`, i.e. `querySelectorAll` (`node_modules/bootstrap/js/src/collapse.js:280-289`, `dom/selector-engine.js:119-123`).
- Observed sequence:
  1. Click RAM's formula button. The browser fetches RAM's explanation, but it is swapped into the **CPU** row's collapse. All three collapses open (CPU, RAM and the hidden storage one). RAM's own collapse stays empty.
  2. Click CPU's button. CPU's explanation replaces RAM's in the CPU slot, and all three collapses close.
  3. Click RAM's button again. `hx-trigger="click once"` (`get_calculated_attribute_explanation_button.html:9`) sends no request, and all three collapses open again. RAM's explanation can no longer be reached until the panel is reopened.
- The explanation fragment itself is correct, because its root id is `ancestors-formula-and-children-{{ explained_obj.web_id }}` (`components/ancestors_formula_and_children.html:2,53`). Only the placement and toggling are wrong.

**6. What is not affected.**
- **Dict group toggles** are already scoped: `collapse-calculated_attributes_{attr}_{item.web_id}` and `icon_accordion_{web_id}` (`explainable_object_dict.html:8-12,21`).
- **Outer section ids** are `collapseCalculatedAttributes{class}` (`calculated_attributes_section.html:6,11`). They are distinct per section in every multi-section panel (server or edge computer class + `Storage`/`EdgeStorage`). Separate a11y nit: `aria-controls` at `:7` is the constant `collapseCalculatedAttributes` and does not match the id.
- **Chart singletons** `#chart-calculated-attribute`, `chart-render-*` and `calculate-attribute-label` (`calculated_attribute_chart.html:4,34`) hold one chart at a time by design.
- **Accordion state restoration** is unaffected. `restoreAccordionStateInFragment` touches only `.accordion-collapse` elements, and only in OOB responses (`theme/static/scripts/model_builder_main.js:314-357`). The per-attribute collapses are plain `.collapse`.
- **No JS** depends on the id format: a grep of `theme/static/scripts` found no references.
- **Two-model comparison is not relevant.** `#sidePanel` is a singleton bound to the active slot, and switching slots closes it (`specs/architecture/workspace.html:39`). So no cross-slot prefix is needed.

**7. The right identity already exists.**
- `ObjectLinkedToModelingObjWeb.web_id` returns `css_escape(efootprint_object.id)` (`model_builder/domain/entities/web_abstract_modeling_classes/object_linked_to_modeling_obj_web.py:38-40`).
- The library id is `{attr}-in-{container id}`, or `{attr}[{key id}]-in-{container id}` for dict entries (`e-footprint/efootprint/abstract_modeling_classes/object_linked_to_modeling_obj.py:102-109`).
- So `web_id` already encodes the attribute, the container and the dict key. Probe results:
  - All 19 collapse-bearing items in the Factory-sensor panel have distinct `web_id`s, e.g. `carbon_footprint_manufacturing-in-Factory-sensor-CPU`, `…-in-Factory-sensor-RAM` and `…-in-Sensor-local-storage`.
  - Empty dict entries become `unitary_power_per_usage_pattern5bFactory-sensors-starting-up5d-in-Sensor-local-storage`.
  - Every `web_id` starts with the attribute name, a letter, so `#collapse-calculated_attributes-{web_id}` is a valid selector.
- Both precedents in this template folder already key by this `web_id`: the dict toggle and `ancestors-formula-and-children-*`. `specs/architecture/rendering.html:75` defines `web_id` as the DOM identity, separate from the route identity `route_id`.

## Fix approach

Key every per-item id and its references by `item.web_id`, which already includes the attribute name:
- `explainable_object_template.html:29`: `id="collapse-calculated_attributes-{{ item.web_id }}"`.
- `components/get_calculated_attribute_explanation_button.html:8,14,16` and `eco_logits_explainable_quantity.html:7,13,15`: the same string in `hx-target`, `data-bs-target` and `aria-controls`.
- The input id and label `for` (`explainable_object_template.html:3,15`, `explainable_quantity.html:6`, `eco_logits_explainable_quantity.html:23`): `calculated_attributes-{{ item.web_id }}`.
  - Keep `name=` unchanged. The inputs are disabled and never submitted.
- Optional one-character a11y fix in the same pass: `calculated_attributes_section.html:7` `aria-controls="collapseCalculatedAttributes{{ object_to_edit.class_as_simple_str }}"`.
- Update the three E2E tests that match the old exact string (see Tests).

**Rejected alternatives:**
- **Relative HTMX targets** (`hx-target="next .collapse"`). This fixes the swap but not Bootstrap. `data-bs-target` is a document-wide selector that toggles every match, so the duplicate ids and `aria-controls` would remain.
- **A template-passed prefix** (`with id_prefix=object_to_edit.web_id` through the section include). The section owner is not the item owner: the CPU and RAM items render inside the EdgeComputer section. This would also need plumbing through every include and the dict loop. `item.web_id` is already unique per item, including dict entries.
- **`modeling_obj_container.route_id` + attr (+ `key_in_dict.route_id`).** This is the same identity rebuilt by hand. Route ids are the URL contract (`rendering.html:75`), not the DOM contract.
- **Dropping colliding attributes in the wrappers.** These are distinct calculated values of distinct objects, so hiding them papers over the bug (constitution §3.1).
- **A system-id prefix.** Not needed, because the side panel is a per-active-slot singleton.

## Files to touch

- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_object_template.html`: collapse id (`:29`), input id and label `for` (`:3,15`).
- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/components/get_calculated_attribute_explanation_button.html`: `hx-target`, `data-bs-target` and `aria-controls` (`:8,14,16`).
- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/eco_logits_explainable_quantity.html`: the same three references (`:7,13,15`) and the input id (`:23`).
- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_quantity.html`: input id (`:6`).
- Optional: `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes_section.html`: `aria-controls` (`:7`).
- `e-footprint-interface/tests/unit_tests/adapters/views/test_views_calculated_attributes.py`: regression test. Task 9 creates this file, so add to it.
- `e-footprint-interface/tests/e2e/test_calculus_graph.py:59`, `tests/e2e/objects/test_external_api_objects.py:70,74` and `tests/e2e/objects/test_video_external_api_objects.py:147,149`: selector updates.
- `e-footprint-interface/CHANGELOG.md`: `## [Unreleased]` fix entry. For example: "Formula buttons in device and server edit panels now open the explanation of their own component instead of another component's."

## Tests

- **View regression (fails today)** in `tests/unit_tests/adapters/views/test_views_calculated_attributes.py`, with the Django client and a programmatic system as `specs/testing.md` requires (efootprint classes, not JSON).
  - Setup: build `EdgeStorage.from_defaults` + `EdgeComputer.from_defaults` + `RecurrentEdgeProcess` + `EdgeFunction` + `EdgeUsageJourney` in **two** `EdgeUsagePattern`s, in a `System`. Use the shape of `tests/integration/test_results_views_smoke.py:93-110`, and save it with `SessionSystemRepository(client.session).save_data(system_to_json(system, save_computed_state=False))`. Then `GET /model_builder/open-edit-object-panel/{computer.id}/`.
  - Assert no `id="…"` value occurs twice. Use a regex that excludes `data-*-id`, such as `(?<![\w-])id="([^"]+)"`. Today this yields 3x `collapse-calculated_attributes-carbon_footprint_manufacturing`.
  - Assert the CPU button whose `hx-get` contains `/get_calculated_attribute_explanation/{cpu_id}/carbon_footprint_manufacturing/` has `hx-target` and `data-bs-target` equal to `#collapse-calculated_attributes-carbon_footprint_manufacturing-in-{cpu web id}`, and that this id exists in the body.
  - With two edge usage patterns, once Task 9 has landed, the same no-duplicate assertion also covers the within-dict empty entries.
- **E2E selector updates:** prefix matches stay unambiguous in those single-object panels.
  - `test_calculus_graph.py:59`: `button[data-bs-target^='#collapse-calculated_attributes-duration-in-']`.
  - `test_external_api_objects.py:70,74` and `test_video_external_api_objects.py:147,149`: `[data-bs-target^='#collapse-calculated_attributes-generation_latency-in-']` and `[id^='collapse-calculated_attributes-generation_latency-in-']`.
  - `test_calculated_attributes.py:62` and `test_calculus_graph.py:101` already use a prefix on the unchanged dict id. Leave them.
  - Run these three E2E files (constitution §2.2).
- No new E2E test and no Jest test: no JS changes. The view test owns the id contract, and the existing E2E tests still exercise click → swap → explanation.

## Acceptance criteria

- In the iot_industrial Factory-sensor panel, clicking the formula button of "Carbon footprint manufacturing" on the RAM row opens only the collapse under the RAM row, and it shows RAM's explanation (`ancestors-formula-and-children-carbon_footprint_manufacturing-in-Factory-sensor-RAM`). The CPU and storage collapses stay closed. Clicking CPU's button opens CPU's explanation under the CPU row without closing or refilling RAM's.
- Repeated clicks toggle only the clicked row, and every row's explanation stays reachable.
- No edit panel of the four introductory examples contains a duplicate `id` attribute. Today 6 panels do.
- The updated E2E tests (calculus graph, GenAI and video external API) pass.

## Risks and side effects

- Ids get longer and include escaped container ids, e.g. `collapse-calculated_attributes-carbon_footprint_manufacturing-in-Factory-sensor-CPU`. They are still valid selectors because every `web_id` starts with the attribute name (`object_linked_to_modeling_obj_web.py:38-40`).
- `ExplainableObjectWeb.web_id` is not system-prefixed. That is acceptable because only one side panel exists at a time. If calculated-attribute markup is ever rendered inside resident canvases or the comparison dashboard, it would need the `sys-` prefix.
- The dict group id `collapse-calculated_attributes_{attr}_{web_id}` (underscore separators, attribute repeated) stays as is, so the E2E prefix selectors on it keep working. Unifying the two formats is cosmetic and out of scope.
- The dict label `for="calculated_attributes-{attr}"` (`explainable_object_dict.html:16`) points to no input today. It is harmless and is in Task 9's file, so leave it unless Task 9 touches that line.

## Flags

- **Shared files with Task 9:** no product template overlaps. Task 9 edits `explainable_object_dict.html` and `views.py`; this task edits `explainable_object_template.html`, the button component, and `explainable_quantity.html`/`eco_logits_explainable_quantity.html`.
  - The test file overlaps: Task 9 creates `tests/unit_tests/adapters/views/test_views_calculated_attributes.py`. Land this task **after Task 9** and append to that file.
  - Coupling: Task 9 routes empty dict entries through `explainable_object_template.html`. With this fix in place, those entries get per-key ids, which closes the within-dict collision Task 9 noted under its risks.
- **Constitution:** §2.2 (the E2E tests depend on the exact id string and must be updated in the same change), §2.6 (CHANGELOG entry), §3.1 (no wrapper-level filtering of colliding attributes).
- **Cross-repo:** none. The library id format (`object_linked_to_modeling_obj.py:102-109`) is used as-is.
- **Migration/serialization:** none. These are DOM ids only.
- **Docs:** optionally add one line under `specs/architecture/rendering.html` "Calculated-dict route identities" (`:75`): per-item calculated-attribute DOM ids derive from the item's `web_id`.
- **Validation:** local only. Scratch harnesses, run from the interface root with `PYTHONPATH=. DJANGO_SETTINGS_MODULE=e_footprint_interface.settings poetry run pytest -s -c pyproject.toml --rootdir=. -p tests.fixtures.system_builders <file>`:
  - `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/repro/test_dupids_collapse.py`
  - `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/repro/test_webid_scope_probe.py`
  - Browser probe: `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/repro/browser_collapse_probe.py` (needs the local server).
- **Sweep gap:** the `Sensor-local-storage` and edge component-need panels fail with `KeyError` before rendering (`check-can-delete-keyerror` / Task 6), and `ExternalAPIServer` panels are not directly openable. They were checked only through their parent panels. Rerun the duplicate-id sweep after Task 6 lands.

## Decisions

- 2026-10-21 (diagnostician default, no user fork): scope by the existing `item.web_id` rather than a new prefix or `route_id`, matching the dict-toggle and `ancestors-formula-and-children-*` precedents in the same template folder.
