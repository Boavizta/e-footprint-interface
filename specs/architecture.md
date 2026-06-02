# Architecture — e-footprint-interface

## Clean Architecture layout

The codebase follows Clean Architecture principles, with strict dependency direction enforced by constitution §1.1. Inner layers never import outer layers.

```
model_builder/
├── domain/                    # Business logic, no Django dependencies
│   ├── entities/              # Web wrappers around efootprint objects
│   │   ├── web_core/          # ModelWeb, ServerWeb, JobWeb, EdgeDeviceGroupWeb, etc.
│   │   ├── web_builders/      # Builder-specific entities (ExternalAPIWeb, etc.)
│   │   ├── web_abstract_modeling_classes/  # Base classes (ModelingObjectWeb)
│   │   └── efootprint_extensions/          # extension point for downstream consumers (currently empty)
│   ├── services/              # EmissionsCalculationService, ObjectLinkingService, EditService, SystemValidationService
│   ├── interfaces/            # Repository interfaces (ISystemRepository)
│   ├── object_factory.py      # Object creation/editing logic
│   ├── all_efootprint_classes.py
│   └── efootprint_to_web_mapping.py
├── application/
│   └── use_cases/             # CreateObjectUseCase, EditObjectUseCase, DeleteObjectUseCase
├── adapters/
│   ├── views/                 # HTTP views (thin adapters)
│   │   ├── views.py
│   │   ├── views_creation.py
│   │   ├── views_edition.py
│   │   ├── views_dict_mutation.py
│   │   └── sankey_views.py
│   ├── presenters/            # HtmxPresenter
│   ├── repositories/          # SessionSystemRepository, InMemorySystemRepository
│   ├── forms/                 # form_data_parser.py, form_field_generator.py
│   └── ui_config/             # UI configuration providers
├── templates/                 # Django templates
├── version_upgrade_handlers.py  # interface_config schema migrations
└── domain/reference_data/     # JSON configs (default data) + modeling_templates/ (see "Modeling templates")
```

### Request lifecycle

1. User action → View (adapter).
2. View maps request → Use Case input.
3. Use Case orchestrates domain logic via `ModelWeb` and domain services.
4. Presenter formats output → HTTP response with HTMX triggers.
5. View returns response (full page or partial DOM swap).

## Core classes

### ModelWeb — the central orchestrator

`model_builder/domain/entities/web_core/model_web.py`. `ModelWeb` is the central web wrapper around the e-footprint domain model:

- Deserializes session `system_data` via `efootprint.api_utils.json_to_system`.
- Wraps the resulting `System` into web objects (`wrap_efootprint_object`).
- Exposes typed accessors: `servers`, `services`, `jobs`, `usage_patterns`, `usage_journeys`, `edge_device_groups`, `ungrouped_edge_devices`, etc.
- Serializes back to JSON with or without calculated attributes via `to_json()`.
- Persists to cache via `persist_to_cache()` (serializes system + merges `interface_config` via the repository).
- Maintains a flat index of objects (`flat_efootprint_objs_dict`) for quick lookups.

`ModelWeb` does **not** see or touch `interface_config`. The repository owns that (constitution §1.3, library is the truth).

### Use cases

`model_builder/application/use_cases/`:

- **`CreateObjectUseCase`** — object creation with hooks (`pre_create`, `post_create`).
- **`EditObjectUseCase`** — object editing with `pre_edit` hook.
- **`DeleteObjectUseCase`** — object deletion with `can_delete`, `pre_delete` hooks.

### Domain services

`model_builder/domain/services/`:

- **`ObjectLinkingService`** — parent-child linking logic.
- **`EditService`** — handles object editing with cascade cleanup.
- **`SystemValidationService`** — validates system completeness (drives the "Get results" button state).
- **`EmissionsCalculationService`** — calculates daily emissions timeseries.

### Web wrappers

Package of web wrappers around e-footprint domain classes. Each provides template-friendly properties and form-generation logic.

Notable:

