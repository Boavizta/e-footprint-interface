# Step 3 — Surface SSOT in the interface: implementation plan

**Status:** Plan — under review.
**Date:** 2026-05-04.
**Spec context:**
- [`99-implementation-plan.md`](99-implementation-plan.md) Step 3 (high-level deliverables).
- [`01-single-source-of-truth.md`](01-single-source-of-truth.md) (DescriptionProvider port, placeholder syntax, content kinds, interface-side tests).
- [`05-maintainability-and-build.md`](05-maintainability-and-build.md) Step 3 row (`{ui:token}` resolution, `class_ui_config.json` completeness, DescriptionProvider round-trip).
- [`00-index.md`](00-index.md) (overall feature framing and decisions summary).

**Prerequisite:** Step 2 has landed in e-footprint. Concrete classes carry `param_descriptions`, class docstrings, `update_<attr>` docstrings, and (where warranted) `disambiguation`, `pitfalls`, `interactions`, `param_interactions`. The library-side `tests/test_descriptions.py` is hard-failing.

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
<library param_description, placeholder-resolved>

<interface tooltip, placeholder-resolved>
```

Two newlines between the two parts (rendered as a paragraph break by the Bootstrap popover via the `tooltip_html` flag — see "Popover content rendering" below). The order is fixed: library first, interface second. Rationale: the library description states the meaning of the parameter; the interface tooltip is local guidance that builds on that meaning.

This forces the existing `FieldUIConfigProvider.get_tooltip(field_name)` callers to rewire, because the merged string requires the class context (param descriptions are per-class). All call sites move to `DescriptionProvider.field_tooltip(class_name, param)`.

---

## Architecture additions

### `DescriptionProvider` port — `domain/interfaces/description_provider.py`

`Protocol` with no Django imports. The interface domain layer depends only on this. Methods return **already-resolved, plain strings** (or `None` when absent). Callers never see `{kind:target}` tokens.

```python
class DescriptionProvider(Protocol):
    def class_description(self, class_name: str) -> str | None: ...
    def class_disambiguation(self, class_name: str) -> str | None: ...
    def class_pitfalls(self, class_name: str) -> str | None: ...
    def class_interactions(self, class_name: str) -> str | None: ...  # interface-side, from class_ui_config
    def field_tooltip(self, class_name: str, param: str) -> str | None: ...  # merged: library param_description + interface tooltip
    def calc_description(self, class_name: str, attr: str) -> str | None: ...
    def param_interaction(self, class_name: str, param: str) -> str | None: ...  # optional Python-facing param hint, rare
```

`field_tooltip` is the merge point described above. `class_interactions` reads from `class_ui_config.json` (interface-owned). The other class-level methods read from the library class via introspection.

### `EfootprintDescriptionProvider` adapter — `adapters/ui_config/efootprint_description_provider.py`

The single adapter implementing the port. Lives next to the existing `*_provider.py` files in `ui_config/` because it consumes the same JSON families.

Construction:

```python
class EfootprintDescriptionProvider:
    def __init__(self, resolver: PlaceholderResolver):
        self._resolver = resolver

    def field_tooltip(self, class_name: str, param: str) -> str | None:
        klass = self._resolve_class(class_name)
        library_desc = (klass.param_descriptions or {}).get(param) if klass else None
        interface_desc = FIELD_UI_CONFIG.get(param, {}).get("tooltip")
        return self._merge(library_desc, interface_desc)
    ...
