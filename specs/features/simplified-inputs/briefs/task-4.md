# Task 4 — Save configuration and exchange independent models

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [configuration save](../plan.html#configuration-save), [workspace files](../plan.html#persistence). Task: [overview](../tasks.md#task-4). Status: under review.
Implementation: standard — extend `save_interface_config()`, slot/ID helpers and `SystemImportService`; preflight both models before the current restore writes.

## Start here

- [`SessionSystemRepository.interface_config`, `save_interface_config()` and `save_data()`](../../../../model_builder/adapters/repositories/session_system_repository.py): config/cache/session publication and size checks; [`InMemorySystemRepository`](../../../../model_builder/adapters/repositories/in_memory_system_repository.py): framework-free parity.
- [`with_fresh_system_id()`](../../../../model_builder/adapters/repositories/workspace_base.py): remints only the System and carries interface metadata; [`_restore_workspace()` and `_system_data_for_add()`](../../../../model_builder/adapters/views/views_workspace.py): replacement and duplication paths.
- [`upload_json()`](../../../../model_builder/adapters/views/views.py): single/workspace opening; [`SystemImportService.import_system()`](../../../../model_builder/domain/services/system_import_service.py): modeling import and size validation.

## Change along the code path

Add `UpdateSimplifiedDefinitionUseCase` over the Task 3 definition: Configure replaces the complete settings; an inline bookmark patches specified field properties against current saved settings. Complete and validate selection, then call `repository.save_interface_config()` without model hydration or recomputation. Move `SessionSystemRepository.save_data()`'s session config publication after the budget check, and scope recovery fallback by slot and System ID; match the in-memory save contract. Duplication copies configuration independently, remapping any System-owned field address when the System ID changes. Prepare every incoming workspace model and combined budget before clearing live slots; keep the same per-model/workspace JSON formats.

## Earlier tasks

Task 3 supplies normalization, addresses, catalog, `complete_selection` and `validate_definition`. Task 7 will own HTTP entry/default-view behavior, using the saved definition produced here.

## Reuse

Keep `ISystemRepository`, `SystemImportService`, the existing distinct-ID helper and repository `save_interface_config()` API. `SystemImportService._preserve_interface_metadata()` currently passes config through; it is not the definition validator. Prefer the existing repository paths over a new persistence layer.

## Invariants and traps

The session fallback is currently a single `interface_config` key, so a slot-aware read must not leak another model's guidance. A budget failure must not publish new config to session, Redis or Postgres. `_restore_workspace()` currently clears before importing model 2; complete model loading and aggregate sizing before this mutation. `with_fresh_system_id()` preserves config by copying it verbatim today, so remap the System's field-address key. Clear removes all per-field entries, including excluded help, while retaining title/guidance. Definition validity is enforced when settings are saved, not rechecked on import.

## Validation

Run new use-case integration tests in `tests/integration/test_simplified_inputs.py`, `poetry run pytest tests/unit_tests/adapters/repositories/test_workspace_repository.py tests/integration/test_workspace_file.py tests/integration/test_workspace_integration.py tests/integration/test_workspace_views.py`. Assert replacement/patch semantics, failed budget publication, duplicate independence, System-ID remapping, both model definitions in exports and malformed second-model modeling data preserving the old workspace. Use local in-memory repositories for domain flows and the existing Django client fixtures for file routes.

## Out of scope

No configuration page, bookmark controls or changes to the library JSON schema.
