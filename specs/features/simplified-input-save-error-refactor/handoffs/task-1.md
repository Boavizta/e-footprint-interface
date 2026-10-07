# Task 1 — Return real error statuses and process modal OOB

Repository and implementation range: `e-footprint-interface`, `56f8278addf36c9551cff873466aed89ea2decc3..a912466dfeb01d8e8af85bec8c4194649ca7c42c`. Library unchanged at `14852b3a0beeee3bcf7ac428d2406c5e26e856e1`.

## Review pointers

- `render_exception_modal()` defaults to 500. Each save view catches recognized validation only around parsing or use-case execution; rendering and persistence retain the generic fallback. Ordinary side-panel cleanup and Simplified workspace/panel preservation use the existing modal payload.
- `modal_utils.js` loads before `model_builder_main.js`: its `beforeSwap` handler permits OOB processing for HTTP errors carrying `HX-Reswap: none` and retains `isError`. Mutation settlement waits for the swap to settle and derives success from HTMX's `successful` flag. Bookmark outcomes use the same flag.

## Design decisions

- Introduced `InputValidationError(ValueError)` because definition validation and persistence share a use-case entry point, while `save_interface_config()` can itself raise `ValueError`. Producers are `complete_selection()`, `validate_definition()`, the explicit validation branches in `UpdateSimplifiedDefinitionUseCase.execute()`, `EditSimplifiedInputUseCase.execute()`, and `reconcile_simplified_definition()`. The inline use case also converts `ValueError` specifically from its `prepare_input_changes()` boundary before mutation/persistence. Catchers are `add_object()`, `edit_object()`, `edit_simplified_input()`, `save_simplified_inputs()`, and `patch_simplified_inputs()` around use-case execution. Parsing is caught separately; side-panel and inline use-case boundaries additionally recognize the library's `WeeklyPatternValidationError`. Arbitrary use-case, rendering, hydration, and persistence failures remain 500. The supervisor will promote this rationale into the approved plan and Task 3 architecture documentation.

## Open concerns

- Full non-E2E pytest remains blocked by the pre-existing editable `efootprint` entry in `pyproject.toml`, reported by `tests/test_no_dev_dependency.py`. The file and lock were preserved. The diagnostic fallback excludes only that test file.
- Plain `npm run jest` discovers the pre-existing untracked `tools/vscode-plan-review-links/extension.test.js` and fails because `extension.js` imports unavailable `vscode`. Those files were preserved. The diagnostic fallback excludes only that extension test. These exclusions do not satisfy the full workspace gates; final E2E validation belongs to Task 3.
