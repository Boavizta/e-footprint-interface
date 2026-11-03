# Side-panel unsaved-changes replay hand-parses htmx attributes: a stored-continuation guard the mission now forbids, and one that misfires on boosted links

- **Status:** CONFIRMED
- **Confidence:** high — code reading of `side_panel_utils.js` and the vendored htmx 2.0.6. A scratch Jest probe loaded the real `htmx.min.js` and `side_panel_utils.js` in jsdom and showed both the redundant parsing and the boosted-link misfire. Not reproduced in a real browser.
- **Reported:** Report 1 of the intake says `proceedWithPendingRequest()` re-reads `hx-get`/`hx-target`/`hx-swap`/`hx-vals` and `eval`s `js:` values. It says this is redundant because Task 6 added `source: pendingRequest`, calls it a cleanup with no visible defect, and proposes either shrinking the call to url + source or moving to `htmx:confirm` + `issueRequest`. **The redundancy claim holds.** **"No user-visible defect" does not:** the guard also catches the two `hx-boost` "Data & privacy" links. Those have no `hx-get`, so after **Yes, Continue** the replay GETs the current page URL into `#sidePanel`. **The url + source shrink is incomplete:** it keeps reading `hx-get`, so it keeps that defect. **Both proposed directions conflict with the mission:** they keep suspend-and-replay, which `specs/mission.md:26-28` (added 2026-10-19) rules out.

## Root cause

**Current guard.** `e-footprint-interface/theme/static/scripts/side_panel_utils.js:127-139` listens to `htmx:beforeRequest`. When the triggering element's own `hx-target` attribute is exactly `"#sidePanel"` and `formModified` is set, it cancels the request and stores the element in `pendingRequest`. It then wires the shared `#unsavedModal` "Yes, Continue" button to `proceedWithPendingRequest()` (`side_panel_utils.js:199-220`). That function rebuilds the request by hand:
- it reads `hx-vals`, `eval`s a `js:` prefix and otherwise `JSON.parse`s (`:202-211`);
- it reads `hx-get`, `hx-target` (default `#sidePanel`) and `hx-swap` (default `innerHTML`) (`:213-215`);
- it calls `htmx.ajax("GET", url, {source, target, swap, values})` (`:216`).

Task 6 (`0ece3445`, "lock every user-initiated request") only added `source: pendingRequest`, so the replay would pick up `hx-disabled-elt` and `hx-indicator`.

**Redundancy (verified against the vendored htmx).** `theme/static/scripts/external_librairies/htmx.min.js` is htmx 2.0.6 (`version:"2.0.6"`). It is byte-identical to `unpkg.com/htmx.org@2.0.6/dist/htmx.min.js` apart from a trailing newline. The line numbers below are from that release's `dist/htmx.js`. With a `source`:
- **Target.** `ajaxHelper` passes `resolveTarget(context.target)` as `targetOverride` (htmx.js:4041-4055). `resolveTarget(undefined)` returns `undefined` (htmx.js:1250-1256), so `issueAjaxRequest` falls back to `getTarget(elt)` (htmx.js:4261). `getTarget` resolves the closest inherited `hx-target` (htmx.js:1385-1399). It defaults to the source element itself only when no `hx-target` exists on it or any ancestor.
- **Swap.** `swapOverride` is `context.swap`. When that is undefined, `getSwapSpecification` reads the closest inherited `hx-swap`, falling back to `defaultSwapStyle` (htmx.js:3738-3745).
- **Values.** `issueAjaxRequest` always computes `getExpressionVars(elt, event)` (htmx.js:4418). That evaluates `hx-vals` and `hx-vars`, including `js:`/`javascript:` prefixes via `Function(...)` with `this` bound to the element, and walks every ancestor (htmx.js:3891-3934). It merges these over `etc.values` (htmx.js:4416-4419), so the hand-`eval`ed values are recomputed and overwritten anyway. The hand parse also misses ancestor `hx-vals`; htmx includes them.
- **Locks.** `hx-disabled-elt` and `hx-indicator` resolve by inheritance from the source (htmx.js:3356-3385, applied at 4603).

The scratch probe confirms this. `htmx.ajax("GET", "/open/X/", {source: btn})` sent `/open/X/?efootprint_id_of_parent_to_link_to=p1&anc=1` with `HX-Target: sidePanel` and disabled the other buttons. The current replay sent `/open/X/?efootprint_id_of_parent_to_link_to=p1`: same own value, ancestor value missing.

