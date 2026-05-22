# Step 5 — Web vs edge in the interface: implementation plan

## Goal

Add a navbar toggle that hides edge object types from the add-menus by default,
revealing them on demand. The toggle is latched on (disabled with a tooltip)
whenever the current model contains any edge object, so a model that legitimately
uses edge never has its edge surface accidentally hidden. Mark edge object cards
with a small coloured dot so industrial users working on mixed models can tell at
a glance which layer a card belongs to.

This step is entirely within the interface repo. It depends on Step 4 only for
the canonical `web_vs_edge.md` Explanation page that the toggle tooltip links to;
the URL is a config value, no library import.

---

## Scope

### Toggle state model

Two inputs combine into one effective state:

| Input | Source | Authority |
|---|---|---|
| User preference | `localStorage["efootprint.edgeModeling"]` ∈ `{"on", "off"}` (default `"off"`) | Browser-local; survives reloads, not tied to the model. |
| Latch | `ModelWeb.has_edge_objects` (server-rendered onto the toggle markup) | Authoritative when `True` — overrides the user preference. |

Effective state on render: `latched OR user_preference == "on"`. When latched, the
toggle is disabled and the latch tooltip is shown instead of the default tooltip.

**Why localStorage (not `interface_config` or session).** Edge modeling is a
per-browser UX preference, not a property of the model. Two users opening the
same shared model may legitimately want different toggle states. Persisting in
`interface_config` would force a migration handler and couple a UI flag to model
export/import for no gain. The latch already covers the only case where the
preference is load-bearing (web-only models with `user_preference == "off"`);
once edge objects exist, the latch wins regardless.

### Edge object classification

Add-menu gating, the card-header dot, and `has_edge_objects` all need a single
"which paradigm does this class belong to?" answer. The cleanest source is a
module-level set built once from `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`:

```python
# model_builder/domain/modeling_paradigm.py (new)
EDGE_EFOOTPRINT_CLASS_NAMES: frozenset[str] = frozenset({
    "EdgeUsagePattern", "EdgeUsageJourney", "EdgeFunction",
    "EdgeDeviceBase", "EdgeDevice", "EdgeDeviceGroup",
    "EdgeComputer", "EdgeComputerCPUComponent", "EdgeComputerRAMComponent",
    "EdgeAppliance", "EdgeApplianceComponent",
    "EdgeComponent", "EdgeCPUComponent", "EdgeRAMComponent",
    "EdgeStorage", "EdgeWorkloadComponent",
    "RecurrentEdgeDeviceNeedBase", "RecurrentServerNeed",
    "RecurrentEdgeProcess", "RecurrentEdgeWorkload",
    "RecurrentEdgeDeviceNeed", "RecurrentEdgeComponentNeed",
    "RecurrentEdgeStorageNeed",
})

def paradigm_for(efootprint_class_name: str) -> str:
    """Return "edge" or "web" for a given efootprint class name."""
    return "edge" if efootprint_class_name in EDGE_EFOOTPRINT_CLASS_NAMES else "web"
```

`ModelingObjectWeb` exposes `modeling_paradigm` as a property returning the
string ("edge" / "web"). Templates emit it as `data-modeling-paradigm` on card
elements and add-buttons (see "Add-menu gating" and "Card badge" below) — using
a `data-*` attribute rather than a marker class because the value is metadata
about the element (what paradigm it belongs to), not a styling classification.
That choice composes cleanly: one attribute drives both the toggle's hide/show
behaviour and the card dot, and future "hybrid" or per-paradigm UX can extend
the same attribute without inventing new marker classes.

A consistency test (see Tests) asserts `EDGE_EFOOTPRINT_CLASS_NAMES` matches
every key in `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING` whose efootprint class
lives under `efootprint/core/usage/edge/` or `efootprint/core/hardware/edge/`
— so adding a new edge class to the mapping without updating the set fails CI.

### Add-menu gating

Top-level edge "Add" buttons in `model_canvas_content.html`:

| Button id | Type | Already wrapped in a stable container? |
|---|---|---|
| `add_edge_usage_pattern` | `EdgeUsagePattern` | No |
| `btn-add-edge-usage-journey` | `EdgeUsageJourney` | No |
| `btn-add-edge-device` | `EdgeDeviceBase` | No |
| `btn-add-edge-device-group` | `EdgeDeviceGroup` | No |

