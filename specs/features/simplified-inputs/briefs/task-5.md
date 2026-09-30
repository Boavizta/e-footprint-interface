# Task 5 — Apply one atomic selected-input edit

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [atomic edit](../plan.html#atomic-edit). Task: [overview](../tasks.md#task-5). Status: approved.
Implementation: hard — the plan fixes one batch and request-local persistence, Tasks 2–3 supply sibling validation and field links, and the existing factory/`ModelingUpdate` supply conversion and rollback. The implementer must derive chained, cross-owner candidate values and coordinate direct metadata changes before that batch; this is demanding because conditional validation reads the applied graph while the current converter invokes `ModelingUpdate` per owner.

## Start here

- [`edit_object_from_parsed_data()` and `_apply_metadata()`](../../../../model_builder/domain/object_factory.py): existing conversion, metadata and `ModelingUpdate` call; [`EditObjectUseCase.execute()`](../../../../model_builder/application/use_cases/edit_object.py): current one-owner flow.
- Library [`ModelingUpdate`](../../../../../e-footprint/efootprint/abstract_modeling_classes/modeling_update.py): validates one multi-owner batch and rolls back on error; [`ModelWeb.persist_to_cache()`](../../../../model_builder/domain/entities/web_core/model_web.py): accepted persistence boundary.
- [`parse_form_data()`](../../../../model_builder/adapters/forms/form_data_parser.py): normalized value/provenance shape; `tests/fixtures/system_builders.py`: real model fixtures.

## Change along the code path

Extract `prepare_input_changes()` from the normal edit function, preserving its conversion and source/metadata semantics. Add `EditSimplifiedInputUseCase` to resolve the addressed owner, prepare the submitted value and recursively reconcile conditional dependents against candidate controlling values. Retain valid dependent values; for invalid values use the first allowed choice, report it; if no allowed choice exists, reject the whole edit. Collect every changed value pair across owners and call one library `ModelingUpdate`, then persist the request-local `ModelWeb` once on success. Return affected addresses/notices for later targeted rendering.

## Earlier tasks

Task 2 corrects library sibling-dependent validation; Task 3 provides field addresses and catalog links. Task 9 will expose this use case through HTTP and browser controls. This task can be checked without a page.

## Reuse

Use current library conditional metadata, `ModelingUpdate` and existing `_apply_metadata()`; no second validator or deferred-metadata store. `ModelWeb` rebuilds per request, so failed request-local metadata does not become stored state. Keep the normal edit function as a caller of the extracted helper.

The current `edit_object_from_parsed_data()` builds one owner's changes and invokes `ModelingUpdate` internally; it directly mutates metadata for same-value edits because `ModelingUpdate` skips equal values. Library `ModelingUpdate` applies the whole batch before checking conditional values against the live graph and rolls back values on validation failure. The new preparation step must therefore derive candidate dependent values before that call and leave metadata unpublished on rejection.

## Invariants and traps

Do not persist a controller before its dependents. An absent conditional branch adds no restriction; an explicitly empty allowed list rejects. Omitted provenance properties stay unchanged. Same-value metadata edits must still save; unchanged values must not trigger unrelated updates. Structural relationship edits remain outside this use case. Check the nested owner address rather than the surrounding Server panel ID.

## Validation

Run `poetry run pytest tests/integration/test_simplified_inputs.py` and affected normal edit tests under `tests/integration/` in the interface against the Task 2 library checkout. Test a controller with valid and invalid dependents, first-choice notice, rejection with zero persisted value/metadata changes, a Server empty-count case, nested owner resolution and normal edit regression. Final full suites run in Task 10.

## Out of scope

No autosave JS, field rendering, timeseries panel or definition editing.

## Verified conditional ordering

`EcoLogitsVideoGenExternalAPI.generate_conditional_list_values()` builds each Provider's Model list in `_MODELS_INFO` iteration order; `EcoLogitsVideoGenExternalAPIJob.generate_conditional_list_values()` builds each Model's Resolution list from its catalog `capabilities.resolutions` order. First-allowed fallback must use the first item of the applicable metadata list, including for a dotted `external_api.model_name` dependency; fixture assertions should read that list rather than assume a label.
