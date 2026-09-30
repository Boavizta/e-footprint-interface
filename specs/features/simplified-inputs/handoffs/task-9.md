# Task 9 — Edit simple selected inputs and refresh totals

Interface implementation range: `0a1d6e8c4196ab2d7de28ae230976365f58bada2..156f33e8c6153dca629b711e36e6a1c1204583ab`.
Library unchanged at `b03a48ce32afe61b7a92b081fa61741e0c515cff`.

## Review pointers

- `views_simplified_inputs.edit_simplified_input()` translates owner-specific DOM names through the normal parser and invokes the existing atomic use case. `present_edited_input()` filters by `changed_fields` before generating editors, preserving unrelated drafts and avoiding full workspace rendering. Conditional choices resolve against accepted owner state on both entry and affected-field replacement. Timeseries editing and export completion remain Task 10.
- Future editor variants must record accepted form snapshots after `workspace-mutation:finished` releases disabled controls; unchanged provenance is omitted from subsequent submissions. Custom source Name and Link complete together when leaving their group or pressing Enter. See the [shared form contract](../../../architecture/forms-and-relationships.html#simplified-input-catalog).
- `ModelingObjectWeb._recompute_state_and_emit_oob_regions()` now refreshes paired totals on every accepted mutation. `hammer_utils.js` reapplies the existing open Results layout after HTMX settlement: OOB replacements previously restored the button's server attributes after the panel script hid it, preventing the next inline-count edit from requesting detailed recomputation. Review the existing repeated-count E2E alongside the new autosave flow.
- `_simplified_inputs.scss` shares desktop height between Simplified inputs and open Results so editing and retry remain reachable. Rationale: [IMPL-DECISION-07](../plan.html#impl-decision-07).

## Open concerns

- The required non-E2E suite retains the expected failure in `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject`. Pre-existing editable `pyproject.toml` and `poetry.lock` remain uncommitted as required by the [local-development and deployment gates](../tasks.md#gates); restore the matching published dependency during release preparation.