Gating mechanism: tag each edge add button with the
`data-modeling-paradigm="edge"` attribute (the same attribute the card dot
keys off — see "Card badge"). A small piece of CSS keyed off
`body.edge-modeling-off` hides every `[data-modeling-paradigm="edge"]`
descendant within `#model-canva`; `body.edge-modeling-on` shows them. The body
class is set by the same JS module that owns the toggle (see "JS module"
below) so localStorage state alone drives visibility — no server re-render
required when the user flips the toggle. This is consistent with constitution
§1.4 (HTMX-first; minimize JS): the only JS is the small handler that
reads/writes localStorage and toggles a body class.

The selector is scoped to `#model-canva` so the navbar toggle markup itself
(which also gets `data-modeling-paradigm` semantics via the surrounding label)
is never accidentally hidden by its own rule.

Child "Add" buttons inside edge cards (e.g. `RecurrentServerNeed` on an edge
device card) do **not** need gating: if the parent edge card is visible, the
model already contains edge objects, so the latch guarantees the toggle is on.

### Latch and toggle OOB re-render

When a mutation flips `has_edge_objects` (first edge object created, last edge
object deleted), the toggle's disabled/enabled state and its popover must
update. Reuse the side-effects OOB pattern established in Step 1:

- Add an `edge_modeling_toggle` OOB region renderer in `oob_regions.py` that
  re-renders the toggle partial via
  `hx-swap-oob="outerHTML:#edge-modeling-toggle-wrapper"`.
- In `ModelingObjectWeb._recompute_state_and_emit_oob_regions` (or a sibling
  helper invoked from the same `*_side_effects` instance methods), detect a
  flip of `has_edge_objects` and append the OOB region. The check is cheap
  (a property read) and only fires on create/delete, not edit.

The IoT starter template (Step 6, sub-phase A) ships with edge objects already
present in the loaded system, so the latch fires automatically on first render
— no template-specific flag.

### Card badge

`button_card_header.html` is the single insertion point used by every object
card. Two changes:

1. Emit `data-modeling-paradigm="{{ object_card.modeling_paradigm }}"` on the
   header element only when the paradigm is `"edge"` (keeping the markup tight
   — default web case stays attribute-free). This is the same metadata
   attribute the add-button gating reads.
2. Render a small dot span when the paradigm is `"edge"`:

```html
{% if object_card.modeling_paradigm == "edge" %}
<span class="modeling-paradigm-dot rounded-circle d-inline-block ms-2"
      data-bs-toggle="popover" data-bs-trigger="hover focus"
      data-bs-placement="top" data-bs-custom-class="blue-popover"
      data-bs-content="Edge object — part of the edge modeling layer (vs. web)."></span>
{% endif %}
```

`.modeling-paradigm-dot` is a pure styling primitive (size, colour). The
"which paradigm" classification lives on the parent's `data-modeling-paradigm`
attribute, not in the dot's class name. Size: ~8px. Colour: reuse an existing
SCSS palette token (see "Static assets" → SCSS).

### Toggle markup

**Host.** The toggle lives inside `#navbarSupportedContent` in
`model_builder/templates/model_builder/upload_download_reboot_model_tooltips.html`
— the collapsible nav-bar section that already hosts Import / Export / Reset /
Show results. Same template covers desktop and mobile (on mobile, it collapses
into the hamburger menu like the other toolbar items), so one host serves both
form factors with no separate mobile wiring.

**Partial.**
`model_builder/templates/model_builder/components/edge_modeling_toggle.html` —
**new**. Rendered as one of the `<li class="nav-item">` entries in the
existing `<ul class="navbar-nav">`, alongside Import/Export. Gated by
`{% if model_web %}` so pages without a model in context don't render it.

