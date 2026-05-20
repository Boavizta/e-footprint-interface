# Implementation plan — help drawer overlay

**Status:** Plan.
**Date:** 2026-05-20.
**Depends on:** [`spec.md`](spec.md).

## 1. Approach

Introduce a second right-column container, `#helpDrawer`, that is a sibling of `#sidePanel` inside `model-builder-page`. Both occupy the same column visually; the help drawer sits on a higher `z-index` and is shown/hidden via the same `d-none` / width classes the side panel already uses. The side-panel DOM is never touched by help-drawer flows.

All help-drawer entry points are switched to target `#helpDrawer` via `hx-target`. The bug-source `<a href=...>` rendered by `handle_class` is replaced by a real HTMX-aware element that works **even when injected into a Bootstrap popover subtree** — by means of a single delegated click listener on `document.body` that intercepts `.help-drawer-trigger` clicks and calls `htmx.ajax('GET', url, '#helpDrawer')`. This sidesteps the "popover content not processed by HTMX" issue once and for all.

A new `help_drawer_structure.html` template mirrors `side_panel_structure.html` minus the form/save apparatus: title, cross button, body block, popover init scoped to `#helpDrawer`. `class_help.html` is reparented onto it.

Closing the help drawer empties `#helpDrawer` only. The side panel underneath, if any, is untouched. Opening any side panel (an HTMX swap into `#sidePanel`) triggers an auto-close of the help drawer via an `htmx:beforeRequest` listener.

## 2. Affected files

### Templates
- `model_builder/templates/model_builder/model_builder_main.html` — add `<div id="helpDrawer">` sibling to `#sidePanel`.
- `model_builder/templates/model_builder/help_drawer/class_help.html` — change `{% extends ... side_panel_structure.html %}` to extend the new `help_drawer_structure.html`. Drop `{% block save_button %}{% endblock %}` (the new structure has no save apparatus).
- `model_builder/templates/model_builder/help_drawer/help_drawer_structure.html` — **new**. Title + close cross + popover init scoped to `#helpDrawer`. No form/save block. Calls `openHelpDrawer()` on render.
- `model_builder/templates/model_builder/help_drawer/components/close_help_drawer_cross.html` — **new**. Cross button calling `closeHelpDrawer()`. (Mirrors `close_side_panel_cross.html` but never warns — closing help is not destructive.)
- `model_builder/templates/model_builder/components/add_object_button.html` — change `hx-target="#sidePanel"` on the `?` button (line 36) to `hx-target="#helpDrawer"`.

### Python adapters
- `model_builder/adapters/ui_config/interface_placeholder_handlers.py` — `handle_class` no longer emits a real `href`. It emits e.g. `<button type="button" class="help-drawer-trigger" data-help-class="X">label</button>` (or an `<a>` with `href="#"` if styling demands it). The class hook and `data-help-class` are what the delegated listener uses. Drop `hx-get`/`hx-target` from the markup — they're inert in popovers anyway, and the delegated listener now drives the request.
- `tests/unit_tests/adapters/ui_config/test_interface_placeholder_handlers.py` — update `test_html_class_handler_emits_anchor_with_label` to match the new markup shape.

### JS
- `theme/static/scripts/side_panel_utils.js` — **new functions**: `openHelpDrawer()`, `closeHelpDrawer()`. Mirror their side-panel counterparts but operate on `#helpDrawer`. `closeHelpDrawer()` empties content, applies `d-none`. No `formModified` reset (help drawer has no form).
- `theme/static/scripts/side_panel_utils.js` — **delegated click listener** on `document.body` for `.help-drawer-trigger`. `event.preventDefault()`, read `data-help-class`, call `htmx.ajax('GET', '/model_builder/open-help-drawer/' + className + '/', { target: '#helpDrawer', swap: 'innerHTML' })`. Also dismisses any visible popover/tooltip so the user sees the help drawer cleanly.
- `theme/static/scripts/side_panel_utils.js` — **auto-close on side-panel open**: extend the existing `htmx:beforeRequest` listener so any successful request with `hx-target === '#sidePanel'` triggers `closeHelpDrawer()` (fires on `htmx:afterSwap` to avoid races with the unsaved-changes modal).

### CSS
- Wherever `#sidePanel` width/transition classes live (Bootstrap utilities used inline today), add equivalents for `#helpDrawer`. Likely a one-line addition in a shared SCSS file or inline classes on the container. Help drawer needs a higher `z-index` than the side panel so it visibly covers it.

### Tests
- Update `tests/unit_tests/adapters/ui_config/test_interface_placeholder_handlers.py` for the new markup.
- Add `tests/unit_tests/adapters/views/test_views_help.py` assertion that the view returns the help-drawer-structure-based template (already covered? confirm during task).
- Add an E2E test in `tests/e2e/` covering: open edit panel → modify field → click `{class:X}` link in tooltip → help drawer opens on top → close → edit form returns with modifications intact and `formModified` still `true`. Critical flow, so worth Playwright per `specs/constitution.md` §2.1.

## 3. Risks and alternatives considered

- **Risk: popovers/tooltips with HTML content get reinitialized after every help-drawer swap.** Mitigation: the new `help_drawer_structure.html` includes its own popover-init script scoped to `[data-location="help_drawer"]`, mirroring the existing side-panel pattern. No change needed for popovers in field tooltips since the trigger element itself is now class-based, not href-based.
- **Risk: existing E2E unsaved-changes tests break because help-drawer paths no longer hit the modal.** They shouldn't — they exercise side-panel-to-side-panel transitions only. But confirm during implementation.
- **Alternative considered: re-process popover content with `htmx.process()` after `shown.bs.popover`.** Rejected — fixes the bug but doesn't address the destructive-swap UX problem, and would still leave help-button clicks destructive.
- **Alternative considered: stacked side panels with back navigation.** Rejected — more plumbing for a marginal UX benefit; an overlay layer is enough for the present need.
- **Alternative considered: render popover with `container: '#sidePanel'` so HTMX scope covers it.** Rejected — fragile under layout overflow, doesn't solve the "?" button's destructive swap.

## 4. Cross-cutting concerns

- **Docs.** Update `specs/architecture.md` with a one-line note about the help-drawer layer being independent of the side panel.
- **Migrations.** None.
- **JS bundle / build.** None — vanilla JS, edited in place.
- **Changelog.** One entry under "Fixed" for the popover-link bug and "Changed" for the overlay behavior.
