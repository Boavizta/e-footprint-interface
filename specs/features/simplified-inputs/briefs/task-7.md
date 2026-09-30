# Task 7 — Build Configure and the shared workspace

Written 2026-09-30 against e-footprint `96ea0d39` and e-footprint-interface `fe6c04e5`.
Plan: [grouped workspace](../plan.html#workspace), [configuration save](../plan.html#configuration-save), [model context](../plan.html#model-context). Task: [overview](../tasks.md#task-7). Status: under review.
Implementation: standard — combine Task 3/4 catalog and save APIs with `side_panel_utils.js`'s deferred-action pattern and resident-canvas switching.

## Start here

- [`model_builder_main.html`](../../../../model_builder/templates/model_builder/model_builder_main.html): resident model canvas and shared shell; [`views.render_model_builder()`](../../../../model_builder/adapters/views/views.py): initial page context and result chrome.
- [`FormContextBuilder`](../../../../model_builder/adapters/forms/form_context_builder.py): existing creation/edit field dictionaries; [`generate_dynamic_form()`](../../../../model_builder/adapters/forms/form_field_generator.py): labels, widgets and ordering.
- [`model_comparison.js`](../../../../theme/static/scripts/model_comparison.js): per-slot switching/Compare; [`side_panel_utils.js`](../../../../theme/static/scripts/side_panel_utils.js): existing unsaved-panel guard.

## Change along the code path

Add thin simplified-input mode/config endpoints and a presenter that joins the Task 3 catalog, Task 4 definition and existing form contexts into type → owner → field groups. Build shared workspace/navigation/object/field partials and SCSS; Configure shows all eligible fields with current-value previews and `selection_controls.html`, while the selected view initially renders saved included fields. Add System-ID/owner/attribute DOM identity and grouped object counts. Browser Configure draft remains in form controls: dependent links auto-include/lock required fields, selected-object filtering changes Navigation/content only, Clear confirms and clears field settings, and Save submits the whole definition to Task 4. A form-level dirty flag gates every exit with Save/Discard/Stay; Save continues only on success. Add toolbar mode switching, per-System-ID last base view, fresh server rendering on Modeling → Simplified inputs, and first-open JSON defaults. Configure starts fresh at top/filter-off each time.

## Earlier tasks

Task 3 supplies catalog/closure; Task 4 supplies persisted config; Task 6 guards mutations. Task 8 will wrap `selection_controls.html` in bookmarks, and Task 9 will turn the selected view's previews into editors.

## Reuse

Keep existing form field dictionaries as rendering context, not a second schema. Use `SessionWorkspaceRepository(request.session).active_repository()` in views. Preserve shared navbar, workspace tabs, normal file controls and Results/Sources access. Configure may use a complete-view response on Save; inline saves later use targeted responses.

## Invariants and traps

Scope every DOM target to System ID plus true owner ID plus attribute; resident canvases can coexist. A filter that hides the last selected object moves keyboard focus to another visible object or the filter. Deselecting keeps help; Clear removes it but keeps title/guidance. Do not copy form state into a JS definition or park Configure drafts/layout. Configure is not a remembered base view. Import opening defaults apply once on file load, not on every model switch.

## Validation

Run new presenter/unit tests, `npm run jest -- --runInBand js_tests/simplified_inputs.test.js`, and focused browser flows in `tests/e2e/test_simplified_inputs.py` with a local server. Assert grouped labels/counts, filtering and focus, recursive draft locks, Save/Discard/Stay including failed save, fresh Configure entry, independent per-model base view, active Results/Sources controls, wide/compact layout and fresh render after Modeling changes. Run existing `tests/e2e/test_model_comparison.py` for resident-canvas regressions.

## Out of scope

No bookmark autosave, simple value autosave or timeseries editor. The selected surface can show current-value previews until Task 9.

## Form-context seam

`FormContextBuilder.build_creation_context()` and `build_edition_context()` dispatch to the object's configured strategy, then add relationship sections; they already return template-ready field dictionaries. The presenter should consume those dictionaries for field wording and widgets, with representative object-family rendering checks during implementation rather than a new field metadata source.