- **`EdgeDeviceGroupWeb`** — uses `attributes_to_skip_in_forms` to exclude dict attributes from standard form generation (they use a dedicated `dict_count` widget instead).
- **`EdgeGroupMemberMixin`** — shared behavior for objects that can be members of edge device groups (pre-delete hooks to remove dict references before deletion).

### Adapters

- **`adapters/repositories/session_system_repository.py`** — loads/saves system from Django session. Holds `interface_config` in RAM and merges it on `save_data()`.
- **`adapters/forms/form_data_parser.py`** — parses HTTP form data before passing to use cases. Parsing happens here, never in domain — the domain receives parsed dicts.
- **`adapters/forms/form_field_generator.py`** — form field generation utilities. Includes `generate_select_multiple_field()` as a standalone reusable helper.
- **`adapters/presenters/htmx_presenter.py`** — formats use case outputs as HTMX responses.
- **`adapters/ui_config/`** — provides UI configuration (class labels, field metadata).

### DescriptionProvider port

Library-side SSOT metadata (`param_descriptions`, class docstrings, `disambiguation`, `pitfalls`) reaches templates through the `DescriptionProvider` port in `domain/interfaces/description_provider.py`. The only implementation, `EfootprintDescriptionProvider` (`adapters/ui_config/efootprint_description_provider.py`), merges library text with interface-side overlays from `class_ui_config.json` (`interactions`) and `field_ui_config.json` (per-field tooltips), then runs `{kind:target}` placeholders through `efootprint.utils.placeholder_resolver` with the interface's HTML handlers (`interface_placeholder_handlers.py`). The module-level `EFOOTPRINT_DESCRIPTION_PROVIDER` singleton is the entry point; templates only ever see `SafeString` output with placeholders already resolved. See `specs/features/tutorial-and-documentation/01-single-source-of-truth.md` for the broader rationale.

### Object factory

`model_builder/domain/object_factory.py`:

