# Step 5 — Web vs edge in the interface: tasks

**Status:** Tasks — under review.
**Plan:** [`step-05-edge-interface.md`](step-05-edge-interface.md).
**Spec context:** [`03-web-vs-edge-modeling.md`](03-web-vs-edge-modeling.md), [`05-maintainability-and-build.md`](05-maintainability-and-build.md) (Step 5 row), [`99-roadmap.md`](99-roadmap.md) (Step 5).

**Prerequisite (verify before Task 1):** Step 4's `web_vs_edge.md` Explanation page is either landed or has a stable mkdocs URL agreed upon — only the URL is consumed here (via `EDGE_MODELING_DOC_URL`), so this step is not blocked on Step 4's content being written, only on the URL being knowable.

---

## Task 1 — Edge paradigm domain foundation

**Goal:** Land the paradigm classification primitives (`EDGE_EFOOTPRINT_CLASS_NAMES`, `paradigm_for`, `ModelWeb.has_edge_objects`, `ModelingObjectWeb.modeling_paradigm`) and their unit + consistency tests. No template, JS, CSS, settings, or OOB wiring — pure domain layer. After this PR the helpers are importable and tested, but no user-visible behaviour changes.

**Files touched:**
- `model_builder/domain/modeling_paradigm.py` — **new**. Exports `EDGE_EFOOTPRINT_CLASS_NAMES: frozenset[str]` (the 23-name set listed verbatim in the plan §"Edge object classification") and `paradigm_for(efootprint_class_name: str) -> str` returning `"edge"` or `"web"`. No Django imports.
- `model_builder/domain/entities/web_core/model_web.py` — add `has_edge_objects` property. Implementation iterates `EDGE_EFOOTPRINT_CLASS_NAMES` and calls `get_web_objects_from_efootprint_type(name)`, returning `True` on the first non-empty result (do not enumerate accessors by hand).
- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` — add `modeling_paradigm` property returning `paradigm_for(self.modeling_obj.class_as_simple_str)`. **Do not** extend `_recompute_constraints_and_emit_regions` here — the OOB hook lands in Task 2 alongside its renderer.

**Tests added/changed:**
- `tests/unit_tests/domain/test_model_web_edge.py` — **new**. Per plan §"Tests" → Unit:
  - `has_edge_objects` returns `False` on a freshly-built web-only model (UsageJourney + UsagePattern + Server + Job).
  - `has_edge_objects` returns `True` with only an `EdgeUsagePattern`.
  - `has_edge_objects` returns `True` with only an `EdgeDevice`.
  - `has_edge_objects` returns `True` for a mixed system (web + edge + `RecurrentServerNeed` bridge).
- `tests/unit_tests/domain/test_modeling_paradigm_consistency.py` — **new**. Per plan §"Tests":
  - `EDGE_EFOOTPRINT_CLASS_NAMES` ⊆ keys of `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`.
  - For every key in the mapping, the efootprint class's module path lies under `efootprint/core/usage/edge/` or `efootprint/core/hardware/edge/` iff the key is in `EDGE_EFOOTPRINT_CLASS_NAMES` (catches drift when new edge classes appear without being added to the set).
  - `paradigm_for("EdgeDevice") == "edge"` and `paradigm_for("Server") == "web"`.
  - For each `web_class` in the mapping, instances expose `modeling_paradigm` returning the expected string.

**Acceptance:**
- `pytest tests/unit_tests/domain/test_model_web_edge.py tests/unit_tests/domain/test_modeling_paradigm_consistency.py` passes.
- `pytest tests/unit_tests/` passes (no regressions elsewhere).
- `python manage.py check` passes.
- `EDGE_EFOOTPRINT_CLASS_NAMES`, `paradigm_for`, `ModelWeb.has_edge_objects`, and `ModelingObjectWeb.modeling_paradigm` are importable and exercised by tests; no call site consumes them yet, so user-visible behaviour is unchanged.

**Depends on:** none.

---

## Task 2 — Edge modeling toggle, latch, card badge

**Goal:** Ship the full user-visible edge modeling surface end-to-end. Navbar toggle with localStorage-driven hide/show of edge add-buttons, latching when the model already contains edge objects (server-rendered + OOB re-rendered on flip), the question-circle popover linking to `EDGE_MODELING_DOC_URL`, and the coloured dot on edge object cards. After this PR a user can toggle edge modeling on/off, see edge cards marked, and have the toggle latched on as soon as an edge object exists.

**Files touched:**

*Domain (OOB hook only):*
- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` — extend `_recompute_constraints_and_emit_regions` (or sibling helper invoked from the same `*_side_effects` instance methods) to detect a `has_edge_objects` flip (pre-mutation vs. post-mutation, caching the pre-mutation value the same way constraints are cached) and append the `edge_modeling_toggle` OOB region only when it flips.

