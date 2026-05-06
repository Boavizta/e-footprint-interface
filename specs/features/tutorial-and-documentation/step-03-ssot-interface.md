# Step 3 — Surface SSOT in the interface: implementation plan

**Status:** Plan — under review.
**Date:** 2026-05-04.
**Spec context:**
- [`99-implementation-plan.md`](99-implementation-plan.md) Step 3 (high-level deliverables).
- [`01-single-source-of-truth.md`](01-single-source-of-truth.md) (DescriptionProvider port, placeholder syntax, content kinds, interface-side tests).
- [`05-maintainability-and-build.md`](05-maintainability-and-build.md) Step 3 row (`{ui:token}` resolution, `class_ui_config.json` completeness, DescriptionProvider round-trip).
- [`00-index.md`](00-index.md) (overall feature framing and decisions summary).

**Prerequisite:** Step 2 has landed in e-footprint. Concrete classes carry `param_descriptions`, class docstrings, `update_<attr>` docstrings, and (where warranted) `disambiguation`, `pitfalls`, `interactions`, `param_interactions`. The library-side `tests/test_descriptions.py` is hard-failing.

**Assumed library inheritance shape (verify against Step 2 before starting):** for every concrete class, `klass.param_descriptions` (read via plain attribute lookup) covers every `__init__` param — either authored on the class directly or inherited from an abstract base. The interface adapter relies on `getattr(klass, "param_descriptions", {})` returning the full dict for the concrete class; if Step 2 lands per-class-only dicts without inheritance, the form-field tooltip coverage claim breaks for subclasses and this plan needs a merge step.

---

## Goal

Make library-side SSOT metadata visible inside the interface via a `DescriptionProvider` port and `EfootprintDescriptionProvider` adapter. Surface it concretely as info icons on form fields and on object cards, plus a help drawer linked from class cards. Resolve `{kind:target}` placeholders before any string reaches a template — domain and templates never see raw tokens. Extend `class_ui_config.json` with an optional `interactions` field for interface-specific guidance and back it with a `{ui:token}` registry. Wire the three new tests called for in Topic 5 (Step 3 row).

This step is interface-only. No library changes.

---

## Layered tooltip merging (user-added constraint)

A field can have descriptive content from two sources, and **both must render**:

1. **Library-side `param_descriptions[param]`** (semantic — what the param means in the model).
2. **Interface-side `field_ui_config.json[field].tooltip`** (interface-specific — UI guidance, formatting hints, edge cases that surface only via the form).

The interface tooltip is **appended** to the library description, not a replacement. When only one is present, that one is used as-is. When both are absent, no tooltip renders. Merging happens once, in the adapter — templates only ever receive a final, placeholder-resolved string.

Concretely the merge produces:

```
<library param_description, placeholder-resolved><br><br><interface tooltip, placeholder-resolved>
```

The separator is a literal `<br><br>` HTML fragment, not `\n\n`: Bootstrap's popover with `data-bs-html="true"` (see "Popover content rendering" below) treats raw newlines as whitespace, so newlines would not produce a visible paragraph break. The order is fixed: library first, interface second. Rationale: the library description states the meaning of the parameter; the interface tooltip is local guidance that builds on that meaning.

This forces the existing `FieldUIConfigProvider.get_tooltip(field_name)` callers to rewire, because the merged string requires the class context (param descriptions are per-class). All call sites move to `DescriptionProvider.field_tooltip(class_name, param)`. Every form field today maps to a real library `(class, param)` pair — including `parent_group_memberships`, which is the UI label for `EdgeDeviceGroup.sub_group_counts` or `EdgeDeviceGroup.edge_device_counts` depending on what is being added. The call site resolves to the right pair before invoking the provider (see "Form context builder rewiring" below), so the provider signature stays strictly class-scoped and there is no unscoped fallback.

---

## Architecture additions

### `DescriptionProvider` port — `domain/interfaces/description_provider.py`

`Protocol` with no Django imports. The interface domain layer depends only on this. Methods return **placeholder-resolved strings; HTML or plain depending on the handler mode the provider was constructed with** (or `None` when absent). Callers never see `{kind:target}` tokens. Step 3 uses the HTML-mode singleton everywhere; the protocol is mode-agnostic so a future text-mode adapter can satisfy the same port.