```html
{% if model_web %}
<li id="edge-modeling-toggle-wrapper" class="nav-item d-flex align-items-center mx-2">
    <div class="form-check form-switch mb-0 d-flex align-items-center">
        {% if model_web.has_edge_objects %}
            <input class="form-check-input me-2" type="checkbox" role="switch"
                   id="edge-modeling-toggle" checked disabled
                   data-bs-toggle="popover" data-bs-trigger="hover focus"
                   data-bs-placement="bottom" data-bs-custom-class="blue-popover"
                   data-bs-content="This model contains edge objects. Remove them to turn edge modeling off." />
        {% else %}
            <input class="form-check-input me-2" type="checkbox" role="switch"
                   id="edge-modeling-toggle" />
        {% endif %}
        <label class="form-check-label me-1 mb-0" for="edge-modeling-toggle">Edge modeling</label>
        {% if not model_web.has_edge_objects %}
            {# Question-circle popover with the canonical web_vs_edge.md link. #}
            <svg data-bs-toggle="popover" data-bs-trigger="hover focus"
                 data-bs-html="true" data-bs-placement="bottom"
                 data-bs-custom-class="blue-popover"
                 data-bs-content='Edge modeling adds support for deployed-device impact (IoT, sensors, industrial PCs). <a href="{{ EDGE_MODELING_DOC_URL }}" target="_blank" rel="noopener noreferrer">Learn more</a>.'
                 xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                 fill="currentColor" class="bi bi-question-circle" viewBox="0 0 16 16">
                <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/>
                <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286m1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94"/>
            </svg>
        {% endif %}
    </div>
</li>
{% endif %}
```

Two notes:
- **Popover, not tooltip.** Matches the established pattern in
  `side_panels/components/tooltip.html` (`bi-question-circle` SVG +
  `data-bs-toggle="popover"` + `data-bs-custom-class="blue-popover"`).
  `data-bs-html="true"` on the question-circle popover lets the "Learn more"
  link be a real clickable `<a>`. The latched-state popover (on the input)
  uses plain text — no link needed.
- **`EDGE_MODELING_DOC_URL`** is a Django settings constant pointing at the
  published mkdocs URL for `web_vs_edge.md`. Made available in templates via a
  small context processor (or passed explicitly from the views that render
  the toolbar — pick whichever is more consistent with existing settings
  injection).

**Insertion point.** Recommend placing the toggle as the first nav item (left
of Import) so it reads as a global modeling-mode setting before the
file-action items. Final position confirmed during implementation by visual
review.

**OOB region target.** The wrapper id is `#edge-modeling-toggle-wrapper`; the
`edge_modeling_toggle` OOB region uses
`hx-swap-oob="outerHTML:#edge-modeling-toggle-wrapper"`, re-rendering the
same partial standalone. The toolbar template (`upload_download_reboot_model_tooltips.html`)
is itself outside `#model-canva`, so the existing constraint-diff OOB
regions don't touch it — this new region is independent and only fires when
`has_edge_objects` flips.

The upper `theme/templates/navbar.html` is **not** touched by this step.

### JS module

`theme/static/scripts/edge_modeling_toggle.js` (new), wired in `base.html`
alongside other utility scripts. IIFE module following the convention used by
`help_drawer_utils.js` (constitution-compatible pattern, see `architecture.md` →
"Help drawer is an independent overlay layer"). Responsibilities:

1. On `DOMContentLoaded` and on `htmx:afterSettle`: read the toggle's `checked`
   state (server-rendered from the latch) and `localStorage`; compute effective
   state; set `document.body.classList` to `edge-modeling-on` /
   `edge-modeling-off`; sync the `checked` attribute on the (possibly newly
   swapped-in) toggle to the effective state.
2. On `change` of `#edge-modeling-toggle` (only fires when not disabled — i.e.,
   when not latched): write the new value to localStorage and update body
   classes. No HTMX request needed.
3. After an OOB swap of `#navbar-edge-toggle`: the `htmx:afterSettle` handler
   re-runs step 1, so the latched-state markup wins automatically.

No new JS framework or dependency. Bootstrap tooltips are re-initialized by the
existing `initModelBuilderMain` flow after OOB settles.

---

## Files to change

### Domain

1. `model_builder/domain/modeling_paradigm.py` — **new**. Exports
   `EDGE_EFOOTPRINT_CLASS_NAMES: frozenset[str]` and
   `paradigm_for(efootprint_class_name: str) -> str` returning `"edge"` or
   `"web"`.
