# `htmx:oobErrorNoTarget` on canvas dict-count edits and unlinks: dict mutations always emit the child's membership-section OOB region, even when that child's edit panel is not mounted

- **Status:** CONFIRMED
- **Confidence:** high — traced in code and reproduced in a real browser (Playwright, fresh isolated sessions on the local dev server at `7f78a329`): every canvas-originated dict mutation logs exactly one `htmx:oobErrorNoTarget`; in-panel mutations and the list path log none.
- **Reported:** canvas inline count edits, model-comparison count saves and edge device-group linking log `htmx:oobErrorNoTarget`, because `_run_edit_and_present()` always adds a `dict_membership_section` region, and the list path does the same with `list_membership_section`. The **dict half holds**. The **list half does not**: that path cannot trigger the error from the UI (see below). "Model-comparison count saves" is the same canvas count edit made while two models are open; nothing about it is comparison-specific. "Edge device-group linking" is the canvas group-entry count edit and unlink ✕ (`group_entry_row.html`). Linking from a device's own panel ("Add to group") logs nothing.

## Root cause

**The region is emitted unconditionally.** `_run_edit_and_present()` always builds
`OobRegion.make("dict_membership_section", object_id=panel_object_id)`
(`e-footprint-interface/model_builder/adapters/views/views_dict_mutation.py:52`). `panel_object_id` is always the dict key, i.e. the child. All three dict endpoints go through it: `update_dict_count` (`views_dict_mutation.py:73`), `unlink_dict_entry` (`:83`) and `link_dict_entry` (`:101`). `present_edited_object` renders every region the use case returns (`model_builder/adapters/presenters/htmx_presenter.py:222-236`). `_render_dict_membership_section` emits
`<div hx-swap-oob='outerHTML:#dict-membership-section-<child id>'>`
(`model_builder/adapters/presenters/oob_regions.py:34-42`).

**The target only exists while that child's edit panel is mounted.**

- `#dict-membership-section-<id>` is the wrapper in `model_builder/templates/model_builder/side_panels/edit/dict_membership_section.html:2`.
- That partial is included only in edit panels: `edit/edit_panel__generic.html:21` (the generic edit panel and `server/server_edit.html`, which extends it) and `edit/edit_edge_device_group.html:4`. `edit/edit_recurrent_edge_component_need.html` and all add panels omit it.
- Closing the panel empties `#sidePanel` (`theme/static/scripts/side_panel_utils.js:64-71`), so the target disappears with the panel.

**The same endpoints are also called from the canvas.** `dict_entry_count_unlink.html` posts `update-dict-count` (`object_cards/partials/dict_entry_count_unlink.html:7`) and `unlink-dict-entry` (`:21`). That partial is included in three places:

1. Canvas step and job inline counts through `inline_count.html:7`. `inline_count.html` is used by `journey_step_card.html:46`, `resource_need_card.html:22` and `resource_need_with_accordion_card.html:36`.
2. Canvas edge-group entry rows, with the ✕: `group_entry_row.html:22` and `:62`.
3. The child's membership section: `dict_membership_section.html:11`. Its "Add to…" button posts `link-dict-entry` (`:22-28`).

So any canvas count edit or ✕ made while the child's panel is closed, or while another object's panel is open, carries an OOB element with no target.

**htmx cannot tolerate this.** The bundled htmx is 2.0.6 (`theme/static/scripts/external_librairies/htmx.min.js`, `version:"2.0.6"`). When a target is missing, its oobSwap removes the fragment and calls `triggerErrorEvent(body, "htmx:oobErrorNoTarget")`. `triggerEvent` calls `logError` → `console.error` (`function R(e){console.error(e)}`) *before* dispatching the event. No config, swap modifier or listener can suppress it, and `htmx:oobBeforeSwap` only fires when a target exists.

**Why the region exists (and must stay when the panel is mounted).** The comment at `views_dict_mutation.py:50-51` says it keeps an *open* child panel in sync. The design hub documents this: `specs/design/journeys/build-a-model.html:799` ("the child's membership section in its open edit panel"). Reproduced: with step S's edit panel open, editing S's count on the journey card changed the panel's membership count from 1 to 5 with no console error. Without the region, that panel would show a stale count. It would only be stale: the membership controls sit outside `#sidePanelForm`, so the stale count is never submitted. In-panel link and unlink also rely on the region to add or remove membership rows.