```python
class DescriptionProvider(Protocol):
    def class_description(self, class_name: str) -> str | None: ...
    def class_disambiguation(self, class_name: str) -> str | None: ...
    def class_pitfalls(self, class_name: str) -> str | None: ...
    def class_interactions(self, class_name: str) -> str | None: ...  # interface-side, from class_ui_config
    def param_description(self, class_name: str, param: str) -> str | None: ...  # library-only, raw (no merge)
    def field_tooltip(self, class_name: str, param: str) -> str | None: ...  # merged: library param_description + interface tooltip
    def calc_description(self, class_name: str, attr: str) -> str | None: ...
    def param_interaction(self, class_name: str, param: str) -> str | None: ...  # optional Python-facing param hint, rare
```

All methods are strictly class-scoped (`class_name: str`, never `None`). `field_tooltip` is the merge point described above and is what every form-field call site uses. `param_description` is exposed separately for callers that explicitly want the unmerged library string (e.g. future help-drawer per-param sections); `field_tooltip` is implemented in terms of it so the contract stays consistent. `class_interactions` reads from `class_ui_config.json` (interface-owned). The other class-level methods read from the library class via introspection. Methods return `SafeString` (Django) in HTML mode so callers can render with `|safe` without re-escaping.

### `EfootprintDescriptionProvider` adapter — `adapters/ui_config/efootprint_description_provider.py`

The single adapter implementing the port. Lives next to the existing `*_provider.py` files in `ui_config/` because it consumes the same JSON families. Shape matches `ClassUIConfigProvider` and `FieldUIConfigProvider`: a module-level singleton instance, no per-request construction.

```python
# adapters/ui_config/efootprint_description_provider.py
from django.conf import settings
from .interface_placeholder_handlers import build_html_handlers
from .ui_token_registry import UI_TOKENS

_HTML_HANDLERS = build_html_handlers(UI_TOKENS, settings.MKDOCS_BASE_URL)


class EfootprintDescriptionProvider:
    def __init__(self, handlers: dict[str, Callable[[str], str]]):
        self._handlers = handlers
        self._class_cache: dict[str, type] = {}

    def field_tooltip(self, class_name: str, param: str) -> SafeString | None:
        klass = self._resolve_class(class_name)
        library_desc = getattr(klass, "param_descriptions", {}).get(param)
        interface_desc = FIELD_UI_CONFIG.get(param, {}).get("tooltip")
        return self._merge(library_desc, interface_desc)
    ...


EFOOTPRINT_DESCRIPTION_PROVIDER = EfootprintDescriptionProvider(_HTML_HANDLERS)
```

Call sites import the singleton:

```python
from model_builder.adapters.ui_config.efootprint_description_provider import EFOOTPRINT_DESCRIPTION_PROVIDER
```

Rationale for the singleton: construction is cheap, no shared mutable state, all underlying data (`UI_TOKENS`, `CLASS_UI_CONFIG`, `ALL_EFOOTPRINT_CLASSES_DICT`, `settings.MKDOCS_BASE_URL`) is module-cached anyway, and broken handler config fails server startup rather than first-request. Matches the existing `ClassUIConfigProvider` / `FieldUIConfigProvider` convention.

Class lookup goes through `efootprint.all_classes_in_order.ALL_EFOOTPRINT_CLASSES_DICT` (concrete + abstract bases — interface-side `MODELING_OBJECT_CLASSES_DICT` only covers concrete classes, which would miss abstract keys like `ServerBase`/`JobBase` that `class_ui_config.json` legitimately uses). For consistency, `class_name` accepts the **efootprint class name** (e.g. `"Server"`, `"GPUServer"`, `"ServerBase"`) — web class names (`"ServerWeb"`) are translated via the existing mapping when the call site only knows the web class. Lookups are cached in `self._class_cache` (bounded — ~20 classes total).

Inheritance: `disambiguation`, `pitfalls`, and `interactions` are inherited via Python attribute lookup. The adapter honors inheritance — same behaviour as the library tests and the mkdocs build. The library-side convention is already settled (see `e-footprint/specs/conventions.md` §"Class-level metadata inheritance"): abstract bases carry the shared text and concrete subclasses override only when wording diverges, so the adapter can rely on plain attribute lookup with no special handling.

### Placeholder resolution — reuse `efootprint.utils.placeholder_resolver`

The library already publishes a generic resolver at `efootprint/utils/placeholder_resolver.py`:

