# Step 3 — Surface SSOT in the interface: tasks

**Status:** Tasks — under review.
**Plan:** [`step-03-ssot-interface.md`](step-03-ssot-interface.md).
**Spec context:** [`01-single-source-of-truth.md`](01-single-source-of-truth.md), [`05-maintainability-and-build.md`](05-maintainability-and-build.md) (Step 3 row), [`99-implementation-plan.md`](99-implementation-plan.md) (Step 3).

**Prerequisite (verify before Task 1):** Step 2 has landed in e-footprint and `getattr(klass, "param_descriptions", {})` returns the full dict for every concrete class (including inherited entries from abstract bases). If not, the plan needs a merge step before this task list starts. See the Prerequisite section of the plan.

---

## Task 1 — Description provider foundation

**Status:** Done.

**Goal:** Land everything needed to call `EFOOTPRINT_DESCRIPTION_PROVIDER.<method>()` from anywhere in the interface, without yet wiring any call site. After this PR the singleton exists, is fully tested, and `class_ui_config.json` carries `interactions` for the four tour-relevant classes — but no user-visible behaviour changes.

**Files touched:**
- `domain/interfaces/description_provider.py` — **new**. `Protocol` with the nine class-scoped methods listed in the plan ("Architecture additions" §`DescriptionProvider` port). No Django imports.
- `adapters/ui_config/interface_placeholder_handlers.py` — **new**. `build_html_handlers(ui_tokens, mkdocs_base_url)` and `build_text_handlers(ui_tokens)` returning handler dicts compatible with `efootprint.utils.placeholder_resolver.resolve_placeholders`. Targets validated against `ALL_EFOOTPRINT_CLASSES_DICT`; HTML handlers escape variable parts via Django's `escape`.
- `adapters/ui_config/ui_token_registry.py` — **new**. `UI_TOKENS` dict. Initial entries cover only the tokens used by `class_ui_config.json` content written in this task (e.g. `infra_panel_add_button`).
- `adapters/ui_config/efootprint_description_provider.py` — **new**. `EfootprintDescriptionProvider` class implementing the port, with `_resolve_class` walking `ALL_EFOOTPRINT_CLASSES_DICT`, `_class_cache`, and the `field_tooltip` merge (`<library><br><br><interface>`, both placeholder-resolved, returns `SafeString`). Module-level `EFOOTPRINT_DESCRIPTION_PROVIDER` built with `build_html_handlers(UI_TOKENS, settings.MKDOCS_BASE_URL)` at import time.
- `adapters/ui_config/class_ui_config_provider.py` — extend with `get_interactions(class_name) -> str | None`.
- `adapters/ui_config/class_ui_config.json` — add `interactions` field for `ServerBase`, `JobBase`, `UsageJourney`, `UsagePattern` (authored on the abstract base where one exists). Tokens used here must be present in `UI_TOKENS`.
- `adapters/ui_config/field_ui_config.json` — migrate `parent_group_memberships`: keep `label` ("Add to parent groups") under that key; move any tooltip text to per-attr entries under `sub_group_counts` and `edge_device_counts`.
- `settings.py` — add `MKDOCS_BASE_URL` (env-overridable, sensible default).

**Tests added/changed:**
- `tests/unit_tests/adapters/ui_config/test_interface_placeholder_handlers.py` — **new**. Per plan §18:
  - Each HTML handler emits the expected tag for a known target.
  - Each text handler emits the expected plain label.
  - Unknown target for `class`, `param`, `calc`, `ui` raises `ValueError`; unknown `doc` slug renders without raising.
  - Variable parts with `<` / `>` are HTML-escaped in HTML handlers.
- `tests/unit_tests/adapters/ui_config/test_description_provider.py` — **new**. Per plan §17:
  - `field_tooltip` merge cases (both present, library-only, interface-only, neither → None; library text first, literal `<br><br>` separator).
  - `field_tooltip("EdgeDeviceGroup", "sub_group_counts")` and `("EdgeDeviceGroup", "edge_device_counts")` both return a merged tooltip.
  - `class_description` returns a placeholder-resolved string (no raw `{kind:target}` tokens survive).
  - `class_interactions` returns a placeholder-resolved string consuming `{ui:...}` tokens from the fixture.
  - Concrete subclass (`Server`) inherits `interactions` from abstract base (`ServerBase`) via MRO walk.
- `tests/unit_tests/adapters/ui_config/test_ui_config_consistency.py` — extend (file exists from Step 1) with the two check groups in plan §19:
  - Every `{ui:token}` in any `class_ui_config.json` `interactions` value has an entry in `UI_TOKENS`; every `UI_TOKENS` entry has a non-empty `display`.
  - Every `CLASS_UI_CONFIG` key is in `ALL_EFOOTPRINT_CLASSES_DICT` (concrete + abstract). Every concrete class in `MODELING_OBJECT_CLASSES_DICT` either has an entry, inherits one via MRO, or is in an explicit `EXCLUDED_CLASSES_FROM_UI_CONFIG` list co-located with the test.

**Acceptance:**
- `pytest tests/unit_tests/adapters/ui_config/` passes.
- `python manage.py check` passes (verifies the singleton builds at import time).
- `EFOOTPRINT_DESCRIPTION_PROVIDER` is importable; no call site consumes it yet, so user-visible behaviour is unchanged.

**Depends on:** none (assumes plan Prerequisite holds).

---

## Task 2 — Form-field tooltip rewiring

**Status:** Done.

