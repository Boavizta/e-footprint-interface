# Library-built objects cannot open their edit panel or be checked for deletion: list-container detection indexes the container's constructor signature with a non-constructor attribute

- **Status:** CONFIRMED
- **Confidence:** high. Reproduced through the real Django views on all three shipped introductory examples. The panel crash is reached from links the UI renders. A monkeypatched fix makes every affected edit panel render with its delete button, and `ask-delete` returns a clean "referenced by …" blocking modal.
- **Reported:** found by the #151 diagnostician during a deletion sweep, not reported by a user: "Calling `DeleteObjectUseCase.check_can_delete` directly raised `KeyError` for EcoLogits external API servers, `EdgeStorage` and recurrent edge process component needs. The cause is `get_init_signature_params(container.efootprint_class)[attr_name]` at `modeling_object_web.py:390` meeting a non-constructor relationship attribute. It is unclear whether the UI exposes delete for these objects." **Hypothesis held.** The reachability question has a sharper answer: the delete button is never reached before the fix, because the same lookup crashes these objects' edit panel first (through `mirrored_cards`). The panel is reachable from links in calculated-attribute explanations, so the user-visible symptom is an error modal when one of those links is clicked. Once that is fixed, the delete button appears and reaches `check_can_delete`, which hits the same line. For EcoLogits servers, a second, independent `KeyError` also blocks the panel (see Root cause, part 2).

## Root cause

### Part 1: the `:390` lookup (EdgeStorage and component needs; also the EcoLogits server's delete check)

`ModelingObjectWeb.list_containers_and_attr_name_in_list_container` (`e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:383-395`) asks one question of each contextual container entry: is this object held in a **list-typed constructor input** of its container? It reads the container's `__init__` signature and indexes it directly with the entry's attribute name (`:389-390`):

```python
container_signature = get_init_signature_params(container.efootprint_class)
annotation = container_signature[attr_name].annotation
```

The library also creates relationship attributes that are **not constructor parameters**. A builder subclass drops a parent constructor input and fills it in `after_init`:

| Container (library) | Attribute | Constructor | Created in | Affected child |
|---|---|---|---|---|
| `EcoLogitsGenAIExternalAPI` / `EcoLogitsVideoGenExternalAPI` | `server` | `__init__(name, …)`; `self.server = None` (`e-footprint/efootprint/builders/external_apis/external_api_base_class.py:75-77`) | `after_init` (`:80-82`) | `EcoLogits*ExternalAPIServer` |
| `EdgeComputer` | `components` | `__init__(…, storage)`, no `components` (`e-footprint/efootprint/builders/hardware/edge/edge_computer.py:148-154`) | `after_init` (`:186-191`) `[cpu, ram, self.storage]` | `EdgeStorage` (also holds `storage`, a constructor input) |
| `RecurrentEdgeProcess` | `recurrent_edge_component_needs` | `__init__(name, edge_device, recurrent_*_needed)`, passing `[]` to the parent (`e-footprint/efootprint/builders/usage/edge/recurrent_edge_process.py:122-129`) | `after_init` (`:137-146`) | `RecurrentEdgeProcessCPUNeed`/`RAMNeed`/`StorageNeed` |
| `RecurrentEdgeWorkload` | `recurrent_edge_component_needs` | passes `[]` to the parent (`e-footprint/efootprint/builders/usage/edge/recurrent_edge_workload.py:55-56`) | `after_init` (`:59-63`) | `RecurrentEdgeWorkloadNeed` (code reading only; not in a shipped example) |
| `EdgeAppliance` | `components` | — | `after_init` (`e-footprint/efootprint/builders/hardware/edge/edge_appliance.py:87-90`) | `EdgeApplianceComponent`: **masked** by an interface override |

The parent classes declare these same attributes as constructor inputs (`e-footprint/efootprint/core/hardware/edge/edge_device.py:59-66`, `e-footprint/efootprint/core/usage/edge/recurrent_edge_device_need.py:26-30`). That is why the generic `EdgeDevice`/`RecurrentEdgeDeviceNeed` cases work.

The interface already works around this for `EdgeComputerCPUComponent`, `EdgeComputerRAMComponent` and `EdgeApplianceComponent`. Each overrides the property to return `[edge_device], "components"` (`e-footprint-interface/model_builder/domain/entities/web_builders/hardware/edge/edge_computer_cpu_component.py:5-8`, `edge_computer_ram_component.py:5-8`, `edge_appliance_component.py:7-10`). `EdgeStorage` maps to the generic `EdgeComponentWeb` (`e-footprint-interface/model_builder/domain/efootprint_to_web_mapping.py:70`). The process and workload component needs fall back to `ModelingObjectWeb`, since they are not mapped (`efootprint_to_web_mapping.py:86-89`). So the generic `:390` lookup applies to them, and `container_signature["components"]` (or `["server"]`, `["recurrent_edge_component_needs"]`) raises `KeyError`.

