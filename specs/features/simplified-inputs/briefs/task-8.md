# Task 8 — Author selection beside Modeling inputs

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [author in Modeling](../plan.html#lifecycle), [new dependents](../plan.html#new-dependents). Task: [overview](../tasks.md#task-8). Status: under review.
Implementation: standard — Task 3/4 provide addresses and patches, and `CreateObjectUseCase` has one final save after request-local hooks; map draft fields to created IDs and use deletion's actual cascade.

## Start here

- [`FormContextBuilder.build_creation_context()`/`build_edition_context()`](../../../../model_builder/adapters/forms/form_context_builder.py): field context after creation strategy; [`generate_dynamic_form()`](../../../../model_builder/adapters/forms/form_field_generator.py): existing `dynamic_lists` and candidate reference options.
- [`build_source_table_row_editor_context()`](../../../../model_builder/adapters/views/source_table_row_editor_context.py): per-input Sources editor without eager model hydration; [`source_table_row_editor.html`](../../../../model_builder/templates/model_builder/result/source_table_row_editor.html): row UI.
- [`CreateObjectUseCase.execute()`](../../../../model_builder/application/use_cases/create_object.py) and [`DeleteObjectUseCase.check_can_delete()`/`execute()`](../../../../model_builder/application/use_cases/delete_object.py): creation/cascade save boundaries and existing confirmation.

## Change along the code path

Attach true field owner addresses and current setting to eligible normal edit fields and Sources rows. `bookmark.html` wraps Task 7's `selection_controls.html` in a compact disclosure; only opening it reveals Include/help. Existing-input inclusion/help patches call Task 4 immediately and update visible bookmarks only, preserving surrounding unsaved values; Undo applies an inverse membership patch against current dependencies. For creation, keep membership/help in the form draft. Enrich the existing `dynamic_lists` entry with `simplified_required_by` for candidate controller objects; fixed edit relationships receive the same requirement directly on field context. JS previews and locks required inclusion as the parent choice changes, but leaves help editable. On successful creation, map provisional controls to final object IDs, rebuild closure and persist with the model. Delete confirmation names exposed fields in the actual cascade; successful deletion prunes selection and retained help for removed owners.

## Earlier tasks

Tasks 3–4 supply addresses/catalog and config patching. Task 7 supplies shared controls and presenter targeting; Task 6 protects immediate bookmark requests. Task 9 later shares source/value field rendering.

## Reuse

Reuse `dynamic_lists`, existing form strategy output, side-panel source editor, delete confirmation and current error modal. Do not autosave creation settings. `CreateObjectUseCase._link_to_parent()` calls `edit_object_from_parsed_data()` with the default `update_system_data=False`; the creation use case calls `model_web.persist_to_cache()` once, after parent linking and `post_create`. Install resolved settings before that final save.

## Invariants and traps

Storage fields shown in a Server panel belong to Storage's ID. A new object has no owner ID yet, so the control ID is provisional and the server resolves it after creation/hooks. Required inclusion is derived, not a permanent lock; changing API A to B can release Resolution. A failed create shows the existing modal, clears its panel and saves no pending settings. Existing bookmark failures preserve the surrounding panel/row draft. Delete cleanup follows actual cascade owners, not only the clicked object's ID. Do not sync a hidden Simplified inputs view during Modeling mutations; Task 7 re-renders it on entry.

## Validation

Run `poetry run pytest tests/unit_tests/adapters/forms/test_form_context_builder.py tests/unit_tests/application/use_cases/test_create_object.py tests/unit_tests/application/use_cases/test_delete_object.py tests/integration/test_simplified_inputs.py` and focused Sources/bookmark Jest/E2E checks. One combined browser flow should cover edit bookmark, Sources row, creation with API A then B requirement preview, help retained, creation success and deletion warning. Unit/integration cases cover failed/cancelled creation and cascade pruning.

## Out of scope

No general creation error-recovery UX, full-view refresh on inline saves, or value changes through bookmarks.

## Verified creation boundary

`ServerWeb.pre_create()` adds Storage to the request-local model before Server creation; the other inspected `pre_create`, `pre_add_to_system` and `post_create` hooks transform input or relationships without persisting. Resolve nested Storage settings through the created Server's Storage reference, then apply closure to the actual created owners before the final save. `DeleteObjectUseCase.execute()` persists after its list-removal or `self_delete()` cascade; derive removed owner IDs from the post-delete model rather than assuming only the clicked object was removed.