- `create_efootprint_obj_from_parsed_data()` — creates efootprint objects from pre-parsed form data. Supports both list-based (`List[ChildType]`) and dict-based (`ExplainableObjectDict`) constructor parameters.
- `edit_object_from_parsed_data()` — handles object updates via `ModelingUpdate`.
- `_apply_metadata(obj, parsed_value, available_sources, pending_sources)` — sets `source`, `confidence`, and `comment` on any `ExplainableObject` from the parsed form dict. Called per-attribute in both create and edit paths. Source resolution order: (1) `available_sources` matched by id (model's existing sources), (2) `pending_sources` matched by id (sources just minted earlier in the same submission), (3) mint a new `Source(name, link, id=submitted_id)` and stash it in `pending_sources`. `pending_sources` is a per-submission dict shared across all calls within one create/edit invocation — this lets two fields submitting the same client-generated id resolve to the same `Source` instance (same-form cross-field source sharing). Confidence carries whatever the form submitted (`None` if absent or invalid); the client clears `__confidence` on value change, so the server simply honors what it receives. `available_sources` is pre-computed once per request and passed in to avoid O(n×m) recomputation inside the per-attribute loop.

### Extension mechanism

The library exposes `ExplainableObject.register_subclass(matcher)` so that JSON files can round-trip back into typed Python objects.

**For e-footprint-interface development, register new subclasses inside the e-footprint package itself** (typically `efootprint/builders/timeseries/`). Otherwise the library would no longer be able to load JSON files generated by the interface. This is why the form-driven extensions originally written here — `ExplainableHourlyQuantitiesFromFormInputs` and `ExplainableRecurrentQuantitiesFromConstant` — now live under `e-footprint/efootprint/builders/timeseries/`.

`model_builder/domain/entities/efootprint_extensions/` is preserved as an extension point for downstream consumers (e.g. a company building a custom interface on top of e-footprint with proprietary subclasses that should not bleed into the public library). It is currently empty in our codebase; this case has not appeared in practice yet. When in doubt, put new subclasses in e-footprint.

## Creation prerequisites and disabled UX

Web classes that have prerequisites for creation define a `can_create(cls, model_web) -> bool` classmethod. Returns `True` when allowed, `False` when blocked. `get_creation_prerequisites` delegates to `can_create` and raises a generic error if blocked (last line of defense — the UI should have disabled the button before this point).

`ModelWeb._build_creation_constraints()` iterates all registered web classes, deduplicates by MRO defining class, and returns a dict keyed by the defining class name (`"JobWeb"`, `"UsagePatternWeb"`, etc.), plus a `"__results__"` sentinel entry from `SystemValidationService`. Values are `{"enabled": bool, "disabled": bool}` for class-based entries; `__results__` additionally carries `reason` (live validation-error text). Static disabled-button tooltips live in `CONSTRAINT_MESSAGES` and are resolved at render time via the `constraint_tooltip` template filter — the domain never imports from adapters. This dict is stored at `model_web.creation_constraints` and recomputed after every mutation.

**Constraint diff on mutation.** `ModelingObjectWeb.create_side_effects`, `edit_side_effects`, and `delete_side_effects` are instance methods. They read `self.model_web` and delegate to the shared `self._recompute_state_and_emit_oob_regions()` helper, which diffs old vs. new constraints and, when any flip:

- Emits two OOB regions: `model_canvas` (re-renders `#model-canva` contents via `innerHTML`) and `results_buttons` (updates `#btn-open-panel-result` and `#show-results-toolbar-btn` via `outerHTML`).
- Sets `model_web.constraint_changes` to a list of `(key, "locked"|"unlocked")` tuples.

Subclasses that override a `*_side_effects` hook (e.g. `EdgeDeviceGroupWeb`) must call `super()` first and then extend the returned region list, or the diff-based regions will be lost.

**Edge-paradigm toggle.** The same helper also diffs `ModelWeb.has_edge_objects` (True iff any class in `model_builder/domain/modeling_paradigm.py::EDGE_EFOOTPRINT_CLASS_NAMES` has at least one instance). When that boolean flips — first edge object created or last one deleted — it appends an `edge_modeling_toggle` OOB region whose renderer (`oob_regions.py`) re-renders the navbar partial via `hx-swap-oob="outerHTML:#edge-modeling-toggle-wrapper"`, latching/unlatching the toolbar's switch. The last-emitted value lives on `model_web._last_emitted_has_edge_objects`, mirroring how `creation_constraints` is cached.

**Toast notifications and tooltips.** `HtmxPresenter._constraint_toast_messages()` reads `model_web.constraint_changes`, looks up messages in `adapters/ui_config/constraint_messages.py` (`CONSTRAINT_MESSAGES`), and passes them as `constraint_messages` in the `displayToastAndHighlightObjects` event. Each `CONSTRAINT_MESSAGES` entry has three keys: `"unlocked"`, `"locked"`, `"tooltip"`. The keyset of `CONSTRAINT_MESSAGES` must match the keyset of `creation_constraints`; `tests/unit_tests/adapters/ui_config/test_constraint_messages_consistency.py` enforces this invariant.

**Template integration.** `add_object_button.html` and `add_child_button.html` accept `disabled` and `disabled_reason`. Disabled state renders a non-interactive button with a Bootstrap tooltip. `child_sections` on `ModelingObjectWeb` exposes `constraint_key` (the defining-class name) for each section, and templates resolve the tooltip copy with `{{ section.constraint_key|constraint_tooltip }}`. The `__results__` entry is looked up in templates via the generic `get_item` filter (Django rejects the `__` prefix in dot syntax). For the Results buttons, the disabled-state tooltip uses the live `reason` string rather than the static copy, because validation errors are dynamic.

## Timeseries handling

Timeseries generation is handled by `ExplainableObject` subclasses registered to the base timeseries types:

### `ExplainableHourlyQuantitiesFromFormInputs`

- **Purpose:** generate hourly timeseries from simple form inputs (start date, duration, initial volume, growth rate).
- **Registration:** matches JSON with `"form_inputs"` key containing `"type": "growth_based"`.
- **Storage:** stores both form inputs (for editing) AND computed compressed timeseries.
- **Lazy evaluation:** computes timeseries only when `.value` is accessed; caches result.

### `ExplainableRecurrentQuantitiesFromConstant`

- **Purpose:** generate 168-element recurrent array from a single constant value.
- **Registration:** matches JSON with `"constant_value"` and `"constant_unit"` keys.
- **Storage:** stores the constant value (for editing) AND computed recurring_values array.
- **Lazy evaluation:** generates 168-element array when `.value` accessed; caches result.

## Persistence and `interface_config`

The repository layer manages two concerns:

1. **System data** — the efootprint model (serialized via `ModelWeb.to_json()`).
2. **Interface config** — UI-only state (e.g., Sankey diagram settings) stored as a top-level `interface_config` key in the cached JSON.

**Key principle:** `ModelWeb` stays pure efootprint domain — it never sees or touches `interface_config`. The repository owns it.

- `SessionSystemRepository` holds `_interface_config` in RAM, populated lazily on first read.
- `save_data()` merges `_interface_config` and `efootprint_interface_version` into the JSON before writing.
- `persist_to_cache()` on `ModelWeb` calls `to_json()` then `repository.save_data()`.
- `version_upgrade_handlers.py` provides migration infrastructure for `interface_config` schema changes across versions.

The `interface_config` is included in JSON exports (download) and restored on imports (upload), enabling Sankey settings to survive export/import cycles.

Import recomputation payloads must be assembled from `efootprint.api_utils.system_to_json.system_to_json()` fragments (the connected `System` plus any orphaned objects) rather than hand-serializing objects in the interface. This keeps object serialization and top-level `Sources` hoisting owned by e-footprint and prevents dangling source references after calculated attributes are recomputed.

## Relationship types

### List-based children (standard pattern)

Most parent-child relationships use `List[ChildType]` constructor parameters. Managed via:

- `select_multiple` widget in forms (add/remove by selecting from available objects).
- `edit_object` endpoint for mutations.
- `child_sections` property on `ModelingObjectWeb` provides structured access with `linkable_existing_count`.

### Dict-based relationships (`ExplainableObjectDict`)

Edge device groups use dict-based relationships where each entry is `{object: count}`:

- `EdgeDeviceGroup.sub_group_counts` — maps sub-groups to counts.
- `EdgeDeviceGroup.edge_device_counts` — maps devices to counts.

These require dedicated mutation endpoints in `views_dict_mutation.py`:

- `POST /update-dict-count/<parent_id>/<key_id>/` — update count.
- `POST /unlink-dict-entry/<parent_id>/<key_id>/` — remove entry.
- `POST /link-dict-entry/<parent_id>/<key_id>/` — add entry with count=1.

The `dict_count` form widget (`dict_count.html` + `dict_count.js`) provides per-entry count inputs. Cycle prevention for nested groups is enforced at the view layer by excluding the group itself and all its ancestors from the sub-group picker.

### "Link existing" flow

When linkable objects of a child type exist, an "Link existing" button appears alongside "Add new" in object cards. It opens a focused side panel (`open_link_existing_panel` in `views_edition.py`) showing only a `select_multiple` field, submitting to the existing `edit_object` endpoint. The `generate_select_multiple_field()` function in `form_field_generator.py` is a standalone reusable helper for building this widget.

## Composite form field metadata

Composite form widgets (e.g., `hourly_quantities_from_growth`) can carry per-class metadata for their subfields. Instead of template conditionals like `{% if object_type == "UsagePattern" %}`, declare a class attribute on the web wrapper:

```python
# On the web wrapper base class — provides safe defaults
hourly_quantities_from_growth_ui_config = {"initial_volume": {"label": "Initial volume", "tooltip": None}}

# On a specific subclass — overrides with class-specific wording
hourly_quantities_from_growth_ui_config = {"initial_volume": {"label": "Custom label", "tooltip": "Help text"}}
```

The form generator injects this as `field["subfields"]` so templates can render it generically.

## Rendering in the web context

- **Session-driven state.** The current system model is stored in Django session as `system_data` (JSON). Each request reconstructs the domain system via `ModelWeb(repository)`.
- **HTMX partials.** Most UI actions trigger small HTTP requests that replace DOM snippets using templates under `model_builder/templates/model_builder/`.
- **Metadata-only edits.** Parsed source metadata submissions (`_metadata_only`) are persisted through the normal
  edit use case, but the output sets `refresh_cards=False` so `HtmxPresenter` skips object-card OOB swaps;
  source-table JS updates already-known metadata display locally instead of reloading the full source table.
- **Templates.**
  - Base layouts in `theme/templates/` (e.g., `base.html`, `navbar.html`) with Bootstrap styling.
  - Feature templates and partials under `model_builder/templates/model_builder/`.
  - Save button is centralized in `side_panel_structure.html` as a `{% block save_button %}` default.
- **Help drawer is an independent overlay layer.** `#helpDrawer` is a sibling of `#sidePanel` with a higher z-index, driven by `help_drawer_utils.js` (IIFE + `data-action` dispatch — see `conventions.md` → JavaScript); it never touches the side panel. Every entry point — the canvas `?` button and `{class:X}` placeholders rendered by `handle_class` — is a `<button data-action="open-help-drawer" data-help-class="X">`; the module's delegated listener swaps `#helpDrawer` via `htmx.ajax`, so the button works even when Bootstrap injects it into a popover subtree HTMX never processed.
- **Frontend assets.**
  - `theme/static/scripts/` includes small utilities (loading bars, charts, leader lines).
  - CSS/SCSS in `theme/static/scss` and compiled CSS in `theme/static/css`.

### Layout model

The page layout uses **flexbox** (`flex: 1 1 0; min-height: 0;` on nested containers) — not computed CSS variable heights. The browser auto-distributes remaining space. **Do not reintroduce height variables** like `--model-height` or `--model-canva-calculated-height`; they were intentionally removed. Hiding/showing elements (navbar, toolbar) automatically reclaims/consumes space with zero JS height manipulation.

### HTMX accordion state preservation

When OOB card swaps re-render a card, accordion open/close state is preserved automatically via `restoreAccordionStateInFragment` in `model_builder_main.js`. This handler intercepts `htmx:beforeSwap`, snapshots all currently-open accordions, modifies the incoming HTML to restore their state, then lets HTMX insert the corrected fragment. Any new OOB card swap benefits from this — no per-feature wiring needed. Do not add competing accordion-restore logic.

### Leaderline target resolution

Leaderlines use a "deepest visible anchor" pattern for target-side resolution: if the target element is hidden inside a collapsed accordion, the line ends on the nearest visible `.leaderline-anchor` ancestor instead. Lines are rebuilt broadly on `shown.bs.collapse` / `hidden.bs.collapse` events. Source-side semantics are unchanged.

### Truncated-text tooltip pattern

Use the `components/truncating_text.html` partial for any text that should ellipsize and reveal the full string on hover. It emits a `<p>` with `.truncated-text-tooltip` + `text-truncate min-w-0` + Bootstrap tooltip attrs; `initTruncatedTextTooltips` in `model_builder_main.js` (re-run on `htmx:afterSettle`) only shows the tooltip when the text is actually truncated. Params: `visible_text`, optional `full_text` (defaults to visible), `extra_classes`. Caveat: flex ancestors must allow the element to shrink (`min-w-0` along the chain) or truncation won't trigger. For compact labels (e.g. `add_child_button.html` with `compact=True` inside labeled sections), skip the partial and emit a plain `<p>` — the surrounding section header already names the type.

## Adding a new modeling object class

You should NOT need to create extension classes — use base efootprint classes directly.

If you need to add a base efootprint class to the web interface:

1. Ensure it's in `efootprint.all_classes_in_order.ALL_EFOOTPRINT_CLASSES`.
2. Add an entry to `model_builder/reference_data/form_type_object.json`.
3. Optionally create a web wrapper in `domain/entities/web_core/` and add to `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`.
4. Run `tests/tests_structure.py` as a script to auto-generate form field entries.

## Adding a new timeseries generation method

To add a new way to generate timeseries (e.g., from uploaded CSV):

1. In **e-footprint**, create a new `ExplainableObject` subclass under `efootprint/builders/timeseries/` (so JSON round-trips in both repos — see "Extension mechanism" above).
2. Register with `@ExplainableHourlyQuantities.register_subclass(lambda d: ...)` using a unique JSON key.
3. Implement `from_json_dict()`, `to_json()`, `__init__()`, and lazy `@property value`.
4. In **e-footprint-interface**, create a form template in `side_panels/dynamic_form_fields/`.
5. Update `generate_dynamic_form()` to detect your new type.

## Modeling templates

`model_builder/domain/reference_data/modeling_templates/` holds the interface template registries shown in the first-run template picker:

- `introductory/registry.py` — the `IntroTemplate` dataclass (mirrors the library's `HowToTemplate`: `id`, `name`, `description`, `icon`, `showcased_concepts`, `json_path`, `category`), the `INTRO_TEMPLATES` tuple, and a closed `CONCEPTS` mapping for picker chips that map to no single efootprint class. `showcased_concepts` tokens are either `{class:X}` (validated against `ALL_EFOOTPRINT_CLASSES_DICT`, like the SSOT placeholder handlers) or `CONCEPTS` keys; `resolve_concept_token` validates them and the registry consistency test fails on drift. The registry imports only the library (no adapter imports — Clean Architecture).
- `introductory/registry.py` points `ecommerce` at the library-owned `efootprint.modeling_templates.introductory` JSON so docs and interface share one web/database scenario; `introductory/{ai_chatbot,iot_industrial}.json` remain interface-owned serialized pure `System` snapshots (no UI metadata inside). The IoT snapshot contains edge objects so the Step 5 edge toggle latches on load.
- `__init__.py` re-exports the introductory registry; **how-to templates are not re-exported here** — they are consumed at runtime from the library's `efootprint.modeling_templates.list_how_to_templates()`.

The interface-owned JSONs are **derived artifacts**: the source of truth is the Python `build_system()` constructors under `scripts/intro_template_scenarios/`, regenerated via `python -m scripts.build_intro_templates` (the build flips `_use_name_as_id` before importing efootprint so ids are readable and stable, mirroring the library's how-to `_authoring` package). Re-run it after a library serialization-schema change. Regenerate the e-commerce JSON from the library with `python -m efootprint.modeling_templates.introductory._authoring.ecommerce`. Template constructors must use `efootprint.builders.timeseries` builders for input hourly/recurrent timeseries so those inputs stay editable after load.

The shipped `default_system_data.json` is a truly empty `System` (no journeys/servers/patterns) — the "Start from scratch" baseline. Tests needing a pre-existing journey use the `default_system_repository_with_journey` (integration) / `seeded_journey_model_builder` (e2e) fixtures instead of relying on default seeding.

### First-run template picker

`domain/services/template_catalog_service.py` merges the introductory registry with the library's how-to templates (consumed at runtime via `efootprint.modeling_templates.list_how_to_templates` / `get_template`) plus a `scratch` sentinel into ordered `CatalogGroup`s, and resolves a picker `template_id` to its raw serialized `System` dict (`get_template_system_data`, raising `KeyError` for unknown ids). `domain/services/empty_model.py::is_empty_model` decides whether the picker is shown: a model is empty when its only top-level efootprint *class* key is `System` (keying off `ALL_EFOOTPRINT_CLASSES_DICT` membership, so new metadata keys never read as content). `adapters/presenters/template_picker_presenter.py` enriches catalog entries with display chips (resolving `{class:X}`/`CONCEPTS` tokens via `CLASS_UI_CONFIG`) and mkdocs deep-link URLs.

`views.py::model_builder_main` renders the canvas with the picker overlay whenever `is_empty_model` holds: `onboarding/template_picker.html` is *included* into `#model-builder-page` at render time (a child of the canvas container, not a separate swap). The picker's own actions, by contrast, are HTMX swaps that replace `#main-content-block` (the full builder): `load_system_into_session`/`render_model_builder` are the shared helpers behind reset, template loading, and empty-model init. `adapters/views/views_onboarding.py` adds `open_template_picker` (re-render the builder with the picker forced on — used by the toolbar Help menu and the home "Browse templates" CTA) and `load_template` (load the chosen/scratch/how-to system, land on the canvas). `views.py::reset_model` discards the session model back to the empty `scratch` baseline and re-opens the picker. `load_template` and `reset_model` are `@require_POST` (they mutate the session model, so must not be GET-reachable); the picker cards and the toolbar reset button confirm before discarding a non-empty model. That confirmation is *not* a server-rendered `hx-confirm` (the toolbar is rendered once and outlives the partial swaps that add/remove objects, so a baked-in attribute goes stale): the buttons carry `data-confirm-when-model-not-empty="<question>"` and a single body-delegated `htmx:confirm` listener in `model_builder_main.js` prompts at click time, reading emptiness live from the DOM (`.model-builder-card`). All three re-render the full builder into `#main-content-block` so the session model is preserved with the app chrome intact. The picker is a welcome overlay: `onboarding_first_run.js` removes it when a side panel or help drawer opens (so toolbar actions like Import are never blocked) and records the `efootprint_onboarding_seen` localStorage flag, emitting `onboarding:first-run` for the guided tour (Step 6 Task 3) to auto-run once.

**Dead-state recovery.** A session model that fails to deserialize would 500 `model_builder_main` at the `ModelWeb` load, stranding the user (the reset button lives on that very page). The view wraps the load in a `try/except` and falls back to `exception_handling.render_recovery_page` (`templates/model_builder/recovery.html`, a self-contained page intentionally decoupled from `model_web`) offering: download the raw session JSON (`download_raw_json`, served verbatim without rebuilding the model), reset, and a prefilled GitHub bug report. `RAISE_EXCEPTIONS=1` still bubbles the raw traceback (same convention as `upload_json`). The same page is reachable read-only at `GET /model_builder/recover/` (the always-available escape hatch that replaced the removed `GET /reboot`) and is rendered by the project-wide `handler500` (`e_footprint_interface/views.py::server_error`) for any unhandled 500 in production.

### Guided tour

The first-run **guided tour** is a thin, non-blocking wrapper (`theme/static/scripts/tour.js`, IIFE + `data-action="replay-tour"` dispatch) around **driver.js** (vendored as `external_librairies/driver.iife.js`, which exposes `window.driver.js.driver`; CSS at `css/driver.css`). The tour's *words live only server-side*: `adapters/ui_config/tour_steps.py::build_tour_steps(is_blank)` authors the map/order/help-discoverability copy with `{kind:target}` placeholders, resolves them through `EFOOTPRINT_DESCRIPTION_PROVIDER.resolve_text` (same SSOT resolver as the rest of the UI — no domain-concept prose is duplicated), and `render_model_builder` renders the result into `onboarding/tour_steps.html` as a `<script type="application/json" id="tour-steps-data">`. `tour.js` reads that payload and drives driver.js; steps anchor on stable `data-tour-target` attributes (`usage-journeys` / `infrastructure` / `usage-patterns` / `results` / `help-menu`) so selectors don't couple to incidental markup. Two flavors share content: the `blank` flavor (empty model) appends a "create a usage journey" first-action step. The help step opens the help drawer via help_drawer_utils.js's `data-action="open-help-drawer"` dispatch. **Non-blocking layering lives in `css/tour.css`, keyed on driver's `.driver-active` body class** (not JS): driver.js makes itself modal with `.driver-active * { pointer-events: none }`, so `tour.css` lifts the toolbar (the Help menu — reachable for the whole tour) and the open help drawer above the overlay and restores `pointer-events` on their *subtrees* (raising the root alone is not enough — the actual buttons are descendants). The canvas itself stays dimmed and guarded. Re-opening the picker (Help ▸ Open templates) ends the tour: `tour.js` destroys the active driver instance when a `#template-picker` is swapped back in, so the picker is never stranded under the overlay. Auto-run is once-ever: `onboarding_first_run.js` defers its `onboarding:first-run` event until the picker is gone (a template loaded, scratch chosen, or content already present), and `tour.js` runs on that event; the help menu's `data-action="replay-tour"` replays it any time.

## Security and data

- Session-only by default; no PII expected. Do not log sensitive info.
- Validate inputs in views; trust computations to the domain engine but validate shape/types at boundaries.