```python
PLACEHOLDER_PATTERN = re.compile(r"\{(\w+):([^}]+)\}")
def extract_placeholders(text) -> List[Tuple[str, str]]
def resolve_placeholders(text, handlers: dict[str, Callable[[str], str]]) -> str
```

The mkdocs reference generator already consumes it via its own `_build_placeholder_handlers` returning `{"class": ..., "param": ..., "calc": ..., "doc": ..., "ui": _reject_ui}`. The library tests consume `extract_placeholders` for validation. **No library changes.** The interface imports `resolve_placeholders` and supplies its own handler dict.

**New file** — `adapters/ui_config/interface_placeholder_handlers.py`. Two builder functions, one per output mode:

- `build_html_handlers(ui_tokens, mkdocs_base_url) -> dict[str, Callable[[str], str]]`
- `build_text_handlers(ui_tokens) -> dict[str, Callable[[str], str]]`

Both consult `ALL_EFOOTPRINT_CLASSES` directly to validate `class:X`, `param:X.y`, `calc:X.y` targets — same lookups the library's `tests/test_descriptions.py` performs. (No need to lift validation predicates into the library: the validation is one `name in ALL_EFOOTPRINT_CLASSES` check, and the mkdocs equivalent of "is this class in the rendered nav?" doesn't apply to the interface.)

| Kind | HTML handler output | Text handler output | Failure mode |
|---|---|---|---|
| `class:X` | `<a href="/model_builder/open-help-drawer/X/" class="help-drawer-trigger" hx-get=… hx-target="#sidePanel">{label}</a>`; `label` from `class_ui_config[X].label` (or `X` if unconfigured). | `{label}` plain. | Unknown `X` (not in `ALL_EFOOTPRINT_CLASSES_DICT`) → `ValueError`. |
| `param:X.y` | `<span class="ssot-param-ref">{label}</span>` where `label` comes from `field_ui_config[y].label` (fallback: `y`). | `{label}` plain. | Unknown `X` (not in `ALL_EFOOTPRINT_CLASSES_DICT`) or `y` not in `X.__init__` → `ValueError`. |
| `calc:X.y` | `<span class="ssot-calc-ref">{humanized_attr}</span>`. | `{humanized_attr}` plain. | Unknown → `ValueError`. |
| `doc:slug` | `<a href="{mkdocs_base_url}/{slug}" target="_blank" rel="noopener">{slug}</a>`. | `{slug}` plain. | Unknown slug not validated here; mkdocs build is authoritative. |
| `ui:token` | `<span class="ssot-ui-ref" data-ui-token="{token}">{display}</span>`; `display` from `UI_TOKENS[token]["display"]`. | `{display}` plain. | Unknown token → `ValueError`. |

HTML handlers escape variable parts with Django's `escape`. Text handlers return plain strings.

The HTML-mode handler dict is built at module import time in `efootprint_description_provider.py` using `build_html_handlers(UI_TOKENS, settings.MKDOCS_BASE_URL)` and injected into the singleton instance. `MKDOCS_BASE_URL` is a Django setting (single source of truth, env-overridable); add it to `settings.py` with a sensible default. Text mode is unused in Step 3; a future text-mode caller would construct a second singleton (`EFOOTPRINT_DESCRIPTION_PROVIDER_TEXT`) rather than introducing a runtime mode flag. Method calls invoke `resolve_placeholders(text, self._handlers)` directly — no wrapper class needed.

### `{ui:token}` registry — `adapters/ui_config/ui_token_registry.py`

Python dict literal mapping each token to:

```python
UI_TOKENS = {
    "infra_panel_add_button": {
        "display": "the Add button in the Infrastructure section",
        "selector": "#add_server",  # used later by the guided tour, optional today
    },
    ...
}
```

Tokens appear only in `class_ui_config.json` `interactions` strings (and later, in tour content from Step 6). Library-side strings are forbidden from using `{ui:...}` and Step 2 already enforces that.

Why a Python module rather than JSON: token entries carry a selector that benefits from comments and grouping; this is interface-only configuration with no need for hot reload or external editing.

### `class_ui_config.json` — new optional `interactions` field

Extended schema, additive only:

```json
{
  "ServerBase": {
    "label": "Server",
    "type_object_available": "Available server types",
    "interactions": "Add via {ui:infra_panel_add_button}, then link {class:Job}s via the jobs panel."
  }
}
```