```

Class lookup goes through `ALL_EFOOTPRINT_CLASSES` (efootprint side) plus the existing `MODELING_OBJECT_CLASSES_DICT` mapping when the input is a web class name. For consistency, `class_name` accepts the **efootprint class name** (e.g. `"Server"`, `"GPUServer"`) — web class names (`"ServerWeb"`) are translated via the existing mapping when the call site only knows the web class.

The adapter caches resolved class lookups in a per-instance dict. The resolver is shared.

Inheritance footgun (flagged in Topic 1): `disambiguation`, `pitfalls`, and `interactions` are inherited via Python attribute lookup. The adapter intentionally honors inheritance — same behaviour as the library tests and the mkdocs build. If a child class needs different wording, the child class declares its own attribute. No special handling here.

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
| `class:X` | `<a href="/model_builder/help-drawer/X/" class="help-drawer-trigger" hx-get=… hx-target="#sidePanel">{label}</a>`; `label` from `class_ui_config[X].label` (or `X` if unconfigured). | `{label}` plain. | Unknown `X` (not in `ALL_EFOOTPRINT_CLASSES`) → `ValueError`. |
| `param:X.y` | `<span class="ssot-param-ref">{label}</span>` where `label` comes from `field_ui_config[y].label` (fallback: `y`). | `{label}` plain. | Unknown `X` or `y` not in `X.__init__` → `ValueError`. |
| `calc:X.y` | `<span class="ssot-calc-ref">{humanized_attr}</span>`. | `{humanized_attr}` plain. | Unknown → `ValueError`. |
| `doc:slug` | `<a href="{mkdocs_base_url}/{slug}" target="_blank" rel="noopener">{slug}</a>`. | `{slug}` plain. | Unknown slug not validated here; mkdocs build is authoritative. |
| `ui:token` | `<span class="ssot-ui-ref" data-ui-token="{token}">{display}</span>`; `display` from `UI_TOKENS[token]["display"]`. | `{display}` plain. | Unknown token → `ValueError`. |

HTML handlers escape variable parts with Django's `escape`. Text handlers return plain strings.

`EfootprintDescriptionProvider` is constructed with the handler dict appropriate for its mode (HTML for tooltips and the help drawer; text reserved for any future non-HTML context but not used in this step). Method calls invoke `resolve_placeholders(text, self._handlers)` directly — no wrapper class needed.

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
  "Server": {
    "label": "Server",
    "type_object_available": "Available server types",
    "interactions": "Add via {ui:infra_panel_add_button}, then link {class:Job}s via the jobs panel."
  }
}
```

The field is optional. Classes without it simply don't render an "Interactions" section in the help drawer. This step adds the field as a schema option; the actual content is written incrementally — at minimum for the four classes that already drive the guided-tour orientation in Step 6 (`Server`, `UsageJourney`, `UsagePattern`, `Job`).

### `ClassUIConfigProvider` — extend with class-level lookups

Currently the provider exposes `get_label`, `get_type_object_available`, `get_more_descriptive_label`. Add:

- `get_interactions(class_name) -> str | None`
- `is_known_class(class_name) -> bool` — used by the completeness test.

The `EfootprintDescriptionProvider` calls these for `class_interactions` and label resolution; the existing form-builder call sites are unchanged.

---

## UI deliverables

### Info icons on form fields

`label.html` already renders an info icon when `field.tooltip` is truthy. Today `field.tooltip` comes from `FieldUIConfigProvider.get_tooltip(field_name)` (interface-only). After this step, the form context builder calls `DescriptionProvider.field_tooltip(class_name, param)` — the merged library+interface string — and stores the result in `field["tooltip"]`. Templates do not change.

The class context is already available in `FormContextBuilder`: every form is generated for a specific web object (`form_context_builder.py` knows the web class via `web_class.efootprint_class.__name__`). Pipe that into the field-build step.

Coverage delta: every form field for every class now has the option of carrying a tooltip. Today many are blank because `field_ui_config.json` doesn't define one and there is no library description. After Step 2, `param_descriptions` covers every param for every class, so info icons will appear on every numeric/text param field — visually busier than today, but consistent. No template changes needed.

### Info icons on class cards

Object cards already display the class label at the top. Add a small info-icon button next to the label that opens the help drawer for that class. The icon reuses the existing `components/tooltip.html` SVG; `data-bs-toggle="popover"` is replaced with an HTMX-driven action that opens the drawer:

```html
{% if class_description %}
<button type="button" class="btn btn-link p-0 ms-1 help-drawer-trigger"
        hx-get="/model_builder/help-drawer/{{ class_name }}/" hx-target="#sidePanel"
        hx-swap="innerHTML" aria-label="About {{ class_label }}">
    {# reuse the question-circle SVG inline #}
</button>
{% endif %}
```

The button is rendered only when the provider returns a non-empty `class_description`.

The card template is `model_builder/templates/model_builder/components/object_card.html` (and the variants for journeys, devices, edge groups). The new icon goes into the existing card header markup.

### Help drawer

A new side-panel template `model_builder/templates/model_builder/help_drawer/class_help.html`. Rendered in the existing `#sidePanel` slot via HTMX, the same way "Link existing" works (`open_link_existing_panel` in `views_edition.py`). Inspecting the existing templates confirms the slide-in side-panel pattern is the idiomatic choice; the open question from Step 3 ("slide-in panel vs modal") resolves to **slide-in side panel**.

Sections, in order, each rendered only when the provider returns a non-empty value:

1. Title: class label + "Help".
2. Description: class docstring.
3. Disambiguation.
4. Common pitfalls.
5. Interface interactions (from `class_ui_config.json`).
6. Footer link: "Read more in the docs" → `{doc:objects/{class_name}}` resolved at render time.

