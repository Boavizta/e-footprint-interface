# Task 7 — Build Configure and the shared workspace

Repository and implementation range: `e-footprint-interface`, `34b1e2e62eb1439f73f337affdb514ef98be0c28..ad20fb53ad606cb95ff0eac5cd3ebb7c14fb50b7`. Task 7 makes no library changes; its library implementation baseline remains `d85de9753db5abe3551ccaa87fce9f714124877d`.

## Review pointers

- `adapters/presenters/simplified_inputs.py` joins the authoritative catalog and definition with `FormContextBuilder.build_input_fields()`. The explicit generator include set implements [IMPL-DECISION-01](../plan.html#impl-decision-01), including optional empty quantities, while ordinary form output remains unchanged.
- `theme/static/scripts/simplified_inputs.js` keeps draft settings in form controls and only remembers base views by System ID. Internal focused-view GETs run after the ordinary side-panel discard helper and continue only after their matching XHR settles; cancelled navigation installs no continuation. Configure exits reuse the mutation guard's success contract, including HTTP-200 error-modal failures.
- `model_builder_main.js` distinguishes explicit stateless `data-workspace-read` navigation from editor inputs and exit controls. Its editor-form guard preserves reading during saves without inherited form-level `aria-disabled`. Shared Results/Sources controls participate in the navigation lock.
- JSON opening markers are consumed once in `views.render_model_builder()`; resident slot switches retain base-view memory. The shared `selection_controls.html` partial is the bookmark seam; the selected surface currently shows previews for later value-editing work.
- Owning patterns are promoted in `specs/architecture/workspace.html`, `forms-and-relationships.html`, and `rendering.html`.

## Open concerns

- The preserved editable `pyproject.toml`/`poetry.lock` dependency still fails `tests/test_no_dev_dependency.py::TestNoDevDependency::test_no_active_develop_true_in_pyproject`. This is the approved local-development exception; restore the published dependency and pass that guard during deployment/merge preparation.