**The library's own idiom.** The library answers "is this attribute a structural input?" with `get_init_signature_params(cls).get(name)` and treats `None` as "not an input":
- `check_input_value` returns early (`e-footprint/efootprint/abstract_modeling_classes/modeling_object.py:423-425`);
- `is_structural_input_dict_attribute` returns `False` (`:491-493`);
- `explainable_object_dict_class_from_init_annotation` falls back (`e-footprint/efootprint/api_utils/json_to_system.py:23`).

The interface's sibling readers iterate the signature itself (`list_attr_names`, `dict_attr_names`, `modeling_object_attr_names`, `child_attr_names_to_child_types_str` at `modeling_object_web.py:460-519`). They therefore never index it with a foreign name and are safe. `:390` is the only place that indexes the signature with an attribute name that comes from outside it.

**Callers that crash** (`mirrored_cards` calls the property at `modeling_object_web.py:415`):
- `open_edit_object_panel`. The `highlightOpenedObjects` trigger computes `obj_to_edit.mirrored_cards` (`e-footprint-interface/model_builder/adapters/views/views_edition.py:44`). The view is wrapped in `@render_exception_modal_if_error` (`:20`), so the user sees an error modal, not the panel. Traceback: `views_edition.py:44` → `modeling_object_web.py:415` → `:390`.
- `ask_delete_object`, through `check_can_delete` → `_container_removal_targets` (`e-footprint-interface/model_builder/application/use_cases/delete_object.py:89` → `:69` → `modeling_object_web.py:390`). This view has **no** exception decorator (`e-footprint-interface/model_builder/adapters/views/views_deletion.py:14-22`), so the result is a raw 500.
- `delete_object`, through `execute` → `_delete` (`delete_object.py:178` → `:69`). The view is decorated, so it shows an error modal.
- Edit paths that call `mirrored_cards` (`e-footprint-interface/model_builder/domain/services/edit_service.py:46`, `:54`; `e-footprint-interface/model_builder/application/use_cases/edit_object.py:117`). These are reachable only after the panel opens, so they cannot be reached today.

Canvas rendering is **not** affected. These objects are never rendered as cards, and the `links_to` targets that reach them have overrides (CPU and RAM) or are not rendered. All three examples load, and the sweep found no `mirrored_cards` failure outside the objects listed.

**User reachability (verified through the real views).** The edit panels of reachable objects render "(see graph)" links for calculated attributes. The chart header and the ancestor/child lists link to `open-edit-object-panel/<container id>` for every container except System/Device/Network/Country (`e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/calculated_attributes/calculated_attribute_chart.html:7-13`, `…/components/ancestor_or_child_list_element.html:4-13`). Scanned results:
- **EcoLogits servers:** the ExternalAPI panel shows the server's calculated attributes (`e-footprint-interface/model_builder/domain/entities/web_builders/services/external_api_web.py:25-26`). Their charts link to `Small-LLM-API-server`, `Seedance-video-generation-API-server`, and so on.
- **`Sensor-local-storage`:** linked from charts reached from the `Factory-sensor` panel, for example `Factory-sensor/instances_manufacturing_footprint_per_usage_pattern/…`.
- **`Measure-temperature-and-vibration-CPU-need` and `-storage-need`:** linked from the `Factory-sensor-CPU/unitary_hourly_compute_need_per_usage_pattern/…` and `Sensor-local-storage/cumulative_unitary_storage_need_per_usage_pattern/…` charts.

Clicking any of these links returns 500 with the error modal. The delete button (`e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/edit_panel__generic.html:4-10`) lives in that panel, so it is never shown. `ask-delete`/`delete-object` are reachable only by direct URL.

### Part 2: EcoLogits server panels also fail on a missing canonical web mapping

With part 1 patched, the EcoLogits server panel still returns 500. Form building calls `get_corresponding_web_class(EcoLogitsGenAIExternalAPIServer)` (`e-footprint-interface/model_builder/adapters/forms/form_field_generator.py:238`). That function resolves the canonical class `ExternalAPIServer` (`e-footprint/efootprint/all_classes_in_order.py:80`), then indexes the mapping, which has no `ExternalAPIServer` key (`e-footprint-interface/model_builder/domain/efootprint_to_web_mapping.py:111`; the mapping is at `:38-82`). The result is `KeyError: 'ExternalAPIServer'` (traceback `views_edition.py:27` → `form_context_builder.py:143` → `simple.py:110` → `form_field_generator.py:238` → `efootprint_to_web_mapping.py:111`). `wrap_efootprint_object` already falls back to `ModelingObjectWeb` for the concrete server class (`efootprint_to_web_mapping.py:84-89`), so the two lookups disagree. Adding `"ExternalAPIServer": ModelingObjectWeb` makes the panel render (200, delete button present).