2. `model_builder/domain/entities/web_core/model_web.py` — add `has_edge_objects`
   property: returns `True` if any of the existing edge accessors is
   non-empty. Implementation should not enumerate accessors by hand — iterate
   `EDGE_EFOOTPRINT_CLASS_NAMES` and call
   `get_web_objects_from_efootprint_type(name)`, return True on the first
   non-empty result.
3. `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py`
   — add `modeling_paradigm` property: returns
   `paradigm_for(self.modeling_obj.class_as_simple_str)`.
4. `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py`
   — extend `_recompute_state_and_emit_oob_regions` (or sibling helper) to
   also detect a `has_edge_objects` flip and append the `navbar_edge_toggle` OOB
   region. The check compares `model_web.has_edge_objects` before vs. after the
   mutation; cache the pre-mutation value the same way constraints are cached.

### Adapter / presenter

5. `model_builder/adapters/presenters/oob_regions.py` — add an
   `edge_modeling_toggle` region renderer:
   `hx-swap-oob="outerHTML:#edge-modeling-toggle-wrapper"`, re-rendering the
   `edge_modeling_toggle.html` partial standalone.
6. `theme/settings.py` — add `EDGE_MODELING_DOC_URL` (string, mkdocs URL for the
   `web_vs_edge.md` page) and a context processor that injects it into
   template context for the relevant views (or pass it explicitly from
   `model_builder_main` / `upload_json`).

### Templates

