# Blank inline relationship count: an optional number input posts an invalid empty value

- **Status:** CONFIRMED
- **Confidence:** high — the shared rendered control has no blank guard, its HTMX endpoint passes the empty POST value directly to the numeric parser, and the parser deterministically raises the reported message before any mutation. The existing focused invalid-count view test passed locally (2 cases), and a live GenAI-template inspection confirmed that a cleared control is considered valid by the browser because it is not required.
- **Reported:** “When a count is set to no value (for example, a usage journey step count in the object card), it creates repeated ‘Count should be a number’ errors from the backend. THere should probably be client validation that counts are always numbers.” The client-validation hypothesis is substantially correct for the autosaving inline relationship-count control: blank is currently allowed by the HTML control and reaches the backend. The exact current backend copy is “Count must be a number.”, not “Count should be a number.” (`e-footprint-interface/model_builder/adapters/forms/form_data_parser.py:25-30`). There is no autonomous request loop in the wiring; the still-blank control can produce the same error again when another `change` is committed.

## Root cause

This is an interface-owned validation gap, not a library modeling bug. A usage-journey step's displayed count is the magnitude of an existing weighted-dictionary entry (`journey.uj_steps[step]`); `count_in_dict_container` resolves the owning dict and reads that magnitude (`e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:197-205`). Weighted relationships are represented as `ExplainableObjectDict` entries whose values are explicit dimensionless counts, and relationship resolution is generic across all annotated modeling classes (`e-footprint-interface/model_builder/domain/services/object_linking_service.py:30-42`, `e-footprint-interface/model_builder/domain/services/object_linking_service.py:45-58`). Therefore an existing relationship has a numeric weight; absence is represented by unlinking the dict entry, not by a null count.

The object-card path is:

1. `journey_step_card.html` includes `inline_count.html` next to every journey step (`e-footprint-interface/model_builder/templates/model_builder/object_cards/journey_step_card.html:30-46`). The same partial is also used for resource-need/job cards (`e-footprint-interface/model_builder/templates/model_builder/object_cards/resource_need_card.html:4-22`).
2. `inline_count.html` renders the shared `dict_entry_count_unlink.html` partial with the current magnitude, `min=0`, a compatible decimal step, and no unlink button (`e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/inline_count.html:1-8`). Canvas counts intentionally allow numeric zero: the existing E2E workflow verifies that zero remains linked and dims the contributing card (`e-footprint-interface/tests/e2e/objects/test_usage_journeys.py:143-171`).
3. The shared partial emits `<input type="number" ... name="count">`, but it has neither `required` nor a blank-normalization handler. It posts on every `change` to `/model_builder/update-dict-count/<parent>/<entry>/`, uses `hx-swap="none"`, and only has client behavior for toggling the zero-dimming class (`e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html:1-12`). The route maps directly to `update_dict_count` (`e-footprint-interface/model_builder/urls.py:41-43`). Since an empty non-required number input is valid HTML, browser constraint validation does not reject it; live inspection of the unmodified GenAI template confirmed `validity.valid == true` after clearing the count.
4. `update_dict_count` retrieves `request.POST.get("count")` and immediately calls `parse_count` (`e-footprint-interface/model_builder/adapters/views/views_dict_mutation.py:60-67`). `parse_count` calls `float(raw_value)` and converts either `""` or `None` into `ValueError("Count must be a number.")` (`e-footprint-interface/model_builder/adapters/forms/form_data_parser.py:25-35`). Because this happens before `_build_edit_form_data`, `EditObjectUseCase`, or persistence, the stored relationship remains unchanged (`e-footprint-interface/model_builder/adapters/views/views_dict_mutation.py:62-72`).
5. The generic decorator catches that `ValueError` and returns a status-200 out-of-band exception modal with `HX-Reswap: none` (`e-footprint-interface/model_builder/adapters/views/exception_handling.py:82-104`). The modal also closes the side panel and hides results when inserted (`e-footprint-interface/model_builder/templates/model_builder/modals/modal_template.html:27-31`), which amplifies the UX disruption.

The “repeated” part is persistence of invalid client state, not timer/polling recursion. The only request trigger on this control is the native `change` event (`e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html:5-7`). The error response deliberately does not replace the triggering input (`HX-Reswap: none`), so its empty DOM value is left in place (`e-footprint-interface/model_builder/adapters/views/exception_handling.py:88-96`). A single numeric-to-blank committed change produces one failing POST; later edits/committed changes can produce the same failing POST again. No `input`, `load`, polling, or post-response retrigger is attached to this control.