**List path: no reachable defect.** `views_list_mutation.py:36` does emit `list_membership_section` unconditionally (`oob_regions.py:45-53`; target at `list_membership_section.html:1`). But `link-list-entry` and `unlink-list-entry` are posted only from inside that same section (`list_membership_section.html:14`, `:32`). The only opt-in is `EdgeUsagePattern.edge_usage_journeys` (`model_builder/domain/entities/web_core/usage/edge/edge_usage_pattern_web.py:16`). Its child, `EdgeUsageJourney`, uses the generic edit panel, which includes the section (`edit_panel__generic.html:22`). So whenever the request can be issued, the target is mounted. A browser link and unlink from an edge journey's panel logged no errors.

Reproduction matrix (scratch Playwright under `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/oobdiag/`):

| Path | Panel state | Console |
|---|---|---|
| Canvas step/job inline count | none open | `htmx:oobErrorNoTarget` |
| Canvas inline count | parent's panel open | `htmx:oobErrorNoTarget` |
| Canvas inline count | child's panel open | clean; panel count synced 1 → 5 |
| Canvas inline count after "add model by duplication" | none | `htmx:oobErrorNoTarget` |
| Canvas group-entry count / ✕ | none | `htmx:oobErrorNoTarget` (each) |
| Device panel membership count / ✕ / "Add to group" | device's panel | clean |
| Edge journey panel list link / unlink | journey's panel | clean |

**Why tests miss it.**

- Unit tests post the dict endpoints but never assert on the region (`tests/unit_tests/adapters/views/test_views_dict_mutation.py:224-300`). Only the list path asserts its region's presence (`tests/unit_tests/adapters/views/test_views_list_mutation.py:91`).
- The E2E tests that drive canvas counts and unlinks do not listen for console errors: `tests/e2e/objects/test_edge_device_groups.py:98-120` and `tests/e2e/test_model_comparison.py:23-52`.
- The console-error pattern exists only in the Compare-chart tests (`tests/e2e/test_model_comparison.py:201-203`, `:230`).
- `htmx:oobErrorNoTarget` is only a console error, not a failed request or a visible DOM change.

## Fix approach

**Recommended (a): the request reports whether the child's membership section is mounted, and the server emits the region only then.** This is the same DOM-derived "what is mounted" signal that saved bookmarks already send: `mounted` in `theme/static/scripts/simplified_inputs/bookmarks.js:105-111`, consumed at `model_builder/adapters/views/views_simplified_inputs.py:157`, `:179`. It reads the rendered DOM instead of keeping client state, so it is compatible with `specs/conventions.md:28` ("the rendered fragment is the state"; use `hx-vals` where it expresses the need).

1. Next to `recomputationVals()` (`side_panel_utils.js:5-11`), add a one-liner helper, e.g.
   ```js
   function dictMembershipVals(objectId) {
       return document.getElementById("dict-membership-section-" + objectId) ? {membership_section_mounted: true} : {};
   }
   ```
2. In `dict_entry_count_unlink.html:15` and `:24`, change `hx-vals` to
   `js:{...recomputationVals(), ...dictMembershipVals("{{ entry_efootprint_id }}")}`.
   In `dict_membership_section.html:28`, do the same with `panel_id`, or send a static `membership_section_mounted: true`, since that button always lives inside the section.
3. In `_run_edit_and_present()`, build `extra_oob_regions` only when `request.POST.get("membership_section_mounted")` is set; otherwise pass `[]`. The `panel_object_id` parameter can then be renamed to the key id, or dropped in favour of `key_obj.id`.
4. Leave the list path unchanged. Its region is always targetable.

This removes the error on every reachable path. It keeps the canvas → open-child-panel sync and makes canvas count responses smaller (no membership-section render) in the common no-panel case.

**Rejected:**

- **(b) Server infers from request origin.** Only the membership-section controls would send a static flag, and canvas controls would never get the region. This is simpler (no JS helper), but it silently drops the documented canvas → open-panel sync, which was reproduced as working today. Keep it only if the user decides that sync is not worth one helper line.
- **(c) Tolerate the missing target.** htmx 2.0.6 logs `console.error` before any listener runs and has no config switch. Silencing it would mean patching htmx or `console`. Any OOB fragment with no target remains an error class worth seeing.
- **Server-side "open panel" bookkeeping in the session.** Panel close is client-only (`closeAndEmptySidePanel`), so the server would go stale.
- **Re-fetching the section through an `HX-Trigger` event.** This costs an extra round trip and a new endpoint, against the mission's eco-design priority.
- **Pointing the region at an always-present container.** No such stable container scopes the section correctly.

## Files to touch

