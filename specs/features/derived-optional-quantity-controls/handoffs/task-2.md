# Task 2 — Render and save derived optional controls

Repositories and implementation ranges: interface `fbd20fac17e4e1169099db560e603a30dc64914c..44584ccf`; separately authorized validation-fixture cleanup `44584ccf..7583fa42`. Library contract consumed from reviewed `baaff4adb9dcaf05f6d8a609ffb554710588a9d4`; this task changes no library files.

## Review pointers

- `generate_dynamic_form()` selects optional quantity partials from constructor unions and resolves empty units with `get_expected_input_unit()`. Both editor surfaces wrap their numeric partials with “Leave unset”; the shared controller clears, hides and requires the number, and simplified edits save an empty switch immediately.
- Generic optional fields can have no conditional controller. Empty entries in the rendered controller list are excluded so an absent controller cannot force empty or lock the switch.
- The separate fixture cleanup addresses six failures reproduced on baseline `fbd20fac`: four retired EcoLogits model fixtures, catalog-only drift in the external-API dynamic-data snapshot, and obsolete source disclosure copy in the focused-timeseries response assertion.

## Open concerns

- The committed PyPI dependency remains `efootprint = "25.0.0"`. Release the reviewed library unit helper and annotations, then update the interface dependency before deployment. Local verification uses that reviewed checkout; pre-existing editable `pyproject.toml` and `poetry.lock` bytes have been restored and are excluded from commits.