The problem is broader than just journey-step cards because the same partial also renders counts in edge-device-group rows (`e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/group_entry_row.html:1-23`, `e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/group_entry_row.html:42-63`) and reverse-membership rows in edit panels (`e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/dict_membership_section.html:1-12`). Fixing the shared autosave control covers those surfaces consistently.

Two superficially similar inputs already have different, intentional semantics and should not be swept into this bug:

- Dict-count widgets inside Apply-button forms already reject blank/non-numeric input client-side by rebuilding the row from the unchanged selected map; they never write the bad value to the hidden JSON payload (`e-footprint-interface/theme/static/scripts/dict_count.js:56-67`, `e-footprint-interface/theme/static/scripts/dict_count.js:114-121`). This is the precedent for restoring an existing relationship's prior count.
- The create-child panel's `parent_link_count` defaults to 1 (`e-footprint-interface/model_builder/templates/model_builder/side_panels/add/add_panel__generic.html:24-31`); its parser intentionally maps blank to `None` (`e-footprint-interface/model_builder/adapters/forms/form_data_parser.py:184-188`), and the creation use case interprets `None` as count 1 (`e-footprint-interface/model_builder/application/use_cases/create_object.py:145-149`). Its blank behavior is covered explicitly (`e-footprint-interface/tests/unit_tests/adapters/forms/test_form_data_parser.py:297-306`) and does not yield the reported backend error.

## Fix approach

Prevent a blank value from reaching HTMX and restore the last value that was displayed when editing began. Restoration is the smallest correct semantic choice: it preserves the persisted weighted-dict entry, matches the existing dict-count widget's invalid-input behavior, and avoids silently converting an accidental deletion to numeric zero. Zero remains a distinct, valid explicit value on canvas relationships; removal remains the explicit unlink action available in group rows and edit-panel membership rows (`e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html:13-21`).

Implement this once for the shared `.count-inline-edit` autosave control, preferably as a small delegated vanilla-JS handler so it survives HTMX/OOB-rendered partials: remember the current value on focus, intercept a committed blank before HTMX handles `change`, restore the remembered value, and suppress that change's POST. Add `required` to the markup as semantic/native-validation metadata, but do not rely on `required` alone: the control is not a form submission, and leaving an empty invalid value visible would keep client and persisted state inconsistent. Preserve the backend `parse_count` validation as defense in depth for direct/malformed requests.

Do not reinterpret blank as unlink: object-card counts intentionally have no inline unlink control (`e-footprint-interface/tests/e2e/objects/test_usage_journeys.py:151-155`), while the shared partial renders a separate explicit unlink button only on surfaces that permit removal (`e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html:13-21`). Do not reinterpret blank as zero: zero is already a deliberate accepted input with observable dimming and recalculation behavior (`e-footprint-interface/tests/e2e/objects/test_usage_journeys.py:166-171`).

The fix belongs in the interface presentation/client layer. This respects the documented request lifecycle—user action, adapter view, use case, presenter, partial response (`e-footprint-interface/specs/architecture.md:41-47`)—and the constitution's rule that the library owns modeling logic while HTMX/vanilla JS owns unavoidable UI behavior (`e-footprint-interface/specs/constitution.md:9-12`). No `e-footprint` change is needed.

## Files to touch

- `e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html` — mark the shared autosaving count and expose semantic required/numeric constraints as needed; keep normal numeric `change` posts unchanged.
- `e-footprint-interface/theme/static/scripts/model_builder_main.js` (or a narrowly named count-control script loaded by the builder) — delegated focus/change handling that restores a committed blank and prevents its HTMX request, including controls inserted by OOB swaps.
- `e-footprint-interface/js_tests/build_fixtures.py` and `e-footprint-interface/js_tests/<inline-count test>.test.js` — render the real shared partial and cover blank rollback/event suppression if the handler is factored for jsdom.
- `e-footprint-interface/tests/e2e/objects/test_usage_journeys.py` and `e-footprint-interface/tests/e2e/pages/components/object_card.py` — exercise the actual object-card/HTMX interaction and provide a page-object helper for keyboard clearing if needed.
- `e-footprint-interface/tests/unit_tests/adapters/views/test_views_dict_mutation.py` — add blank to backend-invalid coverage so defense in depth and non-mutation remain explicit.
- `e-footprint-interface/CHANGELOG.md` — record the user-visible fix under Unreleased at implementation time, per constitution quality gate (`e-footprint-interface/specs/constitution.md:14-21`).