All strings come pre-resolved from `EfootprintDescriptionProvider`. The template uses `|safe` because the resolver emits trusted HTML built from values it controls — *not* from user input. (User-supplied model names never enter description strings.)

A new view `views_help.py::class_help_drawer(request, class_name)` builds the context dict and renders the partial. Routed under `/model_builder/help-drawer/<class_name>/`.

### Form context builder rewiring

`form_context_builder.py:160` (`_build_parent_group_membership_field`) and `form_field_generator.py:168, 207` (`tooltip` keys built from `field_config.get("tooltip")`) all flow through one entry point: each builder/generator that produces a field dict.

Replace the `FieldUIConfigProvider.get_tooltip(attr_name)` calls with `description_provider.field_tooltip(class_name, attr_name)`. The provider is constructed once per request (or once per `FormContextBuilder` instance) and passed through. Avoid threading it through every helper signature — instead, attach it to `FormContextBuilder` at construction, and pass it explicitly to `form_field_generator` helpers via a single new keyword argument.

`FieldUIConfigProvider.get_tooltip` stays — it's still useful for the rare contexts where there's no class scope (e.g. the parent-group-memberships dict field, where the field exists across many classes). For those, the provider falls back to `FieldUIConfigProvider.get_tooltip(field_name)` only.

### Popover content rendering

The existing tooltip popover is plain text. To render the merged content (which contains paragraph breaks and possibly `<a>` tags from the resolver), enable Bootstrap's HTML mode by setting `data-bs-html="true"` on the popover trigger. Adjust `components/tooltip.html` to accept a `tooltip_html` flag (default `false`) and emit `data-bs-html` when truthy. Field-label info icons set `tooltip_html=True`. Other current call sites (which pass plain strings) keep the default and are unaffected.