The field is optional. Classes without it simply don't render an "Interactions" section in the help drawer. This step adds the field as a schema option; the actual content is written incrementally — at minimum for the four classes that already drive the guided-tour orientation in Step 6. **Author on the abstract base where one exists** (e.g. `ServerBase` rather than `Server`/`GPUServer`/`BoaviztaCloudServer`; `JobBase` rather than `Job`/`GPUJob`) so concrete subclasses share the text via the same provider lookup. Where no abstract base exists in the JSON (e.g. `UsageJourney`, `UsagePattern`), author on the concrete class. The provider's class lookup walks the MRO so a request for `Server` resolves to the `ServerBase` entry when `Server` itself has none.

### `ClassUIConfigProvider` — extend with class-level lookups

Currently the provider exposes `get_label`, `get_type_object_available`, `get_more_descriptive_label`. Add:

- `get_interactions(class_name) -> str | None`

The `EfootprintDescriptionProvider` calls this for `class_interactions`; the existing form-builder call sites are unchanged. The completeness test checks JSON keys against `ALL_EFOOTPRINT_CLASSES_DICT` directly — no provider method needed.

---

## UI deliverables

### Info icons on form fields

`label.html` already renders an info icon when `field.tooltip` is truthy. Today `field.tooltip` comes from `FieldUIConfigProvider.get_tooltip(field_name)` (interface-only). After this step, the form context builder calls `DescriptionProvider.field_tooltip(class_name, param)` — the merged library+interface string — and stores the result in `field["tooltip"]`. Templates do not change.

The class context is already available in `FormContextBuilder`: every form is generated for a specific web object (`form_context_builder.py` knows the web class via `web_class.efootprint_class.__name__`). Pipe that into the field-build step.

Coverage delta: every form field for every class now has the option of carrying a tooltip. Today many are blank because `field_ui_config.json` doesn't define one and there is no library description. After Step 2, `param_descriptions` covers every param for every class, so info icons will appear on every numeric/text param field — visually busier than today, but consistent. No template changes needed.

### Info icons on Add buttons

Help is class-level, not instance-level, and the natural moment to ask "what is a Server? when should I use one?" is *before* creation — not after a card already sits on the canvas. The single help-drawer trigger therefore lives next to each Add button in `model_canvas_content.html` (Servers, External APIs, Edge devices, Edge device groups, Usage journeys, Edge usage journeys, Usage patterns, Edge usage patterns — already keyed per class or abstract base, matching the initial `interactions` set).

Object cards do **not** carry a help-drawer trigger. They keep their existing header; no per-instance icon. Rationale: it would render redundantly across every instance and surface help at the wrong moment.