**What the guard actually intercepts.** It matches `event.detail.elt.getAttribute("hx-target") === "#sidePanel"`: the element's own attribute, not an inherited one and not `detail.target`. Every current `#sidePanel` trigger declares it literally:
- **Card and edit openers:** `object_cards/*.html`, `partials/group_entry_row.html`, `side_panels/edit/calculated_attributes/*.html`.
- **Add buttons:** `components/add_object_button.html:23`, `components/add_child_button.html:24,43,60`.
- **Toolbar:** system-name rename (`upload_download_reboot_model_tooltips.html:22`), import JSON (`:122`).
- **Other `hx-get` triggers:** the picker upload card (`onboarding/template_picker.html:34`) and the Simplified "Edit timeseries" button (`simplified_inputs/editor.html:19`).

All of those use `hx-get`, so the hand-built GET works for them. Three exceptions:
- **Two boosted anchors.** `components/help_menu.html:33-39` and `components/workspace_storage_status.html:13-18` are `<a href="{% url 'data-privacy' %}" hx-boost="true" hx-target="#sidePanel">`. Boosting issues a GET of `href` (htmx.js:2388-2416), and the guard intercepts it. But `getAttribute("hx-get")` is `null`, and `issueAjaxRequest` turns a null path into `location.href` (htmx.js:4426-4429). The probe printed `GET http://localhost/` for this replay. In the app, the builder page is `/model_builder/`, which `model_builder_main` (`model_builder/adapters/views/views.py:174`) renders in full, into `#sidePanel`. Reproduction: edit any side-panel form, open Help, click "Data & privacy", then "Yes, Continue".
- **One `hx-post`.** `side_panels/data_privacy.html:83` is an `hx-post` form targeting `#sidePanel`. The hand-built replay would downgrade it to GET. It is unreachable while dirty: that panel calls `openSidePanel()` (`data_privacy.html:166`), which clears `formModified`, and it has no control that tags the form.
- **`htmx.ajax` openers.** Side-panel openers that use `htmx.ajax` (`support.js:16-20`, `model_comparison.js:283-284`) are not caught by this guard. The source element has no own `hx-target`, and both are covered elsewhere: `runAfterSidePanelDiscardConfirmation` and `PANEL_DISCARDING_PATHS`.

**Loading-bar workaround.** The guard runs on `htmx:beforeRequest`. A document-level `htmx:beforeRequest` listener in `theme/static/scripts/loading_bar.js:1-6` starts the progress bar, and `preventDefault()` does not stop propagation. Hence `setTimeout(hideLoadingBar, 200)` at `side_panel_utils.js:135-137` and `hideLoadingBar()` on the modal's Cancel button (`modals/warn_before_side_panel_closing_modal.html:9`). `htmx:confirm` fires earlier (htmx.js:4291-4297), before `htmx:configRequest` and `htmx:beforeRequest` (htmx.js:4462, 4598). A guard on `htmx:confirm` never starts the bar.

**Project rule the design contradicts.** `specs/mission.md:26-28`: "Guards block; they do not suspend and replay. … the user resolves it and repeats the action. Do not store the interrupted intent to resume it afterwards." `specs/architecture/rendering.html:35` says no feature module keeps a continuation for a request. Configure exits already follow this (`specs/architecture/workspace.html:75-78`). Three places in the same file still store a continuation:
- `pendingRequest` / `proceedWithPendingRequest` (this report);
- `pendingNavRequest` / `issueRequest(true)` (`side_panel_utils.js:160-181`);
- `pendingSidePanelReplacement` (`side_panel_utils.js:106-125`).

`specs/features/server-rendered-state-follow-up/kickoff.md` originally deferred this cleanup. User review on
2026-11-03 moved all three paths into Task 1; the separate dirty-detection improvement stays deferred.

## Reproduction and evidence

The existing hand-parsed replay was probed with the real bundled HTMX in jsdom: a boosted Data & privacy link
replays the current builder URL into the panel. This is historical evidence of the defect, not a browser pass.
The new contract removes the replay mechanism entirely. Existing navigation, Feedback and Simplified-entry tests
currently expect continuation; rewrite them to fail on that behavior and validate discard-and-repeat instead.

The earlier claim that matching `detail.target` would inherently stack two dialogs was not established. Feedback
clears the dirty flag before its deferred AJAX call, and overlapping branches can return after the first match.
The own-attribute restriction merely preserved the old scope. It is no longer the selected design.