*Adapter / presenter:*
- `model_builder/adapters/presenters/oob_regions.py` — add `edge_modeling_toggle` region renderer using `hx-swap-oob="outerHTML:#edge-modeling-toggle-wrapper"`, re-rendering the `edge_modeling_toggle.html` partial standalone.
- `theme/settings.py` — add `EDGE_MODELING_DOC_URL` (env-overridable, sensible default pointing at the mkdocs `web_vs_edge.md` URL).
- Context processor (new or existing — pick whichever is more consistent with current settings injection) to expose `EDGE_MODELING_DOC_URL` to templates that render the toolbar.

*Templates:*
- `model_builder/templates/model_builder/components/edge_modeling_toggle.html` — **new** partial. Markup per plan §"Toggle markup": `<li id="edge-modeling-toggle-wrapper" class="nav-item …">` with a Bootstrap switch input. Two branches: latched (`checked disabled` + plain-text latch popover) vs. unlatched (input + `bi-question-circle` SVG popover with `data-bs-html="true"` containing the `EDGE_MODELING_DOC_URL` link). Whole partial gated by `{% if model_web %}`.
- `model_builder/templates/model_builder/upload_download_reboot_model_tooltips.html` — include the partial as the first `<li class="nav-item">` in the existing `<ul class="navbar-nav">` (recommended position; confirm at implementation by visual review). No change to `theme/templates/navbar.html`.
- `model_builder/templates/model_builder/components/model_canvas_content.html` — add `data-modeling-paradigm="edge"` to the four edge top-level add-buttons (`add_edge_usage_pattern`, `btn-add-edge-usage-journey`, `btn-add-edge-device`, `btn-add-edge-device-group`). No conditional rendering — CSS handles the hide.
- `model_builder/templates/model_builder/components/button_card_header.html` — emit `data-modeling-paradigm="{{ object_card.modeling_paradigm }}"` on the header element only when paradigm is `"edge"` (default web case stays attribute-free), and render the `.modeling-paradigm-dot` popover span when paradigm is `"edge"` (markup per plan §"Card badge").

*Static assets:*
- `theme/static/scripts/edge_modeling_toggle.js` — **new** IIFE module following the `help_drawer_utils.js` convention. On `DOMContentLoaded` and `htmx:afterSettle`: read the toggle's server-rendered `checked` state + localStorage, compute effective state (`latched OR user_preference == "on"`), set `document.body.classList` to `edge-modeling-on` / `edge-modeling-off`, sync the toggle's `checked` to the effective state. On `change` of `#edge-modeling-toggle` (only fires when not disabled): write `"on"`/`"off"` to `localStorage["efootprint.edgeModeling"]` and update the body class.
- `theme/templates/base.html` (or wherever utility scripts are wired) — `<script>` tag for the new module.
- `theme/static/scss/_model_builder.scss` (or sibling) — add `body.edge-modeling-off #model-canva [data-modeling-paradigm="edge"] { display: none; }` and `.modeling-paradigm-dot { width: 8px; height: 8px; background-color: <existing-palette-token>; border-radius: 50%; }`. Reuse an existing SCSS palette token for the dot colour; only escalate (and introduce a new variable) if no existing token reads as "edge / secondary accent."