### Interaction with Task 4 (#151)

Task 4 adds a filter in `efootprint_contextual_modeling_obj_containers` (`modeling_object_web.py:378-380`) that drops detached entries (`modeling_obj_container is None`). This fix edits the loop directly below it (`:389-390`). The two changes are independent in behavior: Task 4 removes `None` containers, and this fix skips non-constructor attribute names. They touch adjacent lines of one property, so they should land in sequence (Task 4 first, then this one, or both by one implementer). After Task 4, this fix needs no `None` guard.

## Fix approach

1. **`:389-390`:** look the parameter up with `.get(attr_name)` and `continue` when it is `None`. This follows the library's own "not in the init signature means not a structural input" rule (`modeling_object.py:423-425`, `:491-493`). A library-built relationship is not a user-editable list membership. It must not become a list-removal target either: removing the object would mean editing a non-constructor attribute. Two outcomes follow:
   - The `EdgeStorage` of an `EdgeComputer` is still seen through its constructor input `storage`. It becomes a direct-reference child and is blocked by the default rule (`delete_object.py:105-117`).
   - Process/workload component needs and EcoLogits servers have no constructor container. They are blocked by their owner.

   Verified by monkeypatch:
   - `Sensor-local-storage`: "referenced by Factory sensor, … storage need … To delete it, first delete or reorient these edge computers".
   - `…-CPU-need` and `…-storage-need`: "referenced by Measure temperature and vibration".
   - EcoLogits servers: "referenced by Small LLM API" / "Seedance video generation API".
   - Each panel opens with its delete button.
2. **`efootprint_to_web_mapping.py`:** add `"ExternalAPIServer": ModelingObjectWeb`, next to the other external API entries (`:52-54`). EcoLogits server panels then open, and `get_corresponding_web_class` agrees with `wrap_efootprint_object`.

Rejected alternatives:
- **Use the library's `contextual_container.list_container`** (`e-footprint/efootprint/abstract_modeling_classes/object_linked_to_modeling_obj.py:160-170`) instead of the annotation. It reports *any* list-valued attribute, derived ones included. That would make `EdgeComputer.components` and `RecurrentEdgeProcess.recurrent_edge_component_needs` removal targets for list deletion of library-built children, which is the wrong semantics.
- **Add more per-class overrides** (an `EdgeStorage` web class, or a `RecurrentEdgeProcess*Need` web class, like the CPU/RAM ones): this handles one symptom per class, and the next builder that drops a parent input regresses again. The overrides also declare the non-constructor list removable, which causes the latent no-op described in Flags.
- **Hide links to library-built objects in calculated-attribute templates**: this loses navigation to the objects' calculated attributes, which are informative, and still leaves `check_can_delete` crashing on direct calls.
- **Library API change** (expose the "structural input relationships" of a class): not needed. `get_init_signature_params(...).get()` already is the library's contract for this question, and adding an API would create cross-repo ordering for no gain.

## Files to touch

- `e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py`: in `list_containers_and_attr_name_in_list_container` (`:389-390`), replace `container_signature[attr_name]` with `.get(attr_name)` and skip `None`. Rebase onto Task 4's `:378-380` filter.
- `e-footprint-interface/model_builder/domain/efootprint_to_web_mapping.py`: add `"ExternalAPIServer": ModelingObjectWeb` near `:52-54`.
- `e-footprint-interface/tests/unit_tests/domain/entities/web_abstract_modeling_classes/test_modeling_object_web.py`: extend the list-container test (`:308-334`).
- `e-footprint-interface/tests/unit_tests/application/use_cases/test_delete_object.py`: add `check_can_delete` cases in the `# --- check_can_delete ---` section (`:16`).
- `e-footprint-interface/tests/unit_tests/adapters/views/test_views_edition.py`: add the view regression.
- `e-footprint-interface/CHANGELOG.md`: add a `## [Unreleased]` fix entry.

## Tests

