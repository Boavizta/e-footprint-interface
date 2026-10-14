# Task 2 — Native export and saved-state guidance

Repository and reviewed implementation range: e-footprint-interface, `209e75c4b4c1d0253af9808763b33cf575baf9cb..77a19112c2643a003cd83d8e32998260a4549be6`.

## Review pointers

- `simplified_inputs/index.js` retains only dirty-Configure export interception. Delayed-save browser cases hold persistence while activating the native one-model link or pre-opened active/workspace menu link, then verify fresh exports after settlement; the disabled toggle never replays.
- Bootstrap can leave a pre-opened menu open when its native link is activated while the toggle is disabled. `ModelBuilderPage.download_active_model()` uses that open menu rather than toggling it closed.
- Architecture guidance includes Task 1's Results correction: external recomputation-bearing HTMX requests participate in deferred cleanup, which reapplies the closed layout after a late OOB refresh. Older specs, review guides and the interactive mockup now describe the scoped lock and native links.

## Open concerns

- The full Python gate fails only `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject`: the pre-existing editable `../e-footprint` dependency remains in `pyproject.toml`. Preserve the existing dependency/lockfile edits and restore the publishable dependency deliberately before merge.
- The runtime exposes neither this child's native thread ID nor its applied model. A truthful native usage binding could not be registered.
