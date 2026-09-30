# Task 3 — Establish the definition and eligible-field catalog

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [shared data](../plan.html#contract), [eligible inputs](../plan.html#dependencies). Task: [overview](../tasks.md#task-3). Status: under review.
Implementation: standard — integrate existing constructor/conditional metadata, form fields and timeseries builder lookup into one catalog.

## Start here

- [`generate_dynamic_form()`](../../../../model_builder/adapters/forms/form_field_generator.py): constructor signatures, class `list_values`/`conditional_list_values`, dotted dependency traversal and existing field dictionaries.
- [`build_timeseries_form_config()`](../../../../model_builder/adapters/forms/timeseries_builder_registry.py): builder lookup and editor configuration; [`resolve_optional_annotation()`](../../../../model_builder/domain/type_annotation_utils.py): annotation normalization.
- [`ModelWeb`](../../../../model_builder/domain/entities/web_core/model_web.py): object graph and IDs; [`upgrade_interface_config()`](../../../../model_builder/version_upgrade_handlers.py): existing versioned config migration boundary.

## Change along the code path

Add `FieldAddress` (true owner ID and constructor attribute), JSON-shaped `FieldSetting` and `SimplifiedInputsDefinition`, then a `FieldCatalog` mapping field addresses to eligibility and direct dependent addresses. Read existing constructor metadata; allow numbers, eligible selects and whole supported timeseries, with Country/Network/Device relationship exceptions. Extract the current dotted-path resolver into `domain/conditional_inputs.py` for forms and catalog. Extract lightweight timeseries builder lookup in the adapter registry, then pass its `can_edit_timeseries` function into `build_catalog`; the domain never imports the adapter. `complete_selection` follows dependents recursively, and `validate_definition` checks persisted addresses, eligibility and completeness. Empty and absent definitions normalize without adding values.

## Earlier tasks

Task 2 fixes the library's own sibling-dependent validation. This task introduces the address/catalog/closure APIs that Tasks 4, 5, 7 and 8 use. Do not add a second class-metadata schema or editor registry.

## Reuse

Use `get_init_signature_params()`, `resolve_optional_annotation()`, existing form contexts, `editable_builders_for()`, and library conditional metadata. Preserve current form exclusions, labels, ordering, provenance and `dynamic_lists` output. One current `select_object` widget may be Country while another is Server; decide eligibility from type and relationship policy, not widget name alone.

## Invariants and traps

Persist string keys under `interface_config.simplified_inputs.fields`; `FieldAddress` is request-local. Resolve nested Storage and cross-object `external_api.model_name` to the actual owner. A controller with an ineligible required companion is ineligible; a dependent may be selected alone. Keep authored help capitalization. The version upgrade loop only runs for older major versions, so ensure files already at the current version but lacking this optional key also read as empty.

## Validation

Run focused catalog tests to add under `tests/unit_tests/domain/`, plus `poetry run pytest tests/unit_tests/adapters/forms/test_form_field_generator.py tests/unit_tests/adapters/forms/test_form_context_builder.py` in the interface. Assert empty optional numbers, unsupported timeseries, structural exclusions, reference exceptions, dotted owner resolution, chained closure and required-removal rejection. Use real model fixtures from `tests/fixtures/system_builders.py` for a cross-owner case. Normal form snapshots must still pass.

## Out of scope

No saved configuration mutation, importer replacement, browser view or value editing.

## Unverified

The exhaustive eligible-type matrix should be built from actual constructor signatures during implementation; the plan's policy, not a hand-maintained field list, decides each case.