- **Domain unit** (`test_modeling_object_web.py`): add a stub contextual entry whose container class signature lacks `attr_name`. It must be ignored, while a sibling entry on a list-typed constructor input is still returned with its attribute name.
- **Use case** (`test_delete_object.py`, real examples loaded into a `ModelWeb`):
  - `check_can_delete` on `iot_industrial.json` `Sensor-local-storage` returns `can_delete=False`, with `Factory sensor` among the blocking containers;
  - on `Measure-temperature-and-vibration-CPU-need`, it returns `can_delete=False` and lists `Measure temperature and vibration`;
  - on `ai_chatbot.json` `Small-LLM-API-server`, it returns `can_delete=False` and lists `Small LLM API`.

  All three raise `KeyError` before the fix.
- **View regression** (`test_views_edition.py`, Django client plus session, parametrized over the three example/object pairs above plus `genai_video.json` `Seedance-video-generation-API-server`): `GET /model_builder/open-edit-object-panel/<id>/` returns 200 and contains `btn-ask-delete`. Run it with `RAISE_EXCEPTIONS` unset and assert no exception modal. Optionally chain `GET /model_builder/ask-delete-object/<id>/` and assert 200 with the "referenced by" text. Before the fix, the panel returns 500 (`KeyError 'components'`, `'recurrent_edge_component_needs'`, or `'ExternalAPIServer'`).
- **E2E is not required**: the behavior is server-rendered and the view test covers it.

## Acceptance criteria

- On the Industrial IoT, AI chatbot and GenAI video examples, clicking a calculated-attribute link to an EdgeStorage, a recurrent edge process component need, or an EcoLogits API server opens that object's edit panel, with no error modal.
- Clicking Delete in those panels shows the "referenced by …" blocking modal that names the owning object (edge computer, recurrent edge process or external API), and the model is unchanged.
- Deleting or editing jobs, needs, edge devices, CPU/RAM components and usage patterns behaves as before.

## Risks and side effects

- Library-built objects become openable and editable from their own panel (EdgeStorage, process component needs, EcoLogits servers). The edit-submit path through `edit_service.py:46`/`:54` should work once `mirrored_cards` stops raising, but submitting an edit from these panels was **not** exercised. The task implementer should run one edit (for example EdgeStorage capacity) through `edit-object` as a smoke check.
- EdgeStorage edited from its own panel, and as a nested input of the EdgeComputer form (`e-footprint-interface/model_builder/domain/entities/web_builders/hardware/edge/edge_computer_web.py:12`, `:38-47`), are two edit entry points for one object. This is consistent with CPU/RAM components, which already have their own panels.
- `ask_delete_object` has no `@render_exception_modal_if_error` (`views_deletion.py:14`), unlike its siblings. Any future failure there is a raw 500 rather than a modal. Adding the decorator is optional hardening and not required by this fix.

## Flags

- **Constitution §1.3:** respected. The interface stops guessing and applies the library's own "non-constructor attribute is not a structural input" rule. No modeling logic is added.
- **§2.6:** a changelog entry is needed.
- **Cross-repository:** none. The library semantics were read in the local `e-footprint` 27.0.0 checkout, which the interface venv resolves.
- **Migration and serialization:** none.
- **Ordering:** depends on Task 4 (#151), since both edit `modeling_object_web.py:378-395`. Land it after Task 4, or have one implementer do both.
- **Local-only validation:** none needed. All evidence comes from the Django test client against the shipped examples. Scratch harness (not committed): `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/keyerr/`.
- **Unrelated observations (not diagnosed, out of scope; candidates for separate reports):**
  1. *Edge computer CPU/RAM (and likely appliance) component deletion is a silent no-op.* The overrides at `edge_computer_cpu_component.py:5-8` etc. declare the non-constructor `components` list a removal target. `ask-delete` on `Factory-sensor-CPU` offers "Yes, delete", and `delete-object` returns 200 and re-renders the Factory sensor card. The saved model still contains the CPU component with `components` unchanged. The expected behavior is probably the same blocking modal this fix gives EdgeStorage.
  2. *Hourly chart crash on empty timeseries.* `get_explainable_hourly_quantity_chart_and_explanation` for `Sensor-local-storage/unitary_power_per_usage_pattern/Factory-sensors-starting-up` (also `energy_per_…` and `use_footprint_per_edge_device_per_usage_pattern`) raises `AttributeError: 'EmptyExplainableObject' object has no attribute 'plot_aggregation_strategy'` at `e-footprint-interface/model_builder/domain/entities/web_core/explainable_timeseries_utils.py:86`. The view is undecorated (`e-footprint-interface/model_builder/adapters/views/views.py:569-570`), so it is a raw 500. The links come from "(see graph)" in the Factory-sensor panel.

## Decisions

- 2026-10-21 (supervisor default, same user path): include part 2, the `"ExternalAPIServer": ModelingObjectWeb` mapping entry, in this task alongside the `:389-390` fix. Splitting it out would leave EcoLogits server links showing an error after part 1 ships.