## Fix approach

**2026-11-03 user decision: one dirty-side-panel policy everywhere — block, discard/close, repeat.**

The first attempted action must stop before its request or destructive UI change. Keep editing closes only the
warning. Discard changes closes and clears the side panel; it never resumes the attempted action. The user clicks
again. Clean-panel actions run immediately. There is no stored intent, callback, event detail or HTMX request.

Implement one boolean decision/modal helper in `side_panel_utils.js`, for example `blockIfSidePanelDirty()`:
clean returns false; dirty shows the shared modal and returns true. Thin entry points use it:

- One `htmx:confirm` listener classifies actual panel replacements and model exits, including resolved/inherited
  targets, boosted links and `htmx.ajax` destinations. It prevents a classified dirty exit before loading/locks.
  Preserve Save and validation/preview operations on the current form; a response target alone is not enough to
  classify a Save as abandonment. Existing switch/add paths still identify exits targeting elsewhere.
- JS actions use the same helper before destructive UI changes: Feedback before busy state/request setup;
  Simplified entry before close/base-view/read; close and Cancel controls before clearing the form.
- The shared modal has fixed handlers. Keep editing closes the warning; Discard calls
  `closeWarningModalAndCloseSidePanel()`. That cleanup bypasses the guard and resets dirty state.
- Successful Save and server-directed cleanup still call the low-level close directly. The guard must not turn
  cleanup or saving into another discard prompt.

Delete `pendingRequest`, `pendingNavRequest`, `pendingSidePanelReplacement`, their reset plumbing, all three
`proceedWithPending…` functions, callback-taking `runAfterSidePanelDiscardConfirmation`, the beforeRequest guard
and the loading-bar timeout. Migrate the Feedback and Simplified callers to boolean checks. Keep the existing
dirty flag/detection mechanism; replacing it is a separate follow-up. The unrelated Save-path `eval` stays deferred.

### Covered actions

- Card/add/edit openers, rename/import panels, Data & privacy, Feedback, +Add blank/duplicate/import and model
  switching, including cross-slot dismissal from Compare.
- Entering Simplified inputs or its configuration when doing so abandons a side-panel draft; retain Configure's
  own existing separate draft guard.
- Closing/cancelling an edited panel, including the Simplified timeseries panel.
- Model removal, reset and example loading: remove the previous dirty-handling exemptions. A dirty first click
  opens only the shared discard modal and cannot remove/reset/load anything. After Discard closes the panel,
  the user repeats the action and sees any ordinary destructive confirmation. No click stacks two prompts.
  Coordinate `htmx:confirm` listeners so native confirmations never run after a dirty exit was blocked.

Opening Compare, returning to the same model, help-drawer actions and export preserve the side-panel draft and
need no discard warning. Save/validation/preview remain available while dirty. The classification is abandonment
of the draft, not every request made while a draft exists.

### Modal copy

- Message: "The open side panel has unsaved changes. Discard them?"
- Buttons: "Keep editing" / "Discard changes".
- Keep existing modal/button IDs. Give buttons fixed handlers instead of rewiring them per interrupted action.

### Alternatives superseded or rejected

- The 2026-10-21 own-`hx-target`-only scope is superseded: preserving navigation/Feedback/Simplified replay would
  retain several implementations and contradict the now-approved uniform behavior.
- Shrinking the replay to `htmx.ajax(url, {source})` or using `detail.issueRequest(true)` still stores/resumes the
  dirty action. Ordinary clean-panel destructive confirms may use HTMX's normal confirmation mechanism; they
  must never resume an action interrupted by the dirty guard.
- A single HTMX hook alone misses JavaScript exits that clear/change the UI before their request. Keep the small
  JS entry points, with one shared decision and modal implementation.

## Files to touch

- `theme/static/scripts/side_panel_utils.js` — one boolean helper, HTMX and close entry points; remove all three
  pending-action mechanisms, beforeRequest cancellation and timeout. Retain dirty detection and Save handling.
- `theme/static/scripts/support.js` — Feedback checks before request setup, with no retained callback.
- `theme/static/scripts/simplified_inputs/workspace.js` — gate entry before panel close/base-view/read.
- `theme/static/scripts/model_comparison.js` — shared gate before removal's ordinary confirm; remove its custom
  unsaved-message concatenation; retain switch/add behavior after the user repeats the action.
- `theme/static/scripts/model_builder_main.js` — coordinate reset's existing `htmx:confirm` confirmation with the
  dirty gate. Audit reset/example controls and other exits; add intent markup only where classification needs it.
