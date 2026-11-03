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

**2026-11-03 user decision: discard-and-repeat everywhere, with target-based interception.**

A dirty exit stops before its request or UI change. Keep editing preserves the form. Discard closes/clears the
panel and does nothing else; the user repeats the action. Clean actions proceed immediately. There is no stored
intent, source, callback, event detail or request to resume.

One boolean helper in `side_panel_utils.js`, for example `blockIfSidePanelDirty()`, owns the decision and shared
modal: clean returns false; dirty shows the warning and returns true. Only three entry rules are needed:

1. **Resolved replacement destination:** one `htmx:confirm` listener intercepts replacement of `#sidePanel` or
   the whole builder (`#main-content-block`). This naturally includes inherited `hx-target`, boosted links and
   `htmx.ajax`, including Feedback and import. Do not add a separate dirty check for each opener.
2. **Explicit exit marker:** a source/control with `data-discards-side-panel` identifies a request that abandons
   the draft without one of those replacement targets (notably model switching with `hx-swap="none"`). Remove
   `PANEL_DISCARDING_PATHS`; no URL list or per-action registry replaces it.
3. **Direct exits:** Close/Cancel and Simplified entry call the same helper before clearing/changing the UI.
   They cannot rely on a later HTMX hook because they have no request or perform the destructive step first.

Classify actual replacement, not every request with a destination: `hx-swap="none"` or an OOB canvas update
alone does not discard a panel. Do not blanket-guard canvas updates or all requests. Save, validation/preview,
background status reads, help, export, opening Compare and same-slot return stay available. Keep Configure's
separate unsaved-draft rules. Target/marker eligibility replaces the earlier per-flow request classification.

The dirty gate must run before ordinary removal/reset/example confirmations, e.g. in capture phase with
propagation stopped only for a blocked dirty exit. This avoids depending on the registration order of module
listeners. Dirty first click → shared modal only; Discard → close only; repeat → ordinary destructive confirm.
Remove removal's separate dirty-message concatenation, not its normal clean confirmation.

Feedback relies on the central HTMX check, not a direct dirty predicate. Remove its deferred callback wrapper;
move busy/request bookkeeping to the actual HTMX request lifecycle so canceled requests cannot leave busy state,
open the panel or trigger fallback navigation. Simplified entry instead checks directly before close/base-view/read.

Delete all three pending-action mechanisms (`pendingRequest`, `pendingNavRequest`, `pendingSidePanelReplacement`
and `proceedWithPending…` functions), `runAfterSidePanelDiscardConfirmation`, beforeRequest cancellation and the
loading-bar timeout. Retain dirty detection and the separate Save-path recomputation code/`eval`.

### Modal and cleanup

- Message: "The open side panel has unsaved changes. Discard them?"
- Buttons: "Keep editing" / "Discard changes", with existing IDs and fixed handlers.
- Keep editing closes only the warning. Discard calls `closeWarningModalAndCloseSidePanel()`.
- Successful Save and server-directed cleanup continue to call low-level close directly; never guard cleanup
  after an accepted operation. User Close/Cancel, including the Simplified timeseries panel, uses the shared gate.

### Coverage

Panel/add/edit/rename/import and Data & privacy openers, Feedback, +Add, model switches (including cross-slot
Compare dismissal), Simplified entry, Close/Cancel and removal/reset/example loading all use the three rules
above. Existing panel/full-builder replacement controls need no marker. Mark only exits whose target does not
express abandonment, including desktop/mobile switch controls. No callback or request survives the dirty modal.

### Alternatives rejected or superseded

- **Check every request or canvas update:** blocks Save, previews/background work or updates preserving the draft.
- **Per-opener checks or an endpoint list:** unnecessary when resolved targets and a source marker express intent.
- **Own-`hx-target`-only guard:** misses inherited/programmatic targets; the old two-dialog claim was not established.
- **Single HTMX hook with no direct entry points:** too late for actions that clear the panel before a request.
- **Replay through `htmx.ajax` or `issueRequest(true)`:** contradicts discard-and-repeat. The ordinary clean-panel
  destructive confirmation may use normal HTMX confirmation, but never resumes a dirty-interrupted action.

