# Task 2 — Declarative field saves
Written 2026-10-19 against `e-footprint-interface` commit `e34a9bb3`.
Plan: [1.2 Field save](../plan.html#field-save), [PLAN-UPDATE-02](../plan.html#plan-update-02), [-04](../plan.html#plan-update-04), [-07](../plan.html#plan-update-07), [-10 (rejected)](../plan.html#plan-update-10).
Task: [Task 2](../tasks.md#task-2--declarative-field-saves).
Status: under review.

## Start here
- `createFieldEdits` — `theme/static/scripts/simplified_inputs/field_edits.js`: every job listed in plan 1.2 "Current state", which this task deletes.
- The `<form data-simplified-editor>` and status `<span>` — `model_builder/templates/model_builder/simplified_inputs/editor.html`; `field.html` includes it.
- `present_edited_input`, `render_input_fields_oob` — `model_builder/adapters/presenters/simplified_inputs.py`.
- `edit_simplified_input`, `_rejected_simplified_input`, `simplified_timeseries_panel` — `model_builder/adapters/views/views_simplified_inputs.py`.
- `EditSimplifiedInputUseCase.execute` — `model_builder/application/use_cases/simplified_inputs.py`.
- `[data-simplified-save-status]` rules — `theme/static/scss/_simplified_inputs.scss` (around line 55).
- The export notice listener in `theme/static/scripts/simplified_inputs/index.js`, and the `module.exports` there.

## Change along the code path
1. **Form.** Replace `hx-trigger="simplified-save"` with the plan's attributes: `hx-trigger`, `hx-sync="this:drop"`, `hx-vals='js:{...recomputationVals()}'`, `hx-indicator="#{{ field.dom_id }}-save-status, [data-quick-total-status]"` and `hx-on::validation:halted="this.reportValidity()"`. `recomputationVals()` is in `side_panel_utils.js`. Keep Task 1's lock selector.
2. **Status.** Drop `hx-preserve`, keep the id, add `data-outcome`, and render "Saved" or "Not saved" from `outcome`. `field.html` needs no change if `outcome` is in the include's context; the plan only says it "passes the outcome through".
3. **Response.** Give `render_input_fields_oob` an optional submitted `address` and `outcome`. Put `outcome` in a field's context only when `field["address"] == address`, so companions carry no status. `edit_simplified_input` passes `outcome="saved"` through `present_edited_input`; `_rejected_simplified_input` passes `"rejected"`. The early `render_exception_modal` returns stay without a field fragment, as today.
4. **Notice.** `workspace.html` renders `<p id="si-{{ system_id }}-notice" data-simplified-notice role="status"></p>` right after `</header>`, outside the `{% if configure %}` branches. It must exist in Configure too, because `index.js` writes the dirty-export notice there; this resolves the plan's "saved-view header" wording. `present_edited_input` stops rendering `input_repair_notices.html` and drops the `simplifiedInputSaved` trigger. Instead it renders that paragraph out-of-band (`hx-swap-oob="true"`) with the joined notices; empty text clears it. Keep `triggerResultRendering`. Its `HX-Trigger-After-Settle` still fires inside the swap. `index.js` sets the paragraph's `textContent` instead of creating one.
5. **Use case.** After `apply_input_edits` and before `persist_to_cache()`, read the edited attribute's value. `prepare_input_changes` replaces the object only when its value changed (an `input_values_match` mismatch); a provenance-only edit patches the same object. So an identity check against the value read before applying tells whether the value changed. When it changed and the value is an `ExplainableObject`: if the source is `Sources.HYPOTHESIS` or `Sources.AUTOMATIC_REPLACEMENT` (import from `efootprint.abstract_modeling_classes.source_objects`), set it to `Sources.USER_DATA` and keep the comment and confidence. PLAN-UPDATE-10 was rejected: never reset the confidence. Metadata does not affect calculations, so mutating after the update is safe. If you find a cleaner seam, use it and keep the rule in the use case.
6. **CSS.** In `_simplified_inputs.scss`, `[data-simplified-save-status].htmx-request::after { content: "Saving…" }`, and the same for `[data-quick-total-status]` with "Updating…". Then the fade: `[data-outcome="saved"]` runs a roughly 3 s forwards animation to `opacity: 0`. Recompile `bs_main.css` (see AGENTS.md).
7. **Timeseries panel.** Add `hx-on::after-request="closeAndEmptySidePanel()"`, `hx-vals='js:{...recomputationVals()}'` (today's `configRequest` branch also covers this form) and `hx-indicator="#{{ status_id }}"`. The view computes `status_id = f"si-{system_id}-{object_id}-{attribute}-save-status"`, matching `build_workspace_context`'s `dom_id`. Cancel becomes `onclick="closeAndEmptySidePanel()"`; drop its `data-action`.
8. **Remove** `field_edits.js`, its `require` and `fieldEdits` in `index.js` (export `{ workspace }` only), and its mention in the `conventions.md` module bullet. Drop the "listener order" comment in `index.js`. Update `rendering.html`'s repair-notice paragraph (line 27) to name the out-of-band paragraph.

## Earlier tasks
Task 1 provides zero settle delay and the `:not(:disabled)` lock selector, and removes the restore block. So `afterRequest` already sees final DOM, and nothing restores disabled state.

## Reuse
`render_input_fields_oob` (already used by both outcomes), `closeAndEmptySidePanel()` as in `delete_card_modal.html`, the `hx-vals` recomputation pattern from `list_membership_section.html`, and `render_simplified_editor` in `js_tests/build_fixtures.py`. Add one `outcome` case there for the only remaining editor-markup assertion.

## Invariants and traps
- **Trigger filter.** A bare `change` on the form also fires for nameless controls inside it: the source editor's select, inputs and textarea (`source_editor.html`), and the optional-quantity switch. Unchecking the switch would then save an empty required number, and editing a source would save before Apply. Filter to named controls, e.g. `change[target.name]`. The source editor reports through `simplified-provenance:changed`, and the switch through `optional-quantity:changed[detail.empty]`. Today's code matches number inputs and `select[name]` only.
- **Indicator CSS.** `[data-simplified-save-status]:empty { display: none }` hides the `::after`. Exempt `.htmx-request`. Also, a previous "Saved" (faded) or "Not saved" stays in the span while the next request runs. Hide that text and cancel the animation under `.htmx-request`, e.g. with `font-size: 0` on the span, the size restored on `::after`, and `animation: none`, so only "Saving…" shows.
- The Enter key fires `change` and then the implicit submit; `hx-sync` drops the second. Do not add a keydown listener.
- Provenance is resent unchanged on every save. `_apply_metadata` patch semantics make that a no-op (decision 9). Do not reintroduce trimming.
- The `source-metadata:value-changed` listener in `source_metadata.js` stays for side panels; only the simplified dispatch goes.
- The E2E notice assertions `to_have_count(0)` (around line 1136) become empty-text assertions, because the holder is always rendered.
- Today's client reset of confidence on a value change goes away with the module; that is the spec's accepted change. The removed Jest case asserted the reset, so do not port that assertion.

## Validation
- **View tests** in `tests/unit_tests/adapters/views/test_views_simplified_inputs.py`:
  - an outcome on the submitted field only, for both saved and rejected;
  - a notice fragment with and without repairs, and no `simplifiedInputSaved`;
  - extend `test_value_save_targets_one_field_and_both_totals_and_preserves_provenance` for resent provenance;
  - the user-data rule for hypothesis and automatic sources, and for a comment-only edit, with a changed value keeping its `high` confidence;
  - a timeseries panel context that includes the status id.
- **Jest:** remove the field-save cases in `simplified_inputs.test.js` (the repair-notice case and those from "save status stays visible…" through "timeseries Save closes…", plus export cases that only assert that field edits did not run), and the "simplified optional quantity saves empty…" case in `dynamic_forms.test.js`. Keep the dirty-Configure export cases, adapted to the rendered holder. Update the `require` destructuring at the top of `simplified_inputs.test.js`.
- **E2E** in `tests/e2e/test_simplified_inputs.py`:
  - in `test_field_save_disables_both_resident_workspaces_and_restores_controls`, the Saving… probes check `.htmx-request` on the status and totals instead of text or `aria-busy`, and the transport case expects an empty status;
  - `test_simple_autosave_deduplicates_restores_rejected_field_and_refreshes_results` covers the trigger counts, including the invalid draft and the native message;
  - `test_focused_hourly_panel_save_cancel_failure_and_mobile_preview`;
  - adapt the "automatically replaced value" flow from the removed Jest case.
- **Commands:** `npm run build:js:dev`, compile the SCSS, `npm run jest`, `poetry run pytest tests --ignore=tests/e2e`, then the full E2E suite against a local server.

## Out of scope
Bookmarks (Task 3), workspace reads and exits (Task 4), side-panel metadata hooks, and the source-metadata autosave.

## Unverified
- **Multiple-select encoding.** The vendored HTMX encodes a multiple select as one key per selected option (`un()` in `htmx.min.js`), and `edit_simplified_input` joins `getlist()`. No simplified multiple-select E2E exists today. Add a view test posting repeated keys, and do one manual or E2E multi-select save, before relying on the removed join.
- **Modified tagging in the timeseries panel.** Confirm with the focused-panel E2E that the existing inline `oninput` handlers and the builders' own calls still tag the panel as modified once the module's listeners are gone.