*Documentation:*
- `specs/architecture.md` — add one short paragraph under the "Creation prerequisites and disabled UX" section noting `has_edge_objects` and the `edge_modeling_toggle` OOB region as a sibling of the constraint-diff OOB pattern.

**Tests added/changed:**
- `tests/integration/test_edge_modeling_toggle_oob.py` — **new**. Following the Step 1 constraint-change OOB pattern (`InMemorySystemRepository` + `ModelWeb`, no browser):
  - Creating the first edge object (`EdgeDevice`) on a previously web-only model emits an `edge_modeling_toggle` OOB region.
  - Deleting the last edge object on a previously edge-bearing model emits the region.
  - Edits that don't change `has_edge_objects` do not emit the region.
  - Subclass overrides of `*_side_effects` (`EdgeDeviceGroupWeb`, `EdgeDeviceBaseWeb`, `EdgeComponentBaseWeb`) preserve the region via the super-call pattern.
- `tests/e2e/test_edge_modeling_toggle.py` — **new**, narrow Playwright happy-path:
  - Start on the blank model: edge add buttons not visible; toolbar toggle unchecked and enabled.
  - Flip the toggle on: edge add buttons become visible; `localStorage["efootprint.edgeModeling"] === "on"`.
  - Add an `EdgeDevice`: toggle becomes disabled, latch popover content matches the latched-string fixture.
  - Try to flip the toggle off: input is disabled (Playwright assertion).
  - Delete the `EdgeDevice`: toggle becomes enabled, reflects previous localStorage state (`on`), edge add buttons remain visible.
  - Set `localStorage["efootprint.edgeModeling"] = "off"` and reload: edge add buttons hidden again.
- `tests/jest/edge_modeling_toggle.test.js` — **new**:
  - localStorage round-trip: writing `"on"` and reading sets `body.edge-modeling-on`.
  - When the input is rendered `checked disabled` (latched), the module forces `body.edge-modeling-on` and ignores localStorage.

**Acceptance:**
- `pytest tests/unit_tests tests/integration` passes (in particular `tests/integration/test_edge_modeling_toggle_oob.py`).
- `pytest tests/e2e/test_edge_modeling_toggle.py` passes against a running server.
- `npm run jest` passes (in particular `tests/jest/edge_modeling_toggle.test.js`).
- `npm run build:result-charts:dev` (or whichever SCSS build target the dev workflow uses) compiles cleanly.
- Manually walk the E2E happy-path in a browser on both desktop and a mobile-width viewport (toolbar collapses into the hamburger). **Attach screenshots to the PR**: (a) toggle off — no edge buttons; (b) toggle on — edge buttons visible; (c) latched — disabled toggle with popover; (d) a card with the edge dot. If the dot colour reads ambiguously next to existing card chrome, file a follow-up rather than blocking.
- `specs/architecture.md` gains the paragraph on `has_edge_objects` / `edge_modeling_toggle`.

**Depends on:** Task 1 (consumes `EDGE_EFOOTPRINT_CLASS_NAMES`, `has_edge_objects`, `modeling_paradigm`).

---

## Ordering rationale

Task 1 lands the domain primitives behind no user-visible change — paradigm classification, `has_edge_objects`, `modeling_paradigm`, and their unit + consistency tests. Splitting these from their consumer is the natural "infrastructure unused" pause point: the classification set is the load-bearing piece of the whole step and the consistency test guards future drift, so reviewing it in isolation pays off.

Task 2 is one cohesive user-visible delivery. Toggle, latch, OOB region, card dot, gating CSS, JS, and settings are deliberately bundled: they all key off the same `data-modeling-paradigm` attribute and the single localStorage flag, and there is no meaningful behavioural pause point between "card dot visible" and "toggle works" — shipping the dot without the toggle would advertise a paradigm distinction the user can't yet act on, and shipping the toggle without the dot would leave mixed-model users without the per-card affordance the plan explicitly motivates. The OOB hook on `_recompute_constraints_and_emit_regions` lands in Task 2 (not Task 1) because it has no consumer until the OOB renderer in `oob_regions.py` and the toggle wrapper id `#edge-modeling-toggle-wrapper` also exist — splitting them would leave a half-wired call site.