## Files to touch

- `theme/static/scripts/side_panel_utils.js` — shared helper, target-or-marker HTMX listener, direct close handling;
  remove all pending continuations, URL list, beforeRequest cancellation and timeout.
- `theme/static/scripts/support.js` — remove deferred wrapper; central target-based guard handles its AJAX.
  Ensure only actual requests create busy/bookkeeping/open/fallback side effects.
- `theme/static/scripts/simplified_inputs/workspace.js` — boolean check before close/base-view/read.
- `theme/static/scripts/model_comparison.js` and `model_builder_main.js` — ordinary confirmations respect the
  earlier central dirty gate; remove separate dirty handling and retain clean destructive confirmation.
- `components/model_tab_strip.html`, mobile controls in `upload_download_reboot_model_tooltips.html` and other
  non-replacement exits — `data-discards-side-panel` marker. No new marker for ordinary replacement targets.
- `modals/warn_before_side_panel_closing_modal.html`, `model_builder_main.html` and user Close/Cancel controls,
  notably `simplified_inputs/timeseries_panel.html` — fixed handlers/copy, shared user-exit gate.
- Existing guard, Feedback, Simplified, comparison and reset-confirm Jest suites; E2E forms, model comparison,
  Data & privacy/Feedback, Simplified and destructive-exit flows — migrate replay expectations.
- Workspace/rendering architecture and build/compare design journeys — document the simpler rule with
  implementation. The follow-up kickoff no longer owns replay cleanup; dirty detection stays separate.
- `CHANGELOG.md` — production fix entry when implemented.

## Tests and acceptance

- Shared helper: dirty/clean, Keep editing retains the form, Discard only closes, repeated action proceeds.
- HTMX eligibility: resolved literal/inherited/programmatic replacement targets; arbitrary-URL marked exits;
  unmarked `hx-swap="none"`, canvas/OOB updates, Save/preview and unrelated/background requests pass. No URL cases.
- Guard ordering: one prompt per click. A blocked dirty removal/reset/example request cannot reach native confirm,
  request loading or destructive execution. Repeated clean action uses its ordinary confirmation.
- Feedback's AJAX is caught centrally, with no own dirty check and no canceled-request busy/open/fallback side
  effects. Direct Simplified and Close/Cancel exits stop before UI changes. Update callback mocks accordingly.
- Rewrite `tests/e2e/test_forms.py::test_pending_request_preserves_hx_vals` and the cross-slot Continue-switches
  test in `test_model_comparison.py`: Discard sends nothing/navigates nowhere; repeat preserves values/locks.
  Extend existing Data & privacy/Feedback, Simplified, close/cancel, +Add and destructive-exit coverage.
- Save, validation/preview, export and Compare/same-slot draft preservation remain covered. Assert requests/state,
  and modal copy once. Keep Configure's independent draft rules.
- No stored request/event/callback, URL registry, per-opener dirty branches, dirty replay, hand-parsed request,
  guard `eval`, beforeRequest cancellation or loading timeout remains. Keep dirty detection and Save-path `eval`.
- Run affected Jest suites, full `npm run jest` and local E2E guard flows at implementation time. This planning
  update does not claim a passing implementation or change production code.

## Flags and decisions

- 2026-11-03, user review: all dirty exits use discard/close/repeat. Later review the same day simplified
  interception to resolved replacement targets or an explicit source marker, plus direct checks only where UI
  cleanup precedes/has no request. This supersedes the earlier per-flow request classification and Feedback check.
- Keep the current dirty flag and unrelated Save/recomputation `eval`; their redesign is separate work.
- Task 2 shares `side_panel_utils.js`; run adjacent. Standard implementation difficulty; no library or schema change.
- Update the owning architecture/journey docs with implementation. Keep the follow-up replay cleanup removed.
