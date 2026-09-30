# Task 6 — Guard workspace mutations

Repository and implementation range: `e-footprint-interface`, `0f6f64659d2bcaeff847d99dafd41dc9caeea347..0481af00923dfeab5c93a901ccf6a103905803aa`. The library is unchanged from `d85de9753db5abe3551ccaa87fce9f714124877d`.

## Review pointers

- `theme/static/scripts/model_builder_main.js` suppresses interaction and HTMX confirmation before HTMX can queue a second write, locks after payload capture, and uses the initiating XHR to await response settlement. Its button snapshots distinguish `data-disabled-by-htmx` from real constraint state when read requests overlap a mutation.
- Later controls declare `data-workspace-control` for guarded navigation/export and `data-workspace-editor` around editable fields. Shared state is `body[data-workspace-mutation="updating"]`; `workspace-mutation:started` and `workspace-mutation:finished` carry `{xhr, elt}`, with `successful` on finish. HTTP-200 `openModalDialog` responses report failure. Fetch writes use cancelable `workspace-mutation:begin` and matching `workspace-mutation:end` events.
- Card-order and Sankey diagram-deletion fetch writes participate in the same guard. `hammer_utils.js` keeps Results response targets attached through the interval after HTMX removes its request class but before settlement. Existing immediate-close/reopen Sankey and GenAI workflows cover this interaction alongside the new delayed-count browser case.
- The owning pattern is documented in `specs/architecture/rendering.html`; the existing AGENTS.md rendering pointer already routes to it.
- Saved-diagram reads and settings writes follow [IMPL-DECISION-04](../plan.html#impl-decision-04).

## Open concerns

- The preserved editable `pyproject.toml`/`poetry.lock` dependency still fails `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject`. This is the approved local-development exception; restore the published dependency and pass that guard during deployment/merge preparation.