7. `model_builder/templates/model_builder/components/edge_modeling_toggle.html`
   — **new** partial (markup shown in "Toggle markup" above). Included by the
   toolbar template (#8) and rendered standalone by the OOB renderer (#5).
8. `model_builder/templates/model_builder/upload_download_reboot_model_tooltips.html`
   — include the partial as a new `<li class="nav-item">` inside the existing
   `<ul class="navbar-nav">`, recommended as the first item (left of Import).
   No change to `theme/templates/navbar.html` — the upper logo+GitHub navbar
   is unchanged.
9. `model_builder/templates/model_builder/components/model_canvas_content.html`
   — add `data-modeling-paradigm="edge"` to the four edge top-level
   add-buttons (lines 7, 22, 39, 40). No conditional rendering — CSS handles
   the hide.
10. `model_builder/templates/model_builder/components/button_card_header.html`
    — emit `data-modeling-paradigm="edge"` on the header element and render
    the `.modeling-paradigm-dot` span when
    `object_card.modeling_paradigm == "edge"`.

### Static assets

11. `theme/static/scripts/edge_modeling_toggle.js` — **new** IIFE module (see
    "JS module" above).
12. `theme/templates/base.html` (or wherever scripts are wired) — `<script>`
    tag for the new module.
13. `theme/static/scss/_model_builder.scss` (or sibling) — add:
    - `body.edge-modeling-off #model-canva [data-modeling-paradigm="edge"] { display: none; }`
    - `.modeling-paradigm-dot { width: 8px; height: 8px; background-color: <existing-palette-token>; }`
      where `<existing-palette-token>` is whatever SCSS variable in the
      current palette already reads as "edge / secondary accent." If no
      fitting token exists, raise it during implementation — do **not**
      introduce a new colour variable speculatively. The point is to avoid
      expanding the palette for a single dot.

---

## Tests

### Unit — `tests/unit_tests/domain/test_model_web_edge.py` (new)

- `has_edge_objects` returns `False` on a freshly-built web-only model
  (UsageJourney + UsagePattern + Server + Job).
- `has_edge_objects` returns `True` when the model contains an
  `EdgeUsagePattern` but no edge devices.
- `has_edge_objects` returns `True` when the model contains an `EdgeDevice` but
  no edge usage patterns.
- `has_edge_objects` returns `True` for a mixed system (web + edge +
  `RecurrentServerNeed` bridge).

### Unit — `tests/unit_tests/domain/test_modeling_paradigm_consistency.py` (new)

- `EDGE_EFOOTPRINT_CLASS_NAMES` ⊆ keys of `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`.
- For every key in `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`, the
  `efootprint` class's module path lies under `efootprint/core/usage/edge/`
  or `efootprint/core/hardware/edge/` iff the key is in
  `EDGE_EFOOTPRINT_CLASS_NAMES`. Catches drift when new edge classes appear
  in the mapping without being added to the set.
- `paradigm_for("EdgeDevice") == "edge"` and `paradigm_for("Server") == "web"`.
- For each `web_class` value, instances expose `modeling_paradigm` returning
  the expected string.

### Integration — `tests/integration/test_edge_modeling_toggle_oob.py` (new)

Following the Step 1 constraint-change OOB pattern; no browser, uses
`InMemorySystemRepository` + `ModelWeb`:

- Creating the first edge object (`EdgeDevice`) on a previously web-only model
  emits an `edge_modeling_toggle` OOB region.
- Deleting the last edge object on a previously edge-bearing model emits an
  `edge_modeling_toggle` OOB region.
- Edits that don't change `has_edge_objects` do not emit the region.
- Subclass overrides of `*_side_effects` (`EdgeDeviceGroupWeb`,
  `EdgeDeviceBaseWeb`, `EdgeComponentBaseWeb`) preserve the
  `edge_modeling_toggle` region via the super-call pattern.

### E2E — `tests/e2e/test_edge_modeling_toggle.py` (new, narrow)

One end-to-end happy-path test (Playwright):

- Start on the blank model: edge add buttons are not visible; toolbar toggle
  is unchecked and enabled.
- Flip the toggle on: edge add buttons become visible; localStorage updated.
- Add an `EdgeDevice`: toggle becomes disabled, popover content updated
  (assert the short-variant exact string).
- Try to flip the toggle off: the input is disabled (Playwright assertion).
- Delete the `EdgeDevice`: toggle becomes enabled again, reflects the
  previous localStorage state (on), edge add buttons remain visible.
- Manually set `localStorage["efootprint.edgeModeling"] = "off"`, reload page:
  edge add buttons hidden again.

### Jest — `tests/jest/edge_modeling_toggle.test.js` (new)

- localStorage round-trip: writing `"on"` and reading sets `body` class
  correctly.
- When the input is rendered with `checked disabled` (latched state), the
  module forces body class to `edge-modeling-on` and ignores localStorage.

---

## Open questions

- **Exact toolbar insertion point.** Plan recommends "first item in the nav
  list (left of Import)". Confirm at implementation start by visual review.
- **SCSS palette token for the dot.** Implementation picks the existing token
  that best fits "edge accent." Only escalate (and introduce a new variable)
  if no existing token works.

---

## Out of scope

- Filtering existing edge object cards (the latch guarantees that if edge cards
  exist, the toggle is on, so cards always render).
- Re-rendering the toggle on the home page or upload page (toggle only appears
  when `model_web` is in context).
- A separate column or layout change for edge — explicitly rejected in
  `03-web-vs-edge-modeling.md`.
- Help drawer / `DescriptionProvider` content for edge classes — that lives in
  Step 3 (SSOT in the interface) and is consumed automatically once the library
  metadata exists.
- Library-side `web_vs_edge.md` content — owned by Step 4.

---

## Constitutional and architectural notes

- **§1.1 (Clean Architecture).** The domain layer additions
  (`EDGE_EFOOTPRINT_CLASS_NAMES`, `has_edge_objects`, `is_edge`) are pure
  Python with no Django imports. Templates and the OOB renderer live in
  adapters. JS in `theme/static/`.
- **§1.3 (library is the truth).** `is_edge` is derived from the efootprint
  class name, not redefined here. `EDGE_EFOOTPRINT_CLASS_NAMES` is a set the
  interface maintains because the library doesn't currently expose a
  programmatic "is this an edge class?" predicate; if/when it does, the set
  becomes a derived constant.
- **§1.4 (HTMX-first; minimize JS).** The only JS added is the small
  localStorage/body-class module. Toggling visibility is CSS-driven; the latch
  is server-rendered.
- **`architecture.md` → "Creation prerequisites and disabled UX".** This step
  extends the same `*_side_effects` OOB-region pattern with a new region
  (`edge_modeling_toggle`). Documentation update suggested in the
  implementation summary: add one paragraph about `has_edge_objects` and the
  `edge_modeling_toggle` region under that section.
- **Constitution §4 (mobile best-effort).** The toolbar template
  (`upload_download_reboot_model_tooltips.html`) already serves both desktop
  and mobile (collapsing into a hamburger on small screens). Hosting the
  toggle there means mobile and desktop get the same affordance with one
  include — no separate mobile wiring needed.
