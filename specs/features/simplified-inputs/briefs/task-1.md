# Task 1 — Rename ready-made modelings to Examples

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [Examples](../plan.html#examples). Task: [overview](../tasks.md#task-1). Status: approved.
Implementation: easy — the rename map and Django rendering-template boundary are explicit.

## Start here

- Library [`efootprint/modeling_templates/__init__.py`](../../../../../e-footprint/efootprint/modeling_templates/__init__.py): public list/get/load API; [`how_to/registry.py`](../../../../../e-footprint/efootprint/modeling_templates/how_to/registry.py) and [`introductory/registry.py`](../../../../../e-footprint/efootprint/modeling_templates/introductory/registry.py): IDs and guide associations.
- Interface [`template_catalog_service.py`](../../../../model_builder/domain/services/template_catalog_service.py): library imports, intro resources and scratch ID; [`views_onboarding.py`](../../../../model_builder/adapters/views/views_onboarding.py): picker/deep-link entry points; [`template_picker_presenter.py`](../../../../model_builder/adapters/presenters/template_picker_presenter.py): UI context.
- Library [`pyproject.toml`](../../../../../e-footprint/pyproject.toml): packaged JSON globs; interface [`build_intro_templates.py`](../../../../scripts/build_intro_templates.py): generated introductory assets.

## Change along the code path

The library registries expose ready-made modeling IDs, load JSON resources and associate guides. Rename package/API/registry/authoring names together, preserving IDs and JSON content. The interface catalog imports the renamed API, presents Examples in the picker and Help/tour, and updates routes, deep links, selectors and authoring commands. Rename developer-facing tests and live docs, including library package-resource declarations. Keep Jinja/Django rendering `templates/` paths and historical archives untouched.

## Earlier tasks

None. This workstream is independent of simplified-input eligibility and can be reviewed separately. Interface testing must use the intended sibling library checkout; preserve the existing uncommitted interface dependency edits.

## Reuse

Keep current catalog grouping, `SCRATCH_ID`, `SystemImportService` loading and onboarding swap behavior. Existing [`tests/test_modeling_templates.py`](../../../../../e-footprint/tests/test_modeling_templates.py), interface [`test_template_catalog_service.py`](../../../../tests/integration/test_template_catalog_service.py), [`test_workspace_integration.py`](../../../../tests/integration/test_workspace_integration.py) and [`test_onboarding.py`](../../../../tests/e2e/test_onboarding.py) already check key paths.

## Invariants and traps

IDs, scenarios, results and guide associations stay byte/behavior compatible; no deprecated aliases. Search persisted and linked `template_id` consumers before renaming the key: library `HowToGuide.template_id` and `/template/<id>/` docs links exist today. Rename semantic catalog terms, not ordinary Django template terminology or old archive text.

## Validation

Run `poetry run pytest tests/test_modeling_examples.py` and `poetry run mkdocs build --strict` in e-footprint; test installed-package JSON resources after building/installing the package. In the interface run the renamed catalog/presenter tests, `poetry run pytest tests/integration/test_workspace_integration.py`, the focused onboarding E2E with a local server, and `npm run jest` for touched JS. Assert existing IDs load and example deep links resolve. Full suites remain a final gate.

## Out of scope

No simplified-input catalog, configuration schema or computation changes.

## Unverified

Complete caller inventory across docs, routes and JS remains to be done during the rename; use `rg 'modeling_templates|template_id|load_template|open-template|template_picker'` in both repos before editing.
