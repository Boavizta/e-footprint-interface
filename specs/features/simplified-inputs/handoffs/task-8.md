# Task 8 — Author selection beside Modeling inputs

Repository and final implementation range: `e-footprint-interface`, `5cfe21b02f228beb3272afafa4826112b48f3049..753c63d94baa46599c06e2e530247803a8ded214`. No library changes; library product baseline remains `d85de9753db5abe3551ccaa87fce9f714124877d` (the shared checkout's later experiment commit is not a product dependency change).

## Review pointers

- `adapters/forms/simplified_input_context.py`, `FormContextBuilder`, and the shared `bookmark.html`/`selection_controls.html` attach catalog eligibility and actual owner identity, including Storage inside Server. Disclosures open without toggling membership. Existing settings use Task 4 patches and inverse membership Undo; normal form close handlers react only to their own requests. Bookmark failure uses Task 7's `preserve_workspace` error seam.
- Sources uses compact context from the already hydrated `source_table()`, then lazily loads shared controls through `simplified_input_bookmark()`. The provenance row editor retains its raw-JSON boundary. The disclosure GET explicitly targets its own container. This approved seam is [IMPL-DECISION-06](../plan.html#impl-decision-06).
- Creation keeps settings in nameless provisional controls, serialized once at submission. Existing `dynamic_lists` metadata supplies candidate-controller requirements; previews release forced-only inclusion as candidates change and retain authored help. Successful hooks resolve the new object and nested Storage IDs before the single final persistence call. Cancellation and failed creation leave no persisted provisional definitions.
- Create/edit/delete require the catalog factory at every application entry point, including framework-free callers. `persist_structural_change()` reuses the configuration use case without a separate config save, completes selection, prunes removed owners and retained help, and restores request-local configuration on failed persistence. Delete confirmation runs the same removal operation on a separate inputs-only model to identify the actual cascade, excluding surviving shared children.
- Owning patterns are recorded in `specs/architecture/forms-and-relationships.html` and `persistence.html`. The supervisor can add an AGENTS pointer to the new bookmark/Sources lazy-rendering pattern when consolidating documentation.
- Task 9 seam: when a response updates surviving controls in place, apply their saved constraints after `workspace-mutation:finished`. The shared guard restores pre-request disabled states at settlement; bookmarks then reuse their current requirement labels to apply authoritative locks.

## Open concerns

- The preserved editable `pyproject.toml`/`poetry.lock` dependency fails `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject`. This is the approved local-development exception; restore the published dependency and pass that guard during deployment/merge preparation. Required affected gates otherwise completed; no unavailable checks or downstream task work remain.
