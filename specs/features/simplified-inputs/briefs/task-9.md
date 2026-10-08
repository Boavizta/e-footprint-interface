# Task 9 — Edit simple selected inputs and refresh totals

Updated 8 October 2026 to match the [consolidated review adjustments](../plan.html#save-errors); the original task boundary and baseline below are retained.

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [consumption](../plan.html#consume), [saves](../plan.html#saves), [totals](../plan.html#totals). Task: [overview](../tasks.md#task-9). Status: approved.
Implementation: standard — connect Task 5/6/7 outputs through HTTP save status, targeted swaps and Results OOB rendering.

## Start here

- Task 5 `EditSimplifiedInputUseCase` and Task 7 grouped presenter/partials (new symbols, not yet in baseline); [`parse_form_data()`](../../../../model_builder/adapters/forms/form_data_parser.py): current value/source parsing.
- [`render_exception_modal()`](../../../../model_builder/adapters/views/exception_handling.py) and [`modal_template.html`](../../../../model_builder/templates/model_builder/modals/modal_template.html): error responses use HTTP 422/500, `HX-Reswap: none` and an OOB modal; `openModalDialog` only opens it.
- [`_render_results_buttons()`](../../../../model_builder/adapters/presenters/oob_regions.py), [`ModelingObjectWeb._recompute_state_and_emit_oob_regions()`](../../../../model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py): current Results button refresh; [`views_edition.edit_object()`](../../../../model_builder/adapters/views/views_edition.py): detailed-result recomputation path.

## Change along the code path

Render saved selected fields as normal number/select inputs with source/confidence/comment disclosure; retain existing labels, unit handling and authored help. On blur/Enter for number/text metadata or change for selects, send one request through Task 6 guard to Task 5's use case. Detect Enter-then-blur once. A successful response replaces only affected field/bookmark controls, reports dependent fallback and refreshes detailed results when open. A simplified-save error opts into `preserve_panels`, reads the active repository afresh, restores accepted field fragments OOB and shows Not saved. Initial model/catalog failure returns only the 500 modal. Known validation uses `InputValidationError` and returns 422; persistence and unexpected failures remain 500. Discard the rejected inline value without Retry/Discard state; Configure and bookmark drafts remain separate. Build one active-model total context and render it into both existing Results controls. Emit the `results_buttons` OOB region after successful Modeling value, structural, creation and deletion changes even when computability has not flipped.

## Earlier tasks

Task 5 supplies atomic accepted values/notices; Task 6 blocks overlapping requests; Task 7 supplies the selected-field surface; Task 8 supplies bookmark targeting. Task 10 adds timeseries and export completion. Preserve changed-field targeting; Configure Save from Task 7 may still replace the whole selected view.

## Reuse

Keep existing library display formatting, `ModelWeb.persist_to_cache()` total pull, source metadata controls, `OobRegion("results_buttons")`, `render_exception_modal()` and `recomputation: true` result-panel refresh. No new cache-invalidation state.

## Invariants and traps

HTTP success distinguishes save outcome. On failure, both totals keep their existing content and the field shows repository state. Before use-case success restore the submitted address; after a late presentation failure restore all persisted changed fields, including conditional dependents. Preserve unrelated unsaved controls during targeted updates. The source/comment editor must not erase omitted provenance. The shared guard covers Modeling mutations too; always restore constraint-disabled buttons. Avoid rendering hidden structural inputs as simplified editors.

## Validation

Run `poetry run pytest tests/integration/test_simplified_inputs.py` plus focused OOB and results tests under `tests/unit_tests/adapters/` and `tests/integration/test_results_views_smoke.py`; run `npm run jest -- --runInBand js_tests/simplified_inputs.test.js js_tests/model_builder_main.test.js`. Use a critical E2E flow with delayed save, Enter/blur, 422/500 modal and accepted-value restoration, open Results panel and a successful Modeling edit to confirm both totals update. Check a representative large model for avoidable full rendering; record the environment/build used.

## Out of scope

No timeseries editor or export deferral; those finish in Task 10. Do not change ordinary Modeling error-panel behavior.

## Verified total targets

`_render_results_buttons()` already renders both `results_bar_button.html` and `show_results_toolbar_button.html` as OOB replacements. Their stable targets are `#btn-open-panel-result` and `#show-results-toolbar-btn`; both currently receive `model_web` and `oob`, with no total context. Add one shared total context and display it in those two existing partials.
