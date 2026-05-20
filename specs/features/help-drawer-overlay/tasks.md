# Help drawer overlay — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.md`](spec.md). **Plan:** [`plan.md`](plan.md).

## Task 1 — Help drawer becomes an overlay; canvas "?" button stops destroying the side panel

**Status:** Done.

**Goal:** Land the `#helpDrawer` overlay layer, reparent `class_help.html` onto a dedicated structure, route the canvas `?` buttons to it, and add the auto-close behavior when a side panel opens. After this task ships, the help drawer is non-destructive from its first real entry point and the system is fully working — the only remaining entry point still using the old path is the in-tooltip `{class:X}` link (handled in Task 2, which is also where the original bug is fixed).

**Files touched:**
- `model_builder/templates/model_builder/model_builder_main.html` — add `<div id="helpDrawer" class="d-none ...">` as sibling of `#sidePanel`, higher `z-index`, same column footprint.
- `model_builder/templates/model_builder/help_drawer/help_drawer_structure.html` — **new**. Title, close cross include, body block, popover init scoped to `[data-location="help_drawer"]`. No save apparatus. Calls `openHelpDrawer()` on render.
- `model_builder/templates/model_builder/help_drawer/components/close_help_drawer_cross.html` — **new**. Cross button calling `closeHelpDrawer()`.
- `model_builder/templates/model_builder/help_drawer/class_help.html` — extend the new structure; drop the empty `save_button` block.
- `model_builder/templates/model_builder/components/add_object_button.html` — change the `?` button's `hx-target` from `#sidePanel` to `#helpDrawer`.
- `theme/static/scripts/side_panel_utils.js` — add `openHelpDrawer()` / `closeHelpDrawer()` (mirroring their side-panel counterparts but operating only on `#helpDrawer`; no `formModified` touch); add an `htmx:afterSwap` listener that calls `closeHelpDrawer()` whenever a swap targets `#sidePanel`.
- CSS / inline classes for `#helpDrawer` width and `z-index` (likely inline classes on the container, matching the side-panel pattern).

**Tests added/changed:**
- `tests/e2e/test_help_drawer_overlay.py` — **new**. Two scenarios:
  - With an edit panel open and dirty, clicking `?` on a canvas Add button opens the help overlay on top, does not fire the unsaved-changes modal, and closing the cross returns the user to the edit form with changes intact (`formModified` still `true`).
  - With the help drawer open, clicking any Add button auto-closes the help drawer and shows the new side panel.
- Confirm existing unsaved-changes E2E (`tests/e2e/test_forms.py`) still passes — side-panel-to-side-panel transitions are untouched.

**Acceptance:**
- Canvas `?` button never destroys an open edit form and never triggers the unsaved-changes modal.
- Opening any side panel while the help drawer is open auto-closes the help drawer.
- All existing tests still green.

**Depends on:** none.

---

## Task 2 — Fix the in-tooltip `{class:X}` link via delegated click + handle_class rewrite

**Goal:** Resolve the original bug. The `{class:X}` placeholder in field tooltips no longer renders a navigable `href`; a single document-level delegated listener intercepts `.help-drawer-trigger` clicks (works regardless of which DOM subtree Bootstrap popovers inject the markup into) and opens the help drawer overlay via `htmx.ajax` into `#helpDrawer`. Internal help-to-help navigation works for free.

**Files touched:**
- `model_builder/adapters/ui_config/interface_placeholder_handlers.py` — rewrite `handle_class` to emit `<a href="#" class="help-drawer-trigger" data-help-class="X" role="button">label</a>`. No `hx-get`, no `hx-target`.
- `theme/static/scripts/side_panel_utils.js` — delegated `click` listener on `document.body` matching `.help-drawer-trigger`: `preventDefault`, dismiss any open Bootstrap popover/tooltip containing the trigger, then `htmx.ajax('GET', '/model_builder/open-help-drawer/' + className + '/', {target: '#helpDrawer', swap: 'innerHTML'})`.
- `specs/architecture.md` — one-line note in the render-layer section about the independent help-drawer layer.
- `CHANGELOG.md` — one entry under "Fixed" for the tooltip-link bug and one under "Changed" for the overlay behavior.

**Tests added/changed:**
- `tests/unit_tests/adapters/ui_config/test_interface_placeholder_handlers.py` — update `test_html_class_handler_emits_anchor_with_label`: assert `class="help-drawer-trigger"`, `data-help-class="Server"`, label present, and that the markup contains neither `hx-get` nor a real navigable URL.
- `tests/e2e/test_help_drawer_overlay.py` — extend with:
  - The original bug: open an edit panel containing a field whose tooltip has a `{class:X}` link → hover the tooltip → click the link → assert help drawer visible, page URL unchanged, edit form still in DOM, close cross works, edit form restored.
  - Help-to-help navigation: from an open help drawer, click an inner `{class:Y}` link → drawer content swaps, no unsaved-changes modal fires, side panel underneath untouched.

**Acceptance:**
- Clicking a `{class:X}` link inside a field tooltip opens the help drawer overlay; the browser URL does not change.
- Help-to-help navigation works without firing the unsaved-changes modal.
- Unit + E2E suites green.

**Depends on:** Task 1 (relies on `#helpDrawer` and `openHelpDrawer`/`closeHelpDrawer`).

---

## Ordering rationale

The two tasks split at the only meaningful behavioural pause point: Task 1 ships the overlay layer with one entry point (the canvas `?` button, simplest to migrate) and the auto-close glue, leaving a fully working system; Task 2 then swaps the second, more failure-prone entry point (`handle_class` placeholder) over to the same overlay via a delegated listener, which is also where the original bug is resolved. Combining them would muddle the review surface — Task 1 is mostly new templates and a one-line `hx-target` swap, Task 2 is a Python handler rewrite plus a delegated JS listener with its own subtle interactions (popover dismissal, escaping, scope). Splitting further (separate scaffolding / template / migration / auto-close tasks) would create review boundaries with no behavioural pause point — those atomic units have no value individually and are kept together per the skill's "tightly-coupled units" criterion.
