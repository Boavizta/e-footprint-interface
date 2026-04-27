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
└── domain/reference_data/     # JSON configs (default data)
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

### Object factory

`model_builder/domain/object_factory.py`:

- `create_efootprint_obj_from_parsed_data()` — creates efootprint objects from pre-parsed form data. Supports both list-based (`List[ChildType]`) and dict-based (`ExplainableObjectDict`) constructor parameters.
- `edit_object_from_parsed_data()` — handles object updates via `ModelingUpdate`.

### Extension mechanism

The library exposes `ExplainableObject.register_subclass(matcher)` so that JSON files can round-trip back into typed Python objects.

**For e-footprint-interface development, register new subclasses inside the e-footprint package itself** (typically `efootprint/builders/timeseries/`). Otherwise the library would no longer be able to load JSON files generated by the interface. This is why the form-driven extensions originally written here — `ExplainableHourlyQuantitiesFromFormInputs` and `ExplainableRecurrentQuantitiesFromConstant` — now live under `e-footprint/efootprint/builders/timeseries/`.

`model_builder/domain/entities/efootprint_extensions/` is preserved as an extension point for downstream consumers (e.g. a company building a custom interface on top of e-footprint with proprietary subclasses that should not bleed into the public library). It is currently empty in our codebase; this case has not appeared in practice yet. When in doubt, put new subclasses in e-footprint.

## Creation prerequisites and disabled UX

Web classes that have prerequisites for creation define a `can_create(cls, model_web) -> bool` classmethod. Returns `True` when allowed, `False` when blocked. `get_creation_prerequisites` delegates to `can_create` and raises a generic error if blocked (last line of defense — the UI should have disabled the button before this point).

`ModelWeb._build_creation_constraints()` iterates all registered web classes, deduplicates by MRO defining class, and returns a dict keyed by the defining class name (`"JobWeb"`, `"UsagePatternWeb"`, etc.), plus a `"__results__"` sentinel entry from `SystemValidationService`. Values are `{"enabled": bool, "disabled": bool}` for class-based entries; `__results__` additionally carries `reason` (live validation-error text). Static disabled-button tooltips live in `CONSTRAINT_MESSAGES` and are resolved at render time via the `constraint_tooltip` template filter — the domain never imports from adapters. This dict is stored at `model_web.creation_constraints` and recomputed after every mutation.

**Constraint diff on mutation.** `ModelingObjectWeb.create_side_effects`, `edit_side_effects`, and `delete_side_effects` are instance methods. They read `self.model_web` and delegate to the shared `self._recompute_constraints_and_emit_regions()` helper, which diffs old vs. new constraints and, when any flip:

- Emits two OOB regions: `model_canvas` (re-renders `#model-canva` contents via `innerHTML`) and `results_buttons` (updates `#btn-open-panel-result` and `#show-results-toolbar-btn` via `outerHTML`).
- Sets `model_web.constraint_changes` to a list of `(key, "locked"|"unlocked")` tuples.

Subclasses that override a `*_side_effects` hook (e.g. `EdgeDeviceGroupWeb`) must call `super()` first and then extend the returned region list, or the diff-based regions will be lost.

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
- **Templates.**
  - Base layouts in `theme/templates/` (e.g., `base.html`, `navbar.html`) with Bootstrap styling.
  - Feature templates and partials under `model_builder/templates/model_builder/`.
  - Save button is centralized in `side_panel_structure.html` as a `{% block save_button %}` default.
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

## Security and data

- Session-only by default; no PII expected. Do not log sensitive info.
- Validate inputs in views; trust computations to the domain engine but validate shape/types at boundaries.