XSS concern: only resolver-emitted HTML is allowed. The merge step in `EfootprintDescriptionProvider` runs each input through the resolver (which calls Django's `escape` on the textual chunks before re-inserting tags), so the final string is safe. `field_tooltip` returns `SafeString` to make that contract explicit; non-resolved fallbacks (e.g. legacy interface tooltips already in `field_ui_config.json`) are run through `escape` on their way out.

---

## Files to change

### Domain

1. `domain/interfaces/description_provider.py` — **new**. Protocol per "Architecture additions" above.

### Adapters (the bulk of the work)

2. `adapters/ui_config/interface_placeholder_handlers.py` — **new**. Two builder functions (`build_html_handlers`, `build_text_handlers`) returning handler dicts for the library's `resolve_placeholders`. No new resolver — imports `efootprint.utils.placeholder_resolver`.
3. `adapters/ui_config/ui_token_registry.py` — **new**. `UI_TOKENS` dict. Initial entries cover only the tokens used by `class_ui_config.json` content written in this step.
4. `adapters/ui_config/efootprint_description_provider.py` — **new**. `DescriptionProvider` implementation with class lookup, `field_tooltip` merge, calls `resolve_placeholders(text, handlers)` directly.
5. `adapters/ui_config/class_ui_config_provider.py` — extend with `get_interactions`, `is_known_class`.
6. `adapters/ui_config/class_ui_config.json` — add `interactions` field for the four "tour-relevant" classes (Server, UsageJourney, UsagePattern, Job). Other classes can be filled in later without code changes.

### Forms

7. `adapters/forms/form_context_builder.py` — accept a `DescriptionProvider` at construction; replace direct `FieldUIConfigProvider.get_tooltip` calls for class-scoped fields with `description_provider.field_tooltip(class_name, attr)`. Keep the unscoped fallback for the parent-group-memberships field.
8. `adapters/forms/form_field_generator.py` — accept the provider and class context as keyword args; update the two call sites that build `tooltip` keys.

### Views and presenters

9. `adapters/views/views_help.py` — **new**. `class_help_drawer(request, class_name)` builds the help-drawer context and returns the partial.
10. `model_builder/urls.py` — route `/help-drawer/<str:class_name>/` to the new view.
11. Wherever `FormContextBuilder` is constructed today — pass a single shared `EfootprintDescriptionProvider` instance built per request (provider is cheap; do not memoize across requests because `class_ui_config.json` should reflect dev edits without restart).

### Templates

12. `templates/model_builder/help_drawer/class_help.html` — **new**. Sections per "Help drawer" above.
13. `templates/model_builder/components/object_card.html` (and journey/device/edge variants found by grepping for the card-title block) — add the help-drawer trigger button next to the class label, gated on `class_description` being non-empty.
14. `templates/model_builder/side_panels/components/tooltip.html` — accept `tooltip_html` flag; emit `data-bs-html="true"` when truthy.
15. `templates/model_builder/side_panels/dynamic_form_fields/label.html` — pass `tooltip_html=True` when including the tooltip partial. (Other includes of `tooltip.html` are unchanged.)

### Tests

16. `tests/unit_tests/adapters/ui_config/test_description_provider.py` — **new**. Round-trip per Topic 5 §3.4: construct provider, call each method on a representative class, assert non-None for present fields. Specific cases:
    - `field_tooltip` returns the merged string when both library `param_descriptions` and interface `field_ui_config[tooltip]` are present, with library text first and interface text second separated by a blank line.
    - `field_tooltip` returns library-only text when interface is absent, and vice versa.
    - `field_tooltip` returns `None` when neither is present.
    - `class_description` returns the placeholder-resolved class docstring (i.e. no raw `{kind:target}` tokens survive).
    - `class_interactions` returns a placeholder-resolved string and the resolver has consumed the `{ui:...}` tokens that appear in the test fixture.
17. `tests/unit_tests/adapters/ui_config/test_interface_placeholder_handlers.py` — **new**. Handler tests (the library already tests `resolve_placeholders` itself):
    - HTML handlers: each kind emits the expected tag for a known target.
    - Text handlers: each kind emits the expected plain label.
    - Unknown target for `class`, `param`, `calc`, `ui` raises `ValueError`; unknown `doc` slug renders without raising.
    - Variable parts are HTML-escaped in the HTML handlers (input containing `<` or `>` in a label).
18. `tests/unit_tests/adapters/ui_config/test_ui_config_consistency.py` — extend the existing file from Step 1 with two new check groups:
    - **`{ui:token}` resolution**: every `{ui:token}` appearing in any `class_ui_config.json` `interactions` field has a registered handler entry in `UI_TOKENS`. Every `UI_TOKENS` entry has a non-empty `display`.
    - **`class_ui_config.json` completeness**: every key in `CLASS_UI_CONFIG` corresponds to a class name in `MODELING_OBJECT_CLASSES_DICT` (catches stale entries from deleted classes); every class in `MODELING_OBJECT_CLASSES_DICT` either has an entry or is in an explicit `EXCLUDED_CLASSES_FROM_UI_CONFIG` list. The exclusion list is co-located with the test, with one-line justifications.
19. `tests/unit_tests/adapters/views/test_views_help.py` — **new**. Smoke test: GET `/model_builder/help-drawer/Server/` returns 200 with the expected class label in the response body and no raw `{kind:target}` tokens. Same for one class that has no `interactions` field, asserting the section is absent.

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

- **Visual noise from universal info icons.** After Step 2 every numeric/text field in every form will carry a tooltip. If users find this distracting we can later introduce a `is_advanced_parameter` style flag that suppresses the icon for "self-explanatory" fields — but defer that until we see real screenshots. Mitigation: ship as-is and decide based on feedback.
- **HTML in tooltips raises XSS surface area.** Mitigation: only resolver output is allowed; resolver escapes textual chunks; merge output is a `SafeString`. No user-supplied content reaches the merge.
- **Class lookup ambiguity (web vs efootprint class names).** Mitigation: provider accepts efootprint class names only; call sites that have the web class translate explicitly via `web_class.efootprint_class.__name__`. A single helper method on the adapter handles both forms to keep call sites short.
- **`field_ui_config.json` already-present tooltips written from a UI-mechanics perspective ("click X").** They will now sit *under* the library description, which can read awkwardly. Mitigation: scan the existing tooltip set as part of this step and rewrite any that are pure UI-mechanics into "interface-context" wording. Small list (count is in the dozens, not hundreds).
- **Fallback path for unscoped fields.** The "parent-group-memberships" field has no class scope. Calling `FieldUIConfigProvider.get_tooltip` directly bypasses the merge — that's correct, but a future contributor might add another unscoped field and silently lose library content. Mitigation: a comment on the fallback branch and a unit test asserting the fallback returns the unscoped tooltip verbatim.

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

- **Scope of initial `interactions` content.** Default plan covers four tour-relevant classes (Server, UsageJourney, UsagePattern, Job). Confirm the list matches the four classes Step 6's tour will hit, or expand if Step 6 has shifted scope. Decide before writing the `class_ui_config.json` entries.
- **Help-drawer URL pattern.** Plan uses `/model_builder/help-drawer/<class_name>/`. If there is an existing convention (e.g. `/model_builder/help/...`) we should follow it. Confirm during implementation.
- **Should the help drawer also offer a "view raw docstring" link (e.g. for power users)?** Out of scope for now, but easy to add later.