## Tests

- Extend a JS test rendered from the real Django partial (the testing guide requires real-template fixtures for DOM-manipulating JS: `e-footprint-interface/specs/testing.md:190-196`) to assert: focus a numeric count, clear it, commit change; the previous value is restored and the event does not reach the request trigger. Also assert that `0`, an integer, and a decimal pass through unchanged.
- Extend `TestCanvasInlineCounts` to clear a journey-step count and blur it, then assert no exception modal appears, the visible prior count is restored, and no relationship/recalculation mutation occurs. This is an E2E concern because it spans native input events and HTMX; the test guide assigns such behavior to Playwright (`e-footprint-interface/specs/testing.md:5-12`). Keep the existing numeric edit and zero-dimming assertions (`e-footprint-interface/tests/e2e/objects/test_usage_journeys.py:147-171`).
- Add `""` (and optionally an omitted `count`) to `test_update_dict_count_rejects_invalid_count`, asserting the existing modal and unchanged persisted value. The test already proves non-numeric/negative requests render the modal and do not mutate the relationship (`e-footprint-interface/tests/unit_tests/adapters/views/test_views_dict_mutation.py:145-173`).
- Focused verification run during diagnosis: `poetry run pytest tests/unit_tests/adapters/views/test_views_dict_mutation.py::TestDictMutationViews::test_update_dict_count_rejects_invalid_count -q` → **2 passed**. This confirms the present defensive endpoint/error-modal path for the two covered invalid values; blank is deterministic static evidence from the same parser branch but is not yet a regression parameter.

## Acceptance criteria

- Clearing and committing an autosaving relationship count in a journey-step card, nested job/resource card, edge-device-group row, or edit-panel membership row sends no count-update request and shows no backend exception modal.
- The input immediately returns to the numeric value it had when editing began, so the DOM remains consistent with the persisted model.
- Explicit `0` continues to save where the surface allows zero and continues to dim/recompute as today; positive integer and decimal counts continue to save normally.
- Explicit unlink remains the only way to remove a relationship; blank never means unlink or zero.
- Direct requests with blank, missing, non-numeric, or negative `count` remain rejected by the backend without mutating the model.
- The existing inline-count E2E workflow, dict-mutation view tests, and relevant JS tests pass.

## Risks and side effects

- A handler that merely adds `required`/`hx-validate` but leaves the field blank would stop backend traffic while preserving a false UI state; restoration is required.
- Restoring the HTML `value` attribute or `defaultValue` is unsafe after a successful `hx-swap="none"` edit because the original attribute is not re-rendered; capture the live property when editing begins instead (`e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html:2-8`).
- Event ordering matters: blank suppression must occur before HTMX's `change` listener issues the request. A delegated capture-phase handler or an explicit filtered trigger is safer than relying on the relative order of independent bubbling listeners.
- The shared partial includes both zero-allowed (`min=0`) and group-card (`min=1`) controls (`e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/inline_count.html:7-7`, `e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/group_entry_row.html:22-22`). The fix must restore rather than hard-code `0` or `1`.
- Client validation is not a reason to weaken backend parsing; direct API/malformed HTMX requests must remain safe.

## Flags

- **Invariant:** keep the change in interface templates/vanilla JS and adapter tests; no library modeling logic belongs in the interface (`e-footprint-interface/specs/constitution.md:9-12`).
- **Cross-repository ordering:** none; `e-footprint` is unaffected.
- **Migration/serialization:** none; blank is rejected before persistence today and the fix changes no stored shape.
- **Validation limitation:** the exact report was confirmed statically and through live DOM validity inspection; the local focused test lacks a blank parameter, which is part of the required regression work.
- **Documentation:** no new pattern is required if this uses the existing delegated-event/invalid-value rollback conventions; no architecture update is necessary.

## Decisions

- **2026-08-31:** Treat blank as an invalid transient edit and restore the prior live count. Do not map blank to zero, unlink, or the create-panel default of one.
- **2026-08-31:** Apply the behavior to the shared autosaving relationship-count partial, not the already-guarded dict-count form widget or the intentionally defaulting create-child `parent_link_count` field.

