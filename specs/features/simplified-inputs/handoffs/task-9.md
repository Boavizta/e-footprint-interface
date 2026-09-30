# Task 9 — Edit simple selected inputs and refresh totals

Interface implementation range: `0a1d6e8c4196ab2d7de28ae230976365f58bada2..6cf746bee16a00e3ee5ffc1935541838aebf1974`.
Library unchanged at `b03a48ce32afe61b7a92b081fa61741e0c515cff`.

## Review pointers

- `views_simplified_inputs.edit_simplified_input()` translates owner-specific DOM names through the normal parser and invokes the existing atomic use case. `present_edited_input()` filters field generation by `changed_fields`, preserving unrelated drafts; provenance completion omits unchanged metadata. Timeseries editing and export completion remain Task 10.
- `ModelingObjectWeb._recompute_state_and_emit_oob_regions()` now refreshes paired totals on every accepted mutation. `hammer_utils.js` reapplies the existing open Results layout after HTMX settlement: OOB replacements previously restored the button's server attributes after the panel script hid it, preventing the next inline-count edit from requesting detailed recomputation. Review the existing repeated-count E2E alongside the new autosave flow.
- At the default Chromium viewport (1280 × 720), full-height Results intercepted the simplified editor's Retry save button. `_simplified_inputs.scss` reserves the upper half for Simplified inputs and caps Results at the lower half on desktop (≥1200px); Modeling layout is unaffected. `test_simple_autosave_deduplicates_preserves_failed_draft_and_refreshes_results` exercises retry and provenance completion with Results open, followed by a Modeling edit.
- `test_large_selected_model_value_save_builds_only_affected_editor` checks a 61-server / 61-selected-input model without building unrelated editors. Validation used local Python 3.12.11, the editable library checkout above, localhost:8000 and CSS compiled with Sass 1.100.0.

## Open concerns

- The required non-E2E suite retains the expected failure in `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject`. Pre-existing editable `pyproject.toml` and `poetry.lock` remain uncommitted as required by the [local-development and deployment gates](../tasks.md#gates); restore the matching published dependency during release preparation.
