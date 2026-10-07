# Task 1 — Return real error statuses and process modal OOB
Written 2026-10-07 against e-footprint-interface `f005dee5`.
Plan: [error response](../plan.html#modal-response). Task: [Task 1](../tasks.md#task-1--return-real-error-statuses-and-process-modal-oob).
Status: approved — implementation pending.

## Start here

- `render_exception_modal()` / `render_exception_modal_if_error()` — `model_builder/adapters/views/exception_handling.py` — shared modal and catch-all fallback.
- `add_object()` / `edit_object()` — `model_builder/adapters/views/views_addition.py` and `views_edition.py` — parsing and domain-validation boundaries.
- `edit_simplified_input()`, `save_simplified_inputs()`, `patch_simplified_inputs()` — `model_builder/adapters/views/views_simplified_inputs.py` — three save POSTs; `simplified_timeseries_panel()` is a GET.
- `htmx:beforeSwap` / `htmx:afterRequest` — `theme/static/scripts/modal_utils.js`, `model_builder_main.js`, `simplified_inputs.js` — OOB processing, mutation settlement and bookmark status.

## Change along the code path

Give the shared modal helper a 500 default and an explicit status argument. Identify validation at the parsing or use-case boundary in each named POST, pass 422 there, and leave unclassified errors to 500. `WeeklyPatternValidationError` is a typed side-panel case. A broad `ValueError` catch around the whole save would mislabel repository or rendering failures; `SessionSystemRepository.save_interface_config()` can itself raise `ValueError` in current tests. Keep `HX-Reswap: none`, `HX-Trigger-After-Settle` for opening the modal, and the existing `preserve_panels`/`preserve_workspace` flags. The shared decorator remains a 500 catch-all for other views.

The `modal_utils.js` `beforeSwap` listener runs before the mutation guard. For an HTTP error with `HX-Reswap: none`, set `shouldSwap = true` while preserving `isError = true`: HTMX processes OOB content, skips the main target, and emits settlement. The guard derives success from `event.detail.successful`; the bookmark handler does likewise. See the [proposed contract](../plan.html#modal-response).

## Earlier tasks

None. This task establishes the status and settlement contract consumed by Tasks 2–3.

## Reuse

`model_builder/templates/model_builder/modals/exception_modal.html` already contains the OOB modal; no payload format change. `parse_form_data()` owns transport conversion. The existing `WeeklyPatternValidationError` examples in `test_views_addition.py` and `test_views_edition.py` exercise typed library validation. `test_workspace_views.py` and `test_computation_memory_middleware.py` cover whole-builder and middleware paths.

## Invariants and traps

HTTP 422 means a recognized validation rejection, not every POST or `ValueError`. Preserve successful 200 responses, ordinary side-panel cleanup, `HX-Reswap: none`, and OOB modal opening on both error statuses. Do not change domain validation or catch exceptions in inner layers. A modal trigger remains an action signal, never a save-outcome signal.

## Validation

Extend `tests/unit_tests/adapters/views/{test_views_simplified_inputs,test_views_addition,test_views_edition,test_views_dict_mutation,test_sankey_views}.py`, `tests/integration/{test_workspace_views,test_results_views_smoke}.py`, `tests/unit_tests/test_computation_memory_middleware.py`, and `js_tests/{model_builder_main,simplified_inputs}.test.js`. Assert 422 only for identified validation; 500 for generic/memory/persistence failures; OOB modal and preserved target on both; successful mutation still 200. Update the smoke-test comment that assumes HTTP-200 error modals. Run `poetry run pytest` on changed Python test files and `npm run jest -- --runInBand` in the interface checkout. Browser behavior receives the final E2E gate in Task 3.

## Out of scope

Accepted-field restoration, failed-draft removal, documentation synchronization and library changes.

## Unverified

Exact exception types from all library constructor paths vary; classify only verified typed exceptions or errors caught at a clearly identified parsing/validation boundary. Check any newly encountered exception at its source before assigning 422.
