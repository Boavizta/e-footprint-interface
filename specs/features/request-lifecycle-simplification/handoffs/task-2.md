# Task 2 — Declarative field saves
Repositories and implementation ranges: `e-footprint-interface` `f0a0b38e..352e6a51`.

## Review pointers
- HTMX 2.0.6 runs a trigger only when its filter returns exactly `true`, so the editor uses `change[!!target.name]`. A bare `change[target.name]` never fires.
- Enter does not cause an implicit submit on the editor form, because the source editor's text and URL inputs block implicit submission. Enter commits through `change` alone, so the `submit` trigger rarely fires. E2E covers Enter followed by blur sending once.
- The user-data rule lives in `EditSimplifiedInputUseCase.execute`. It compares the attribute's object identity before and after `apply_input_edits`, and matches sources by id. It also applies to focused timeseries saves, which previously kept a hypothesis source because that form submits no provenance.
- `present_edited_input` sets `HX-Trigger-After-Settle` only when recomputing, so success responses without Results open carry no trigger header.
- The notice paragraph comes from the new `simplified_inputs/notice.html` template, which both `workspace.html` and the presenter render.
- `test_nested_storage_owner_and_omitted_metadata_are_preserved` in `tests/integration/test_simplified_inputs.py` now expects user data after a value change, as the agreed rule requires.

## Open concerns
- No eligible simplified input renders a multiple select today: `UsagePattern.devices` is the only list input and renders as a single select. A view test posting repeated keys and an in-browser HTMX encoding probe confirm the server join. No E2E multiple-select flow exists.