- `model_builder/templates/model_builder/modals/warn_before_side_panel_closing_modal.html` — fixed handlers and
  labels, no `hideLoadingBar`. `model_builder_main.html` — new message.
- Audit user close/Cancel controls, notably `simplified_inputs/timeseries_panel.html`, and any affected exit
  templates. Do not guard successful-save or server-directed low-level cleanup.
- `js_tests/side_panel_switch_guard.test.js`, `support.test.js`, `simplified_inputs.test.js`,
  `model_comparison.test.js` and existing reset-confirm tests — migrate continuation expectations/mocks.
- E2E forms, model comparison and existing Feedback/Simplified entry flows — test the new behavior.
- `specs/architecture/workspace.html`, `specs/architecture/rendering.html`, build-a-model and compare-models
  design journeys — document unified behavior, second clicks and non-destructive exceptions when implementing.
- `specs/features/server-rendered-state-follow-up/kickoff.md` — remove the deferred replay row; retain dirty
  detection as separate follow-up. `CHANGELOG.md` — production fix entry when implemented.

## Tests

- Shared helper and HTMX tests: dirty/clean; Keep editing preserves form; Discard closes/clears without requests
  or callbacks; repeat performs the action. Actual/inherited target and programmatic request coverage; overlapping
  eligibility paths produce one modal. No request/loading-bar stage occurs on a blocked action.
- Feedback and Simplified-entry tests: no AJAX, fallback navigation, busy state or view change while blocked;
  Discard alone does not open the requested panel or enter Simplified inputs. Update callback mocks.
- Model navigation/removal/reset/example tests: Discard cannot switch, add, remove, reset or load; repeat follows
  ordinary clean behavior and any destructive confirmation. No native confirm on the first dirty click.
- Close/Cancel and normal Save/validation/preview coverage. Compare and same-slot return retain drafts; export
  does not save or discard. Keep the Configure draft rules independent.
- Rewrite `test_pending_request_preserves_hx_vals` in `tests/e2e/test_forms.py`: no replay after Discard;
  repeat preserves authored values and locking. Add Data & privacy and close/cancel cases; assert copy once.
- Rewrite `test_cross_slot_dismiss_warns_over_the_revealed_model_then_continue_switches` in
  `tests/e2e/test_model_comparison.py` to stay on the current slot after Discard, then switch on repeat.
  Extend existing Feedback coverage in `tests/e2e/test_data_privacy.py`, Simplified and reset/example coverage. Reuse fixtures and assert requests/state.
- Run affected Jest suites, full `npm run jest`, and the E2E guard flows with a local server. No new contract pass
  is claimed by this planning update; existing tests expecting replay must change during implementation.

## Acceptance criteria

- Every supported user exit abandoning a dirty side-panel draft uses the shared block/discard-close/repeat rule.
- Keep editing preserves edits. Discard never performs the interrupted request, navigation, view change or
  destructive action. Clean actions proceed normally, with one confirmation at most per click.
- No pending request/event/callback or dirty-action replay remains in the covered paths. The guard contains no
  hand-parsed request, `eval`, beforeRequest listener or loading-bar timeout. Save-path `eval` remains out of scope.
- Resolved HTMX destinations and small JS entry points cover all openers; own-attribute matching is not required.
- Save/preview/validation work while dirty, and non-destructive Compare/same-slot/help/export preserve drafts.
- The deferred replay row is removed from the follow-up; the dirty-detection improvement remains separate.

## Flags

- Interface-only, no library or persistence schema change. Task 2 shares `side_panel_utils.js`; run adjacent.
- Standard implementation difficulty: behavior changes now include Feedback, switching, +Add, Simplified entry,
  close/Cancel, removal, reset and example loading, not just the old attribute-based guard.
- Architecture/journey updates belong with implementation; their current pages still describe shipped behavior.
- Modal ordering must be explicit across listeners. A prevented dirty exit cannot open a second native confirm.

## Decisions

- 2026-11-03, user review: adopt unified discard-and-repeat everywhere a user action abandons dirty side-panel
  edits. One shared decision/modal helper, thin HTMX/JS/close entry points, no stored continuation. This supersedes
  the 2026-10-21 guard-only scope and moves the remaining replay work out of the separate follow-up.
- Keep the separate Save/recomputation `eval` and dirty-detection redesign outside this task. Neither is needed
  to unify how existing dirty state is handled.
