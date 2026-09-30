# Task 10 — Focused timeseries and save-aware export

Repositories and implementation ranges:

- e-footprint-interface: `72aa659469990424cf091e766efc086a35223ebd..5463ada91d2d5c4bf33091d637cc8d70dbc2927e`.
- e-footprint: unchanged at `b03a48ce32afe61b7a92b081fa61741e0c515cff`.

## Review pointers

- [Focused panel adapter](../../../../model_builder/adapters/views/views_simplified_inputs.py) reuses the ordinary builder field/parser and selected-input mutation. The panel edits value only; provenance autosaves in the field's existing disclosure. HTTP-200 modal errors retain the panel draft.
- [Export and failure recovery](../../../../theme/static/scripts/simplified_inputs.js): capture mouse-press intent before blur disables Bootstrap controls; direct activation uses the click path. Continue only after successful mutation settlement. Active export checks its resident forms; workspace export checks both slots. Explicit discard reloads the affected field with zero settlement delay before initializing its accepted baseline.

## Design decisions

- [IMPL-DECISION-08: recover failed drafts before refreshing views](../plan.html#impl-decision-08).

## Open concerns

- The preserved, uncommitted editable dependency in `pyproject.toml`/`poetry.lock` triggers `tests/test_no_dev_dependency.py`. Restore the published dependency before merge, as required by [tasks.md](../tasks.md).
- The ordinary [weekly round-trip browser test](../../../../tests/e2e/test_weekly_pattern_builder.py) timed out once when reopening after Save in the initial focused run. It passed unchanged in subsequent focused/full runs; the intermittent cause remains unconfirmed.
- Unrelated packaging metadata: library [pyproject.toml](../../../../../e-footprint/pyproject.toml) includes `efootprint/builders/services/ecobenchmark_analysis/ecobenchmark_data_for_job_defaults.csv`, which exists in neither checkout nor wheel and has no current services consumer. No library cleanup was made here.