- `e-footprint-interface/theme/static/scripts/side_panel_utils.js` — add `dictMembershipVals(objectId)` beside `recomputationVals()` (around line 5).
- `e-footprint-interface/model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html` — extend `hx-vals` on the count input (line 15) and the unlink button (line 24).
- `e-footprint-interface/model_builder/templates/model_builder/side_panels/edit/dict_membership_section.html` — extend `hx-vals` on the "Add to…" button (line 28).
- `e-footprint-interface/model_builder/adapters/views/views_dict_mutation.py` — emit the `dict_membership_section` region only when `membership_section_mounted` is posted (lines 47-55); fix the comment at 50-51.
- `e-footprint-interface/js_tests/fixtures/inline_count_autosave.html` — regenerate through `js_tests/build_fixtures.py` (case at line 289), because it renders the real `dict_entry_count_unlink.html`.
- `e-footprint-interface/specs/design/journeys/build-a-model.html:799` — optional wording: "only when that panel is mounted (the request says so)". A one-line mention in `specs/architecture/rendering.html` or `forms-and-relationships.html` is optional, under the dict-relationship paragraph.

## Tests

- **Unit, `tests/unit_tests/adapters/views/test_views_dict_mutation.py`:**
  - `update-dict-count`, `unlink-dict-entry` and `link-dict-entry` posted without `membership_section_mounted` must not contain `#dict-membership-section-`.
  - The same requests with `membership_section_mounted=true` must contain `outerHTML:#dict-membership-section-<key id>`.
  - Parametrize over the three endpoints, reusing the step/job fixture at lines 224-260.
- **E2E, `tests/e2e/objects/test_edge_device_groups.py:98-120`:** attach the console/pageerror collector pattern from `tests/e2e/test_model_comparison.py:201-203` around the canvas group-entry `set_inline_count` and `click_unlink_button`, and assert no console errors.
- **E2E, new case (e.g. beside `test_device_edit_panel_updates_and_removes_group_membership`, or in `tests/e2e/test_model_canva.py`):** open a step's edit panel, edit that step's inline count on the journey card, then assert:
  - the panel's `[data-dict-membership-name] input[name='count']` shows the new value (sync is preserved);
  - no console error was logged.
- **Optional JS (`js_tests/`):** `dictMembershipVals` returns the flag only when `#dict-membership-section-<id>` is present. The E2E above already covers this end to end.

## Acceptance criteria

- With no edit panel open, or with an unrelated panel open, canvas step/job inline count edits, canvas group-entry count edits and ✕ unlinks log no `htmx:oobErrorNoTarget`. This holds in single-model and two-model (comparison) workspaces.
- With the child's edit panel open, editing that child's count or ✕ on the canvas still updates the panel's membership section in place, with no console error.
- In-panel membership count, ✕ and "Add to…" behave as today (rows added, removed or updated in place), with no console error.
- Canvas count responses with no mounted membership section no longer contain a membership-section fragment.

## Risks and side effects

- **The flag is a client claim.** If it is missing (for example, a hand-crafted request), the response skips one display refresh. It is never a correctness or persistence issue: the section's controls are outside the panel form, and the next panel open re-renders from the model.
- **Panels with no membership section.** `edit_recurrent_edge_component_need.html` and all add panels never mount the section, so they never request the region. This is correct: today's emission there is exactly the error case.
- **List path untouched.** If list memberships ever gain canvas controls, they will need the same flag. Mention this in the code comment or the architecture page.
- **Unrelated finding, out of scope.** `tests/e2e/pages/side_panel_page.py` still carries the helpers `link_group_member`, `set_linked_entry_count` and `remove_linked_entry` (lines 139-176). No test calls them, and they target a group-panel markup that no longer exists.

## Flags

- No migration, serialization or library change; interface-only.
- HTMX/OOB state transition: FULL review surface under `.agents/repository.md`. The change is small, though.
- Constitution §1.4 and `specs/conventions.md:28`: the server stays the source of truth. The client only reports DOM presence through `hx-vals`, with no stored state. Server failures stay visible.
- After editing the partial, rebuild the JS fixtures (`js_tests/build_fixtures.py`). No JS bundle rebuild is needed: `side_panel_utils.js` is not part of the simplified-inputs bundle.
- Validation is local only and needs the dev server for E2E. The scratch reproduction ran against the user's running `runserver` in isolated Playwright sessions; no persistent state was touched.

## Decisions

- 2026-10-21 — User decision: keep the canvas → open-child-panel sync. Implement option (a): the client posts `membership_section_mounted` through a `dictMembershipVals(id)` helper, and the server emits the `dict_membership_section` region only when that flag is present. The list path stays unchanged.
