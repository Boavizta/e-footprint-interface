# Help drawer as overlay on top of side panel

**Status:** Functional spec.
**Date:** 2026-05-20.

## 1. Context and goal

Today the help drawer (the panel rendered by `open_help_drawer` at `model_builder/adapters/views/views_help.py`) is swapped into the right-hand `#sidePanel`. Two consequences:

1. Clicking the help "?" button next to an Add button on the canvas destroys whatever edit form was already open in `#sidePanel`.
2. Field tooltips can contain `{class:X}` references rendered by `model_builder/adapters/ui_config/interface_placeholder_handlers.py:handle_class` as `<a href="/model_builder/open-help-drawer/X/" hx-get=...>`. Because Bootstrap popovers insert their content into a fresh DOM subtree *after* HTMX has processed the side panel, the `hx-get` is inert and the browser follows the `href` instead — navigating the whole page to the partial template URL. The user lands on a "full-screen help drawer" with a changed URL and no way to close it. **This is the bug that triggered the work.**

The fix is to make the help drawer a *separate layer* on top of the side panel: independent container, independent close behavior, never destructive to side-panel state.

## 2. Scope

**In scope**
- Introduce a dedicated `#helpDrawer` overlay container, distinct from `#sidePanel`.
- Route every help-drawer entry point to `#helpDrawer`:
    - The "?" buttons rendered by `model_builder/templates/model_builder/components/add_object_button.html`.
    - The `{class:X}` links rendered by `interface_placeholder_handlers.handle_class` (including those that end up inside Bootstrap popovers and tooltips).
    - Any future help-drawer entry point.
- Help drawer renders **over** the side panel in the same right-hand column (layout option A previously agreed). When the side panel is open, the help drawer visually replaces it; the side panel DOM and form state remain mounted underneath, untouched.
- Internal navigation between help topics: a `{class:Y}` link inside a help drawer swaps `#helpDrawer` content. No unsaved-changes modal — help-drawer swaps are never destructive.
- Closing the help drawer (cross button) empties `#helpDrawer`. If a side panel was open underneath, it becomes visible again with its previous content and form state intact. If not, the canvas re-expands to full width as today.
- Opening any side panel (any HTMX swap into `#sidePanel`) auto-closes the help drawer.
- Fix the popover/HTMX bug so the in-tooltip `{class:X}` link works regardless of which DOM subtree the popover renders into.

**Out of scope**
- Visual restyling of the help drawer beyond what the layer change requires.
- Stacked side panels (back button to return to a previous side-panel state). Side-panel-to-side-panel swaps keep their current behavior.
- Persisting help-drawer state across page reloads or system reboots.
- Help content for things other than classes (params, calcs, UI tokens — they continue to render as inline spans, not as links).
- Changes to the unsaved-changes modal flow for `#sidePanel`. It continues to fire on `hx-target="#sidePanel"` requests exactly as today.

## 3. User-visible behavior

| Situation | Today | After |
|---|---|---|
| Click `?` next to Add button on canvas (no side panel open) | Help opens in side panel column | Help opens in side panel column (visually identical) |
| Click `?` next to Add button on canvas (side panel open with unsaved edits) | Unsaved-changes modal fires; if confirmed, edits are lost | Help opens **on top of** the edit form; edits preserved; no modal |
| Click `{class:X}` link inside a field tooltip popover | Browser navigates to partial URL; full-screen broken page | Help drawer opens on top of the side panel; URL unchanged |
| Click another `{class:Y}` inside the open help drawer | (would navigate) | Help drawer content swaps to Y; side panel underneath unchanged |
| Click cross button on help drawer | Side panel closes entirely | Help drawer closes; side panel reappears underneath if any |
| Start editing/adding (any `#sidePanel` swap) while help drawer is open | n/a | Help drawer auto-closes; side panel takes over |

## 4. Success criteria

1. The original bug is resolved: clicking a `{class:X}` link inside any field tooltip opens the help drawer overlay; the URL does not change; the user can close it via the cross.
2. From any edit panel, opening the help drawer for any class and then closing it returns the user to the exact same edit form, with all unsaved changes preserved and `formModified` still `true`.
3. The "?" button next to Add buttons on the canvas opens the help drawer as an overlay; if a side panel is already open, it is *not* destroyed.
4. Internal help-to-help navigation works without firing the unsaved-changes modal.
5. Starting any new side-panel action while a help drawer is open auto-closes the help drawer.
6. Existing E2E coverage of side-panel unsaved-changes flow continues to pass unchanged.

## 5. Open questions resolved in plan

- Exact DOM structure of `#helpDrawer` (sibling of `#sidePanel`, absolutely positioned over the same column, or sharing the column via z-index).
- Where popover initialization for help-drawer content lives, given the help drawer can re-swap independently of the side panel.
- Whether to keep the existing `open-help-drawer/<class_name>/` URL or rename it (likely keep — only the front-end target changes).
