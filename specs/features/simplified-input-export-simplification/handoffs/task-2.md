# Task 2 — Verify native activation and downloaded state

Repository and implementation range: `e-footprint-interface`,
`1cdbbbe9d52948e1ea3bdd0c8c7da4c4a26c0365..c8d4309a`.

## Review pointers

- Physical press/release and native keyboard helpers distinguish blocked gestures from already-ready download helpers. Held inline saves settle without replay; fresh activations verify scalar values and provenance comments in downloaded files.
- Native invalid-input focus restoration can coexist with an opened two-model menu. Its next fresh link activation exports accepted state without saving the invalid input.
- Configure coverage keeps a clean menu open while guidance becomes dirty, making both blocked download links reachable through ordinary gestures. The existing Modeling round-trip also verifies export while its value draft remains unfinished.

## Open concerns

- `poetry run pytest tests --ignore=tests/e2e` fails only `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject`: the pre-existing editable `../e-footprint` dependency remains in `pyproject.toml`. Its owner must resolve the [publishable dependency prerequisite](../tasks.md#gates-and-prerequisites) before merging to main; the dependency files were preserved.
