# Deleting an edge computer's CPU/RAM or an appliance's component reports success and changes nothing: an interface override declares a library-built list as a removal target, and the edit path drops it without telling anyone

- **Status:** CONFIRMED
- **Confidence:** high. Reproduced through the real Django views on `iot_industrial.json` (CPU and RAM) and on that example plus a created `EdgeAppliance`, with and without `RAISE_EXCEPTIONS`. The persisted session state was read back after each run. A probe of the recommended fix (Task 6's `.get` patch, plus the placement override described below) gives the blocking modal and keeps edits re-rendering the parent card. The probe was monkeypatched, not committed.
- **Reported:** found by the Task 6 diagnostician, not reported by a user: "Edge computer CPU/RAM (and likely appliance) component deletion is a silent no-op. The overrides at `edge_computer_cpu_component.py:5-8` etc. declare the non-constructor `components` list a removal target. `ask-delete` on `Factory-sensor-CPU` offers 'Yes, delete', and `delete-object` returns 200 and re-renders the Factory sensor card. The saved model still contains the CPU component with `components` unchanged. The expected behavior is probably the same blocking modal this fix gives EdgeStorage." **Hypothesis held**, appliance included. Two clarifications follow:
  - The overrides are not dead code. They exist so that an edit to a component re-renders its owning device's card. Deleting them alone turns every CPU/RAM/appliance-component edit into an error modal.
  - No exception is swallowed. The removal edit is a genuine no-op.

## Root cause

### The library: these components are internal and cannot be removed

- `EdgeComputer.__init__` has no `components` parameter. It passes `components=[]` to `EdgeDevice` (`e-footprint/efootprint/builders/hardware/edge/edge_computer.py:148-154`). `after_init` then builds `[cpu, ram, self.storage]` (`:186-191`).
- `cpu_component` and `ram_component` are `next(...)` lookups over `components` (`:195-200`). An `EdgeComputer` without them raises `StopIteration` on every derived attribute.
- `EdgeComputer.self_delete` deletes its CPU and RAM itself (`:218-223`).
- The docstrings say "Internal … created automatically by an EdgeComputer" (`:15`, `:55`).
- `EdgeAppliance` follows the same pattern: `components=[]` in `__init__` (`e-footprint/efootprint/builders/hardware/edge/edge_appliance.py:72-74`), `after_init` builds `[appliance_component]` (`:87-90`), `appliance_component` is `components[0]` (`:94-95`), `self_delete` cascades (`:101-105`), and the class is documented as internal (`:11`).
- The library forbids deleting an object that still has containers: `ModelingObject.self_delete` raises `PermissionError` (`e-footprint/efootprint/abstract_modeling_classes/modeling_object.py:678-681`).

So the library offers no way to remove one of these components from its device. It can only be deleted with the device. The correct UI answer is the "referenced by &lt;owner&gt;" blocking modal. This is the same outcome Task 6 gives `EdgeStorage`, recurrent component needs and EcoLogits servers.

By contrast, a custom `EdgeDevice` takes `components: List[EdgeComponent]` as a constructor input (`e-footprint/efootprint/core/hardware/edge/edge_device.py:59-66`). Its user-added components are list-removable, and they delete correctly today (sweep control below).

### The interface: an override that says one thing for rendering and another for deletion

`EdgeComputerCPUComponentWeb`, `EdgeComputerRAMComponentWeb` and `EdgeApplianceComponentWeb` override `list_containers_and_attr_name_in_list_container` to return `[self.edge_device], "components"` (`e-footprint-interface/model_builder/domain/entities/web_builders/hardware/edge/edge_computer_cpu_component.py:5-8`, `edge_computer_ram_component.py:5-8`, `edge_appliance_component.py:7-10`). They were added in `9e247e7b` ("Fix EdgeAppliance and EdgeComputer calculated attributes", 2025-11-18). They are the only overrides of that property apart from `UsagePatternWebBaseClass` (`e-footprint-interface/model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py:52-55`). The property has two consumers:

1. **Rendering (load-bearing).** `mirrored_cards` turns each list container into a nested mirror, `type(self)(…, list_container=container_mirror)` (`e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:412-432`). From there, `top_parent` resolves to the edge computer or appliance card (`:453-457`). Edits use `edited_obj.mirrored_cards` (`e-footprint-interface/model_builder/application/use_cases/edit_object.py:117`), and the presenter re-renders each mirror's `top_parent` (`e-footprint-interface/model_builder/adapters/presenters/htmx_presenter.py:267-284`). That is why a CPU rename re-renders the Factory sensor card.
   - Removing the override with Task 6's patch applied gives `mirrored_cards == [self]` at root.
   - The edit then tries to render `object_cards/edge_computer_c_p_u_component_card.html`, which does not exist. The result is a 500 error modal, even though the rename has already been persisted (probe `task6_plus_removal`).
2. **Deletion (the bug).** `DeleteObjectUseCase._container_removal_targets` reads the same property (`e-footprint-interface/model_builder/application/use_cases/delete_object.py:69`):
   - `check_can_delete` sees a list container. It skips both the required-relationship block and the direct-reference block (`:89-118`; the latter is `if … and not list_or_dict_containers`, `:106`), then returns `can_delete=True` (`:140-149`). The modal offers "Yes, delete".
   - `_delete` takes the list branch (`:180-219`). It builds `{"name": …, "components": [ram, storage]}` (`:200-205`) and calls `EditService.edit_with_cascade_cleanup(edge_computer, …)` (`:208`).
   - `prepare_input_changes` skips every key that is not in the container's `__init__` signature (`e-footprint-interface/model_builder/domain/object_factory.py:176-181`). `components` is not in `EdgeComputer`'s signature, so it produces zero changes.
   - `apply_input_edits` runs no `ModelingUpdate` when nothing is proposed (`:352-356`).
   - The list branch never calls `self_delete` on the target. It relies on the cascade cleanup, which deletes only orphaned **accordion children** (`e-footprint-interface/model_builder/domain/services/edit_service.py:57-69`). The CPU is neither an accordion child nor an orphan.
   - The use case returns `was_list_deletion=True`. The presenter re-renders the edited container's top card (`htmx_presenter.py:318-329`), so the user sees a normal post-delete refresh.

**Observed through the views** (`scratchpad/silentdel/test_silent_repro.py`):
- `ask-delete-object/Factory-sensor-CPU/` returns 200 with "Are you sure you want to delete this EdgeComputerCPUComponent? Yes, delete".
- `delete-object/Factory-sensor-CPU/` returns 200 with a `hx-swap-oob='outerHTML:#sys-…-EdgeComputer-Factory-sensor'` card. It is the same with `RAISE_EXCEPTIONS=1`.
- A spy reports `prepare_input_changes` skipping `('Factory-sensor', 'components')`, 0 changes and 0 `self_delete` calls.
- Session state after the call: `EdgeComputerCPUComponent/Factory-sensor-CPU` is still present. `EdgeComputer/Factory-sensor.components` is unchanged (`['Factory-sensor-CPU', 'Factory-sensor-RAM', 'Sensor-local-storage']`), and a fresh `ModelWeb` reload agrees.
- RAM is identical. The `EdgeAppliance` component is identical: 200, card re-rendered, component still listed.

**User reachability.** The Factory sensor panel embeds 26 calculated-attribute links owned by `Factory-sensor-CPU`/`-RAM`, because `EdgeComputerWeb.calculated_attributes_values` prepends the components' values (`e-footprint-interface/model_builder/domain/entities/web_builders/hardware/edge/edge_computer_web.py:19-22`). Each chart header links to `open-edit-object-panel/<component id>` (`e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/calculated_attribute_chart.html:7-13`). That panel renders the Delete button (`…/side_panels/edit/edit_panel__generic.html:4-17`), and it opens today because of the override. Appliances are reachable the same way (`e-footprint-interface/model_builder/domain/entities/web_builders/hardware/edge/edge_appliance_web.py:11-16`).

### Deletion sweep across the shipped examples

`scratchpad/silentdel/test_sweep.py` runs this loop for each of the 75 objects in `ai_chatbot`, `genai_video` and `iot_industrial` (excluding Sources and System), plus two synthetic cases: fresh session, then `ask-delete`, then `delete-object` when it is offered, then a re-read of the session. Results: 37 DELETED, 22 BLOCKED (correct "referenced by" modal), 12 `ask-delete` KeyErrors (exactly Task 6's set: EcoLogits servers, `Sensor-local-storage`, recurrent process component needs), and 6 SILENT_NOOP:

- `iot_industrial` `Factory-sensor-CPU` and `Factory-sensor-RAM`, plus the synthetic `EdgeApplianceComponent`: this bug.
- `Device/Default-laptop` in all three examples. This is a different and latent case. The list branch does edit `UsagePattern.devices` to `[]`, leaving a pattern with no device. It then leaves the `Device` behind as an orphan, because `UsagePatternWebBaseClass.accordion_children` is `[]` (`usage_pattern_web_base_class.py:57-60`) and the cascade cleanup therefore never deletes it. It is **not reachable from the UI**: `Device` has no web mapping, so its edit panel raises `KeyError 'Device'` (`efootprint_to_web_mapping.py:111`). The calculated-attribute ancestor list also deliberately skips Device containers (`…/calculated_attributes/components/ancestor_or_child_list_element.html:4`). Only a hand-crafted POST reaches it. It is out of scope and recorded under Flags.

Control: a component added to a custom `EdgeDevice` (synthetic `EdgeCPUComponent`) is offered for deletion and is actually deleted.

## Reproduction

- `e-footprint-interface/tests/unit_tests/adapters/views/test_views_deletion.py::test_library_built_edge_component_deletion_is_blocked_and_edits_rerender_its_device` — view (Django client and session, `RAISE_EXCEPTIONS` unset, programmatic `edge_system_data` fixture extended with an `EdgeAppliance` under a `RecurrentEdgeWorkload`); fails on `dev@6a1c10ea`. It is parametrized over `EdgeComputerCPUComponent`, `EdgeComputerRAMComponent`, `EdgeStorage` (owner: "Shared edge computer") and `EdgeApplianceComponent` (owner: "Edge appliance"). Each case asserts three things in order:
  1. `ask-delete-object` shows "is referenced by" with the device's name and no "Yes, delete".
  2. A direct `delete-object` POST is not a 200, and the component is still saved, in the device's `components` too.
  3. Renaming the component through `edit-object` returns 200 with an out-of-band swap of the device card.

  The third assertion holds today for CPU, RAM and the appliance component, through the overrides. It guards the placement that the fix moves into `EdgeComponentWeb.mirrored_cards`.
- Failures recorded with `--runxfail`:
  - CPU, RAM and appliance component, at `test_views_deletion.py:111`: `assert 'is referenced by' in '…<p id="exception-msg" class="modal-message">Are you sure you want to delete this EdgeComputerCPUComponent ?</p>… Yes, delete …'`. RAM and the appliance component fail the same way, with their own class names.
  - `EdgeStorage`, at HEAD, raises from the `ask-delete-object` call at `:110`. This is Task 6's failure, not this task's:
    ```
    e-footprint-interface/model_builder/adapters/views/views_deletion.py:22 ask_delete_object
    e-footprint-interface/model_builder/application/use_cases/delete_object.py:89 check_can_delete
    e-footprint-interface/model_builder/application/use_cases/delete_object.py:69 _container_removal_targets
    e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:390 list_containers_and_attr_name_in_list_container
    KeyError: 'components'
    ```
  - `EdgeStorage` with Task 6's part 1 applied: assertions 1 and 2 pass, and the case then fails for this task's reason at `:123`: `assert "hx-swap-oob='outerHTML:#sys-…-EdgeComputer-…'" in '<div hx-swap-oob=\'outerHTML:#sys-…-EdgeStorage-…\'>…'`. The edit swaps a storage card that is not on the canvas, and the edge computer card is not refreshed. This layering is why the storage case belongs here: Task 6 makes it reachable, and Task 8 places it.
  - The masked assertion 1 stops the run before the POST. A scratch observation of the same POST on the same fixture (below) gives, for all three classes: `status=200`, no modal, the component id still in the device's `components`, and the device card swapped. That is the silent no-op.
- Watch (values from the recorded run; the three classes differ only in names):
  - `[c.name for c in containers], attr_name` returned at `e-footprint-interface/model_builder/domain/entities/web_builders/hardware/edge/edge_computer_cpu_component.py:8` (RAM `edge_computer_ram_component.py:8`, appliance `edge_appliance_component.py:10`) → `(['Shared edge computer'], 'components')`; for the appliance `(['Edge appliance'], 'components')`.
  - `list_or_dict_containers` at `e-footprint-interface/model_builder/application/use_cases/delete_object.py:106` → `['Shared edge computer']`, so the direct-reference block is skipped. `check_can_delete` returns `can_delete=True, is_list_or_dict_deletion=True` at `:140-141`.
  - `edit_data` at `e-footprint-interface/model_builder/application/use_cases/delete_object.py:205` → `{'name': 'Shared edge computer', 'components': [<RAM id>, <storage id>]}` for the CPU; for the appliance `{'name': 'Edge appliance', 'components': []}`.
  - `attr_name not in init_sig_params` at `e-footprint-interface/model_builder/domain/object_factory.py:180`, for `components` on `EdgeComputer` or `EdgeAppliance` → `True`, so the key is skipped. `prepare_input_changes` returns `0` changes, and `proposed` is empty at `:352`.
  - `deletion.status_code`, plus the component id in `saved_after['EdgeComputer'][device_id]['components']`, after the POST at `e-footprint-interface/tests/unit_tests/adapters/views/test_views_deletion.py:115` → `200`, `True` (scratch observation).
- Debug recipe: run `poetry run pytest --runxfail "tests/unit_tests/adapters/views/test_views_deletion.py::test_library_built_edge_component_deletion_is_blocked_and_edits_rerender_its_device"` and break on `test_views_deletion.py:111`, right after the `ask-delete-object` call. To step through the silent POST, break at `delete_object.py:205` and `object_factory.py:180` and evaluate the POST from the debugger, because assertion 1 stops the test first.
- Discrimination: I ran Tasks 6 and 8 as scratch pytest plugins with `--runxfail`, without committing them:
  - Tasks 6 + 8: 4 passed. Tasks 4 + 6 + 8 also pass.
  - Task 6 alone: all 4 fail. CPU, RAM and the appliance component still get "Yes, delete"; `EdgeStorage` swaps the wrong card.
  - Task 8 alone: all 4 fail with `KeyError: 'components'` from `ask-delete-object`, which confirms the hard dependency.
  - Task 6 plus deleting the three overrides without the placement override (rejected alternative): all 4 fail. CPU, RAM and the appliance component fail with `assert 500 == 200` at `:122` on the edit; `EdgeStorage` swaps the wrong card.

  The plugins are `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/a41b7a33-6432-494e-94e6-03d14dee464c/scratchpad/task6/task6_plugin.py` (`TASK6_PATCH=part1`) and `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/a41b7a33-6432-494e-94e6-03d14dee464c/scratchpad/task8/task8_plugin.py` (`TASK8_PATCH=1|removal`, `TASK8_WATCH=1`); the observation test is `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/a41b7a33-6432-494e-94e6-03d14dee464c/scratchpad/task8/test_task8_observe.py`.
- Line numbers cited in Root cause were re-checked against `6a1c10ea`; none drifted.

## Fix approach

The fix lands on top of Task 6's `.get(attr_name)` skip in the base property. It separates the overrides' rendering role from the removal role they claim by accident:

1. **Place edge components under their device's cards in one place.** Add a `mirrored_cards` override to `EdgeComponentWeb` (`e-footprint-interface/model_builder/domain/entities/web_core/hardware/edge/edge_component_base_web.py:9`). It returns one `type(self)(self._modeling_obj, self.model_web, list_container=parent)` per `parent in self.edge_device.mirrored_cards`. `edge_device` is the library's own owner link (`e-footprint/efootprint/core/hardware/edge/edge_component.py:67`).
2. **Make `EdgeComputerCPUComponentWeb`, `EdgeComputerRAMComponentWeb` and `EdgeApplianceComponentWeb` subclass `EdgeComponentWeb`**, as their library classes do. Delete their `list_containers_and_attr_name_in_list_container` overrides and keep their `calculated_attributes_without_validations` filters.

The behavior follows from those two changes:
- With Task 6, the base property drops `components`, since it is not a constructor input. The use case then has no list target. It falls through to the default direct-reference block (`delete_object.py:105-118`), which is the library's `PermissionError` rule.
- In the probe:
  - CPU: "This EdgeComputerCPUComponent is referenced by Factory sensor, Measure temperature and vibration CPU need, Keep recent readings on the sensor CPU need. To delete it, first delete or reorient these edge computers."
  - RAM: the same message.
  - Appliance component: "… referenced by Test appliance … edge appliances."
- Panels still open with a Delete button.
- CPU, RAM and appliance-component renames still re-render the device card.
- Deleting an unreferenced `EdgeComputer` or `EdgeAppliance` still cascades to its components.
- For a custom `EdgeDevice` component, `mirrored_cards` web ids are identical to the current ones, and deletion still works.
- **It also closes a gap that Task 6 opens.** With Task 6 alone, an `EdgeStorage` edit from its newly openable panel saves the change. It then swaps `#sys-…-EdgeStorage-Sensor-local-storage`, which is not on the canvas, and the edge computer card is not refreshed. With step 1, the same edit re-renders `#sys-…-EdgeComputer-Factory-sensor` (probe `test_storage_placement.py`). This answers Task 6's "smoke check (not covered by the diagnosis)".

Rejected alternatives:
- **Delete the three overrides only.** Deletion becomes correctly blocked, but every CPU/RAM/appliance-component edit becomes a 500. The overrides are the only thing placing these components under their device's card.
- **Keep the overrides; filter non-constructor list targets in `_container_removal_targets`** (option (a); the probe also gave the blocking modal). This leaves a domain property that claims a list membership the library doesn't have, read differently by its two consumers. It moves the library-signature knowledge into the use case and does not fix the `EdgeStorage` edit placement.
- **Override `mirrored_cards` in each of the three classes (no `EdgeComponentWeb` change).** It works for the three classes (probe option `e`), but it duplicates the same three lines three times and leaves `EdgeStorage` mis-placed after Task 6.
- **Hide the Delete button for library-built objects.** There is no structural library marker for "internal" objects, only docstrings. A hidden button still leaves direct POSTs a silent no-op. It is also inconsistent with the blocking modal already settled for Task 6's objects. See Decisions for the fork.
- **Make the list branch raise when the container attribute is not a constructor input.** This is defensible under constitution §3.1, but no remaining code path produces such a target once the overrides go. It adds a guard for a state the fix removes.

## Files to touch

- `e-footprint-interface/model_builder/domain/entities/web_core/hardware/edge/edge_component_base_web.py`: add the `mirrored_cards` override (parent-card placement through `edge_device`) and a one-line docstring explaining why.
- `e-footprint-interface/model_builder/domain/entities/web_builders/hardware/edge/edge_computer_cpu_component.py`, `edge_computer_ram_component.py`, `edge_appliance_component.py`: base class `EdgeComponentWeb`; delete the `list_containers_and_attr_name_in_list_container` overrides (`:5-8`, `:5-8`, `:7-10`); drop the unused `typing` import in the appliance file.
- `e-footprint-interface/specs/architecture/forms-and-relationships.html` (or `layers-and-wrappers.html`, wherever `mirrored_cards`/list containers are described): one line. Library-built relationships are never removal targets, and edge components are placed under their device's cards through `EdgeComponentWeb.mirrored_cards`.
- `e-footprint-interface/CHANGELOG.md`: `## [Unreleased]` fix entry.
- `e-footprint-interface/tests/unit_tests/adapters/views/test_views_deletion.py`: remove the reproduction's `xfail` marker.
- `e-footprint-interface/tests/unit_tests/domain/entities/web_builders/hardware/edge/test_edge_computer_cpu_component_web.py`, `test_edge_computer_ram_component_web.py`, `test_edge_appliance_component_web.py`: delete the override tests (see Tests).

## Tests

- The reproduction is this task's only test: `tests/unit_tests/adapters/views/test_views_deletion.py::test_library_built_edge_component_deletion_is_blocked_and_edits_rerender_its_device`. Remove its expected-failure marker.
  - It covers deletion blocking, direct-POST refusal and device-card placement at the view boundary, for CPU, RAM, edge storage and the appliance component. Task 6's reproduction listed edge-storage edit placement as a smoke check; this test now carries it.
  - No placement unit test, separate edit-view test or `check_can_delete` use-case case is needed. `check_can_delete` is exercised through `ask-delete-object`, and placement through `edit-object`. No other existing test covers a component edit re-rendering the device card; the reproduction's third assertion is that coverage.
- Required existing-test edits: delete `test_list_containers_and_attr_name_in_list_container` from `tests/unit_tests/domain/entities/web_builders/hardware/edge/test_edge_computer_cpu_component_web.py:13`, `test_edge_computer_ram_component_web.py:13` and `test_edge_appliance_component_web.py:11`. They test the overrides that the fix deletes. Keep their `test_calculated_attributes_filters_known_fields` tests.
- Must keep passing: `tests/integration/test_deletion.py::test_delete_edge_computer_cascades_to_components` and `::test_delete_edge_appliance_cascades_to_component`, and the custom-edge-device component flow `tests/e2e/objects/test_edge_objects.py::TestEdgeObjects::test_edge_device_with_cpu_ram_components_and_component_needs` (`:334`).
- No E2E test is needed: the behavior is server-rendered, and the view test covers it.

## Acceptance criteria

- On the Industrial IoT example, opening the edge computer's CPU or RAM panel from a calculated-attribute link and clicking Delete shows the blocking modal naming the edge computer. The model is unchanged. The same holds for an edge appliance's component.
- Renaming a CPU, RAM or appliance component, or (with Task 6) an edge storage, from its own panel re-renders the owning device card, with no error modal.
- Deleting an edge computer or appliance still deletes its components. Components of custom edge devices are still deletable and render exactly as before.

## Risks and side effects

- `EdgeComponentWeb.mirrored_cards` now applies to every edge component, custom-device ones included. The probe showed identical web ids for a custom `EdgeDevice` component. If an `EdgeComponent` can exist with `edge_device is None`, the override would raise. None was found in the shipped examples or flows, because list removal of a custom device's component cascades its deletion as an orphaned accordion child. The implementer should confirm this rather than add a speculative guard.
- The three classes inherit `EdgeComponentWeb`'s creation-only members (`form_creation_config`, `get_htmx_form_config`, `create_side_effects`) and `template_name = "edge_component"`. The creation members are unused, since internal components are never created from a form. `template_name` is read only for the creation render (`htmx_presenter.py:144-150`) and for a `top_parent` render, which is the device here.
- The blocking-modal copy shows the raw class name and lists the recurrent needs beside the device. It also says "reorient", which is impossible for an internal component. This is the same copy Task 6 accepts for `EdgeStorage`. Polishing it is a separate copy change.

## Flags

- **Ordering:** **depends on Task 6** (hard). Without Task 6's `.get` skip, removing the overrides makes the CPU, RAM and appliance-component panels raise `KeyError 'components'`, as `EdgeStorage` does today. Task 4 is a transitive dependency through Task 6, with no shared lines. The cleanest option is one implementer for Task 6 and this task, since this also delivers Task 6's `EdgeStorage` edit smoke check. **Task 3:** no shared product file; shares `test_views_deletion.py` and `CHANGELOG.md`.
- **Constitution §1.3:** respected. Removal semantics come from the library: these are not constructor inputs, they are internal by construction, and `self_delete` raises while containers exist. Placement uses the library's `edge_device` owner link. **§3.1:** the silent no-op goes away because the false removal target is removed at its source, not filtered downstream. **§2.6:** changelog entry needed.
- **Cross-repository:** none. Library semantics were read in the local `e-footprint` 27.0.0 checkout that the interface venv resolves.
- **Migration and serialization:** none.
- **Local-only validation:** none needed. All evidence comes from the Django test client. Scratch harnesses (not committed): `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/silentdel/` (`test_silent_repro.py`, `test_fix_probe.py`, `test_fix_options.py`, `test_storage_placement.py`, `test_unified.py`, `test_sweep.py`, `sweep_out.txt`).
- **Unrelated, latent (not user-reachable), out of scope:** a POST to `delete-object/Default-laptop/` empties `UsagePattern.devices` and leaves an orphan `Device`. The cause is the list branch's reliance on accordion-child cascade cleanup (`delete_object.py:180-219`, `edit_service.py:64-69`). It is unreachable because `Device` has no web mapping and no panel. It is a candidate for the backlog only if Device editing is ever exposed.

## Decisions

- 2026-10-21 (supervisor default, consistent with Task 6's settled behavior): internal components show the "referenced by &lt;owner&gt;" blocking modal. The Delete button is not hidden. The existing blocking copy is accepted as-is, as it is for Task 6: it shows the raw class name, lists the recurrent needs and says "reorient". Tracked as Task 8 in `tasks.md`.