The Add-button include (`model_builder/components/add_object_button.html`) is extended to optionally render a sibling info icon when `class_name`, `class_label`, and `class_description` are all passed. The icon is a separate `<button>` next to the Add button (not nested — the Add button's `hx-trigger="click"` covers its whole interior):

```html
{% if class_name and class_description %}
<button type="button" class="btn btn-link p-0 ms-1 help-drawer-trigger"
        hx-get="/model_builder/open-help-drawer/{{ class_name }}/" hx-target="#sidePanel"
        hx-swap="innerHTML" aria-label="About {{ class_label }}">
    {# reuse the question-circle SVG inline #}
</button>
{% endif %}
```

The icon renders only when `class_description` is non-empty. The two elements (Add button + help icon) are wrapped in a flex row so layout stays unchanged when the icon is absent. Each call site in `model_canvas_content.html` passes the same `class_name` it already passes via `hx_url` (e.g. `ServerBase`, `UsageJourney`), plus `class_label` and `class_description` resolved in the view.

The view that renders `model_canvas_content.html` calls:
- `EFOOTPRINT_DESCRIPTION_PROVIDER.class_description(class_name)` for the gating value,
- `ClassUIConfigProvider.get_label(class_name)` for the aria-label,

once per Add button, and exposes both alongside the existing `creation_constraints` dict in the template context. `aria-label` is the screen-reader text announced when the help icon receives focus — using the class's human label ("Server") rather than the technical class name ("ServerBase") gives assistive-tech users meaningful context.

### Help drawer

A new side-panel template `model_builder/templates/model_builder/help_drawer/class_help.html`. Rendered in the existing `#sidePanel` slot via HTMX, the same way "Link existing" works (`open_link_existing_panel` in `views_edition.py`). Inspecting the existing templates confirms the slide-in side-panel pattern is the idiomatic choice; the open question from Step 3 ("slide-in panel vs modal") resolves to **slide-in side panel**.

**Trigger:** the only entry point is the info icon next to each Add button (see "Info icons on Add buttons" above). There is no card-level trigger.

Sections, in order, each rendered only when the provider returns a non-empty value:

1. Title: class label + "Help".
2. Description: class docstring.
3. Disambiguation.
4. Common pitfalls.
5. Interface interactions (from `class_ui_config.json`).
6. Footer link: "Read more in the docs" → `{doc:objects/{class_name}}` resolved at render time.

All strings come pre-resolved from `EfootprintDescriptionProvider`. The template uses `|safe` because the resolver emits trusted HTML built from values it controls — *not* from user input. (User-supplied model names never enter description strings.)

A new view `views_help.py::open_help_drawer(request, class_name)` builds the context dict and renders the partial. Routed under `/model_builder/open-help-drawer/<class_name>/` to match the existing convention (`/open-edit-object-panel/...`, `/open-link-existing-panel/...`). Unknown `class_name` (not in `ALL_EFOOTPRINT_CLASSES_DICT`) raises `Http404` — Django default, catches typos in templates and hand-typed URLs.

### Form context builder rewiring

Three call sites switch from `FieldUIConfigProvider.get_tooltip(attr_name)` to `EFOOTPRINT_DESCRIPTION_PROVIDER.field_tooltip(class_name, attr_name)`:

1. **`form_field_generator.py:168`** (`generate_select_multiple_field`) — class scope is `efootprint_class_str` from the enclosing `generate_dynamic_form` (verified: this variable is in scope at the call site, passed via the existing call chain).
2. **`form_field_generator.py:207`** (`generate_dynamic_form` loop) — same `efootprint_class_str` is the local variable being iterated.
3. **`form_context_builder.py:160`** (`_build_parent_group_membership_field`) — this is the "Add to parent groups" select. The field updates a concrete library attr on `EdgeDeviceGroup`:
   - `sub_group_counts` when the new object is itself an `EdgeDeviceGroup`,
   - `edge_device_counts` when the new object is an `EdgeDevice` (or any subclass of `EdgeDeviceBase`).

   Resolution is local to `_build_parent_group_membership_field`: the caller already knows the new object's web class, so the builder maps it to the right `(class_name="EdgeDeviceGroup", param=<sub_group_counts|edge_device_counts>)` pair and calls `field_tooltip` with it. The provider stays strictly class-scoped — there is no unscoped branch.

Since the singleton is imported, there is no provider plumbing through helper signatures. `FieldUIConfigProvider.get_tooltip` becomes unused and is removed from `FieldUIConfigProvider` (label, config lookups remain).

### Popover content rendering

The existing tooltip popover is plain text. To render the merged content (which contains explicit `<br><br>` separators and possibly `<a>` tags from the resolver), enable Bootstrap's HTML mode by setting `data-bs-html="true"` on the popover trigger. Adjust `side_panels/components/tooltip.html` to accept a `tooltip_html` flag (default `false`) and emit `data-bs-html` when truthy. Field-label info icons set `tooltip_html=True`. Other current call sites (which pass plain strings) keep the default and are unaffected.

Note on whitespace: Bootstrap's HTML mode does **not** convert raw newlines into paragraph breaks — they collapse to whitespace. The merge step therefore inserts a literal `<br><br>` between the library and interface segments rather than `\n\n` (see "Layered tooltip merging" above).

XSS concern: only resolver-emitted HTML is allowed. The merge step in `EfootprintDescriptionProvider` runs each input through the resolver (which calls Django's `escape` on the textual chunks before re-inserting tags), so the final string is safe. `field_tooltip` returns `SafeString` to make that contract explicit; non-resolved fallbacks (e.g. legacy interface tooltips already in `field_ui_config.json`) are run through `escape` on their way out.

---

## Files to change

### Domain

1. `domain/interfaces/description_provider.py` — **new**. Protocol per "Architecture additions" above.

### Adapters (the bulk of the work)

2. `adapters/ui_config/interface_placeholder_handlers.py` — **new**. Two builder functions (`build_html_handlers`, `build_text_handlers`) returning handler dicts for the library's `resolve_placeholders`. No new resolver — imports `efootprint.utils.placeholder_resolver`.
3. `adapters/ui_config/ui_token_registry.py` — **new**. `UI_TOKENS` dict. Initial entries cover only the tokens used by `class_ui_config.json` content written in this step.
4. `adapters/ui_config/efootprint_description_provider.py` — **new**. `DescriptionProvider` implementation with class lookup, `field_tooltip` merge, calls `resolve_placeholders(text, handlers)` directly. Exposes a module-level `EFOOTPRINT_DESCRIPTION_PROVIDER` singleton built with HTML handlers at import time.
5. `adapters/ui_config/class_ui_config_provider.py` — extend with `get_interactions`.
6. `adapters/ui_config/class_ui_config.json` — add `interactions` field for the four "tour-relevant" classes, authored on the abstract base where one exists (`ServerBase`, `JobBase`) or on the concrete class otherwise (`UsageJourney`, `UsagePattern`). Other classes can be filled in later without code changes.
6b. `adapters/ui_config/field_ui_config.json` — migrate the existing `parent_group_memberships` entry. The `label` ("Add to parent groups") stays under that key (it's the UI label, not a library attr). Any tooltip text moves to per-attr entries under `sub_group_counts` and `edge_device_counts` (the real library attrs on `EdgeDeviceGroup`), where it will layer under library `param_descriptions` via the merge.

### Forms

7. `adapters/forms/form_context_builder.py` — in `_build_parent_group_membership_field`, replace `FieldUIConfigProvider.get_tooltip("parent_group_memberships")` with a call to `EFOOTPRINT_DESCRIPTION_PROVIDER.field_tooltip("EdgeDeviceGroup", attr)` where `attr` resolves to `sub_group_counts` or `edge_device_counts` based on the new object's web class. No constructor changes (singleton is imported).
8. `adapters/forms/form_field_generator.py` — at `:168` and `:207`, replace `field_config.get("tooltip", False)` with `EFOOTPRINT_DESCRIPTION_PROVIDER.field_tooltip(efootprint_class_str, attr_name)` (verified: `efootprint_class_str` is in scope at both call sites via `generate_dynamic_form`). No new keyword arguments.
8b. `adapters/ui_config/field_ui_config_provider.py` — remove `get_tooltip` (now unused). Keep `get_label` and `get_config`.

### Views and presenters

9. `adapters/views/views_help.py` — **new**. `open_help_drawer(request, class_name)` raises `Http404` for unknown `class_name`, otherwise builds the help-drawer context via the singleton and returns the partial.
10. `model_builder/urls.py` — route `/open-help-drawer/<str:class_name>/` to the new view (matches the existing `/open-edit-object-panel/...`, `/open-link-existing-panel/...` convention).
11. `settings.py` — add `MKDOCS_BASE_URL` with a sensible default (env-overridable). Consumed by `efootprint_description_provider.py` at module import to build the HTML handler dict.
12. The view that renders `model_canvas_content.html` (`adapters/views/views_model_builder.py` or wherever the canvas context is built) — for each Add button: call `EFOOTPRINT_DESCRIPTION_PROVIDER.class_description(class_name)` and `ClassUIConfigProvider.get_label(class_name)`, expose both in the template context, and pass them through the `add_object_button.html` include.

### Templates

13. `templates/model_builder/help_drawer/class_help.html` — **new**. Sections per "Help drawer" above.
14. `templates/model_builder/components/add_object_button.html` — accept optional `class_name`, `class_label`, and `class_description` parameters; when `class_description` is truthy, render a sibling help-icon button that opens the help drawer with `aria-label="About {{ class_label }}"`. Object cards (`button_card_header.html`, `object_cards/*.html`) are not modified.
14b. `templates/model_builder/components/model_canvas_content.html` — pass `class_name`, `class_label`, `class_description` to each `add_object_button.html` include.
15. `templates/model_builder/side_panels/components/tooltip.html` — accept `tooltip_html` flag; emit `data-bs-html="true"` when truthy.
16. `templates/model_builder/side_panels/dynamic_form_fields/label.html` — pass `tooltip_html=True` when including the tooltip partial. (Other includes of `tooltip.html` are unchanged.)

### Tests

17. `tests/unit_tests/adapters/ui_config/test_description_provider.py` — **new**. Round-trip per Topic 5 §3.4: call each method on the singleton for a representative class, assert non-None for present fields. Specific cases:
    - `field_tooltip` returns the merged string when both library `param_descriptions` and interface `field_ui_config[tooltip]` are present, with library text first and interface text second separated by a literal `<br><br>`.
    - `field_tooltip` returns library-only text when interface is absent, and vice versa.
    - `field_tooltip` returns `None` when neither is present.
    - `field_tooltip("EdgeDeviceGroup", "sub_group_counts")` and `field_tooltip("EdgeDeviceGroup", "edge_device_counts")` both return the merged tooltip — covers the `parent_group_memberships` resolution path (guards against the migration regressing if either per-attr entry goes missing in `field_ui_config.json`).
    - `class_description` returns the placeholder-resolved class docstring (i.e. no raw `{kind:target}` tokens survive).
    - `class_interactions` returns a placeholder-resolved string and the resolver has consumed the `{ui:...}` tokens that appear in the test fixture.
    - Class lookup with a concrete subclass (`Server`) returns the `interactions` text authored on its abstract base (`ServerBase`) via MRO walk.
18. `tests/unit_tests/adapters/ui_config/test_interface_placeholder_handlers.py` — **new**. Handler tests (the library already tests `resolve_placeholders` itself):
    - HTML handlers: each kind emits the expected tag for a known target.
    - Text handlers: each kind emits the expected plain label.
    - Unknown target for `class`, `param`, `calc`, `ui` raises `ValueError`; unknown `doc` slug renders without raising.
    - Variable parts are HTML-escaped in the HTML handlers (input containing `<` or `>` in a label).
19. `tests/unit_tests/adapters/ui_config/test_ui_config_consistency.py` — extend the existing file from Step 1 with two new check groups:
    - **`{ui:token}` resolution**: every `{ui:token}` appearing in any `class_ui_config.json` `interactions` field has a registered handler entry in `UI_TOKENS`. Every `UI_TOKENS` entry has a non-empty `display`.
    - **`class_ui_config.json` completeness**: every key in `CLASS_UI_CONFIG` corresponds to a class name in `efootprint.all_classes_in_order.ALL_EFOOTPRINT_CLASSES_DICT` (concrete + abstract — needed because the JSON intentionally keys some entries by abstract bases like `ServerBase`/`JobBase`/`EdgeDeviceBase`; using `MODELING_OBJECT_CLASSES_DICT` would reject those). Every concrete class in `MODELING_OBJECT_CLASSES_DICT` either has an entry, inherits one from an abstract base entry via MRO, or is in an explicit `EXCLUDED_CLASSES_FROM_UI_CONFIG` list. The exclusion list is co-located with the test, with one-line justifications.
20. `tests/unit_tests/adapters/views/test_views_help.py` — **new**. Smoke tests:
    - GET `/model_builder/open-help-drawer/Server/` returns 200 with the expected class label in the response body and no raw `{kind:target}` tokens.
    - GET on a class with no `interactions` field returns 200 with the "Interactions" section absent.
    - GET `/model_builder/open-help-drawer/NotARealClass/` returns 404.

### Out of scope for this step

- Writing `interactions` content for all classes. Initial set covers tour-relevant classes only; the rest is filler work that can land in any later step (or alongside docs work in Step 4).
- Tour-step content (Step 6).
- Anchor-scrolling behaviour for `{param:X.y}` and `{calc:X.y}` links (currently they render as labels; clickability comes later if needed).
- Translating the help-drawer view into a fully accessible modal alternative — slide-in side panel only.

---

## Cross-cutting concerns

- **Tests:** unit tests for resolver, provider, and view; extension of the existing `test_ui_config_consistency.py`. No new integration or E2E tests — the visible UI changes (info icons, help drawer) are covered well enough by view-level smoke tests; the underlying logic is pure and unit-testable. Rationale aligns with constitution §2.1 (Playwright reserved for critical flows).
- **Migrations:** none. No DB schema changes; no `interface_config` schema changes.
- **Docs:** add a short "SSOT and the DescriptionProvider port" section to `specs/architecture.md` once the step is implemented (per project convention in this repo's `CLAUDE.md`). One paragraph + a pointer to the topic file is enough.
- **CI:** no new workflow steps — the new tests run inside the existing `pytest tests/unit_tests` invocation already on `ci.yml`.

---

## Risks

- **Visual noise from universal info icons.** After Step 2 every numeric/text field in every form will carry a tooltip. If users find this distracting we can later introduce a `is_advanced_parameter`-style flag that suppresses the icon for "self-explanatory" fields — but defer that until we see real screenshots. Mitigation: ship as-is and **review screenshots of two representative dense forms (Server creation, Job creation) before declaring this step done**; if either looks objectively cluttered, scope a small follow-up rather than letting the risk roll silently into Step 7.
- **HTML in tooltips raises XSS surface area.** Mitigation: only resolver output is allowed; resolver escapes textual chunks; merge output is a `SafeString`. No user-supplied content reaches the merge.
- **Class lookup ambiguity (web vs efootprint class names).** Mitigation: provider accepts efootprint class names only; call sites that have the web class translate explicitly via `web_class.efootprint_class.__name__`. A single helper method on the adapter handles both forms to keep call sites short.
- **Step 2 inheritance shape.** The form-field tooltip coverage claim assumes `getattr(klass, "param_descriptions", {})` returns the full dict for any concrete class (via attribute inheritance from the abstract base). If Step 2 lands per-class-only dicts, subclasses will silently lose tooltips. Mitigation: verify against Step 2 before implementation (see Prerequisite), and the consistency test in #19 can be extended to cover `(class, param)` pairs missing from `param_descriptions`.

---

## Alternatives considered

- **Reimplement a resolver on the interface side.** Rejected: `efootprint.utils.placeholder_resolver` already exists and is shape-correct (parser + per-kind handler dispatch, handlers supplied by consumer). Two parsers on the same syntax would drift. Interface owns only its handler dict — that's adapter code where it belongs (constitution §1.1).
- **Lift validation predicates (`is_known_class`, etc.) into the library as a refactor.** Rejected: each check is a one-liner against `ALL_EFOOTPRINT_CLASSES`; the mkdocs equivalent ("is this class in the rendered nav?") is mkdocs-specific and doesn't generalize. Not worth the API surface.
- **`field_tooltip` returns library and interface strings separately, template concatenates.** Rejected: pushes presentation logic into Django templates and forces every consumer to know about both layers. The merge belongs in the adapter — single rendering contract for callers.
- **A second JSON file for `{ui:token}` tokens.** Rejected: tokens are tightly coupled to interface code (selectors), benefit from comments, and don't need to be hot-editable. Python module is the better fit.
- **Eagerly fill `interactions` for all classes in this step.** Rejected: it's content authorship work that can lag the plumbing without breaking anything. Wiring is what's load-bearing for Step 6.
- **Resolve `{doc:slug}` against a hard-coded list of mkdocs slugs in the interface.** Rejected: doc slugs live in mkdocs and would have to be duplicated. The mkdocs build is authoritative; we render the link and accept that the validation lives there.

---

## Constitutional notes

- §1.1 (CA dependency direction): `DescriptionProvider` Protocol lives in `domain/interfaces/`; the adapter and resolver live in `adapters/`. Domain code holds a port reference, never a concrete adapter. ✓
- §1.3 (library is the domain truth): library-side `param_descriptions`, docstrings, etc. remain authoritative. The interface adds an *append-only* layer (interface tooltip + `interactions`) — never overrides library text. ✓
- §1.4 (HTMX-first; minimize JS): help drawer is HTMX-driven; no new JS state. The only JS adjustment is enabling Bootstrap's `data-bs-html` flag on existing popovers. ✓
- §2 (quality gates): adds tests, no migrations, documents the new pattern in `architecture.md`. ✓

No constitutional amendment needed.

---

## Open questions

- **Scope of initial `interactions` content.** Default plan covers four tour-relevant classes — authored on `ServerBase`, `JobBase`, `UsageJourney`, `UsagePattern` (abstract base where one exists in the JSON, concrete otherwise). Confirm the list matches the four classes Step 6's tour will hit, or expand if Step 6 has shifted scope. Decide before writing the `class_ui_config.json` entries.
- ~~**Help-drawer URL pattern.**~~ Resolved: `/model_builder/open-help-drawer/<class_name>/`, matching the existing `/open-edit-object-panel/...`, `/open-link-existing-panel/...` convention.
- **Should the help drawer also offer a "view raw docstring" link (e.g. for power users)?** Out of scope for now, but easy to add later.