**Goal:** Switch the three form call sites to `EFOOTPRINT_DESCRIPTION_PROVIDER.field_tooltip`, enable Bootstrap HTML-mode popovers on form-field info icons, and remove the unused `FieldUIConfigProvider.get_tooltip`. First user-visible delivery: every form field can carry the merged library + interface tooltip.

**Files touched:**
- `adapters/forms/form_field_generator.py` — at `:168` (`generate_select_multiple_field`) and `:207` (`generate_dynamic_form` loop), replace `field_config.get("tooltip", …)` with `EFOOTPRINT_DESCRIPTION_PROVIDER.field_tooltip(efootprint_class_str, attr_name)`. `efootprint_class_str` is already in scope; no new keyword arguments.
- `adapters/forms/form_context_builder.py` — in `_build_parent_group_membership_field` (`:160`), resolve the new object's web class to the right `(class_name="EdgeDeviceGroup", param=<sub_group_counts|edge_device_counts>)` pair and call `field_tooltip` with it.
- `adapters/ui_config/field_ui_config_provider.py` — remove `get_tooltip`. Keep `get_label` and `get_config`.
- `templates/model_builder/side_panels/components/tooltip.html` — accept optional `tooltip_html` flag (default `false`); emit `data-bs-html="true"` on the popover trigger when truthy.
- `templates/model_builder/side_panels/dynamic_form_fields/label.html` — pass `tooltip_html=True` when including `tooltip.html`. Other includes unchanged.

**Tests added/changed:**
- Existing form-rendering tests should still pass. If any test asserted on a specific tooltip string sourced from `field_ui_config.json`, update it to the merged form.
- No new test file; behaviour is covered indirectly by `test_description_provider.py` (Task 1).

**Acceptance:**
- `pytest tests/unit_tests/adapters/forms/` passes.
- Manually open Server and Job creation forms in a browser: numeric/text fields show info icons; popovers render the library description and (where present) interface tooltip separated by a paragraph break. No raw `{kind:target}` tokens visible. **Attach screenshots to the PR** to discharge the visual-noise risk from plan §Risks; if either form is objectively cluttered, file a follow-up rather than blocking.
- `FieldUIConfigProvider.get_tooltip` is no longer referenced anywhere (grep clean).

**Depends on:** Task 1.

---

## Task 3 — Help drawer and Add-button icon

**Status:** Done.

**Goal:** Wire the user-visible help drawer. Add the info-icon button next to each Add button in the canvas, route `/model_builder/open-help-drawer/<class_name>/` to a new view, render the multi-section partial. Also record the new `DescriptionProvider` pattern in `specs/architecture.md`.

**Files touched:**
- `adapters/views/views_help.py` — **new**. `open_help_drawer(request, class_name)` raises `Http404` for unknown `class_name`, otherwise builds the context dict via `EFOOTPRINT_DESCRIPTION_PROVIDER` and renders the partial.
- `model_builder/urls.py` — route `/open-help-drawer/<str:class_name>/` to the new view.
- `adapters/views/views_model_builder.py` (or wherever the canvas context is built) — for each Add button, call `EFOOTPRINT_DESCRIPTION_PROVIDER.class_description(class_name)` and `ClassUIConfigProvider.get_label(class_name)`; expose both in the template context.
- `templates/model_builder/help_drawer/class_help.html` — **new**. Sections per plan §"Help drawer": title, description, disambiguation, pitfalls, interactions, footer "Read more in the docs" → `{doc:objects/{class_name}}`. Each section rendered only when its provider value is non-empty. Uses `|safe` (resolver output is trusted).
- `templates/model_builder/components/add_object_button.html` — accept optional `class_name`, `class_label`, `class_description`. When `class_description` is truthy, render a sibling `<button>` (not nested) with `hx-get="/model_builder/open-help-drawer/{{ class_name }}/"`, `hx-target="#sidePanel"`, `aria-label="About {{ class_label }}"`. Wrap Add button + help icon in a flex row.
- `templates/model_builder/components/model_canvas_content.html` — pass `class_name`, `class_label`, `class_description` to each `add_object_button.html` include.
- `specs/architecture.md` — short paragraph on the `DescriptionProvider` port + pointer to `specs/features/tutorial-and-documentation/01-single-source-of-truth.md`.

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_help.py` — **new**. Per plan §20:
  - `GET /model_builder/open-help-drawer/Server/` → 200, contains expected class label, no raw `{kind:target}` tokens in body.
  - GET on a class with no `interactions` field → 200 with "Interactions" section absent.
  - `GET /model_builder/open-help-drawer/NotARealClass/` → 404.

**Acceptance:**
- `pytest tests/unit_tests/adapters/views/test_views_help.py` passes.
- Manually open the canvas in a browser: each Add button has a sibling help icon; clicking it slides in the side panel with the populated sections and a docs link. Cards on the canvas are unchanged.
- Tab focus on the help icon announces "About <class label>".

**Depends on:** Task 1. Independent of Task 2 (different files, different surface).

---

## Ordering rationale

Task 1 lands the entire backing infrastructure — port, adapter, handlers, registry, config extensions, and all unit tests — behind no user-visible change. It's the largest PR but the changes are tightly coupled (the protocol exists to serve the adapter; the handlers are only consumed by the adapter; the consistency tests guard the JSON edits made alongside), so splitting them just creates artificial review boundaries with no behavioural pause point.

Tasks 2 and 3 are the two user-visible deliveries. They share no files and could in principle land in parallel; sequencing 2 → 3 keeps the user-visible surface area changing one step at a time and matches the order in which the plan introduces them.
