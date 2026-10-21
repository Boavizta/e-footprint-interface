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

`specs/features/server-rendered-state-follow-up/kickoff.md` (Group 2, "Deferred side-panel request replay") already plans to make all three block.

## Reproduction
- none — the settled fix (Decisions, 2026-10-21) replaces the replay contract rather than correcting it: after "Discard changes" nothing is issued and the user repeats the click, as the mission's guards-block rule requires. The boosted-link misfire exists only inside the replay path that the task deletes, so there is no expected behaviour of the current mechanism to assert. The new contract is pinned by the tests listed under Tests (Jest branch cases and the rewritten and new E2E tests), which the task names as its public-contract tests. The misfire was shown in jsdom only; the new Data & privacy E2E confirms it in a browser and is the test to watch fail first if a reviewer wants the defect observed.

## Fix approach

**Recommended: make this guard block, and move it to `htmx:confirm`.**
1. Delete the `htmx:beforeRequest` listener (`side_panel_utils.js:127-139`), `pendingRequest` (`:2`, resets at `:61`, `:77`) and `proceedWithPendingRequest()` (`:199-220`). This removes the hand parsing, the `eval` and the `hideLoadingBar` timeout.
2. In the existing `htmx:confirm` listener (`:162-171`), also intercept, while `formModified`, any request whose `detail.elt` has its own `hx-target` of `#sidePanel`. Keep that exact predicate so the scope matches today's. Do not test `detail.target`: that would newly catch the `htmx.ajax` openers that already run through `runAfterSidePanelDiscardConfirmation`, and stack two dialogs. On a match it shows `#unsavedModal`, and the confirm button (relabelled "Discard changes", see below) calls the existing `closeWarningModalAndCloseSidePanel()` (`:222-225`). The edits are discarded, the panel closes, and nothing is issued. The user clicks the card again, and that request runs as authored: verb, url, inherited values, locks.
3. The cancel button (relabelled "Keep editing") keeps its current meaning. Its `hideLoadingBar()` becomes unnecessary for this path.

This fixes the boosted-link misfire with no special case, because nothing is replayed. The `hx-post` form is handled the same way.

**Scope (decided 2026-10-21: option a).** Convert only the `#sidePanel` guard, as above. The navigation guard (`pendingNavRequest`/`issueRequest(true)`, `side_panel_utils.js:160-181`) and `runAfterSidePanelDiscardConfirmation` (`:106-125`) break the same mission rule but stay for `server-rendered-state-follow-up`. This task narrows that feature's kickoff row to them. Converting all three now (option b) was declined: it changes the switch-model, +Add, Simplified-entry and Support flows and belongs with the follow-up.

**Modal copy (decided 2026-10-21: discard wording).** `#unsavedModal` is a single instance, included once at `model_builder/templates/model_builder/model_builder_main.html:84` from `modals/warn_before_side_panel_closing_modal.html`. All four paths share it, and each only rewires the Continue `onclick`:
- the `#sidePanel` guard (this task; blocks after the change);
- the navigation guard (`:168-169`, still re-fires the request);
- `runAfterSidePanelDiscardConfirmation` (`:113-115`, still runs the stored action; called from `simplified_inputs/workspace.js:40` and `support.js:42`);
- `warnBeforeClosingSidePanel` (`:191-193`, closes the panel).

So the copy must stay true whether the action then proceeds or not. Wording that only names the discard does:

| Where | Current | New |
|---|---|---|
| `model_builder_main.html:84`, `message` | "The currently opened side panel has pending changes. Would you like to continue and lose them ?" | "The open side panel has unsaved changes. Discard them?" |
| `warn_before_side_panel_closing_modal.html:12`, `#cancel-unsaved-modal` | "No, Cancel" | "Keep editing" |
| `warn_before_side_panel_closing_modal.html:20`, `#continue-unsaved-modal` | "Yes, Continue" | "Discard changes" |

Every path discards on the confirm button. The replaying paths then also carry on with the switch, add or entry, and nothing in the wording promises otherwise. Labels use initial capital only (`specs/design/writing-style-guide.md:9`). The button ids stay unchanged: tests select `#continue-unsaved-modal`/`#cancel-unsaved-modal`, and no test or JS reads the label text. Two design journey pages quote the old strings verbatim and must follow (style guide `:14`).

**Rejected:**
- *Shrink to `htmx.ajax("GET", hx-get, {source})`* (intake option 1). It still stores the continuation against the mission, and it keeps the boosted-link bug. A `url = hx-get || href` patch would add special cases and still hard-code GET.
- *`htmx:confirm` + `detail.issueRequest(true)` replay* (intake option 2). This would be the correct mechanism if replay were wanted. It re-issues the exact request, boosted anchors included, and the probe confirmed `htmx:confirm` fires for clicks, boosted anchors, `hx-trigger="load"` and `htmx.ajax` with or without source. But it is still suspend-and-replay. It also keeps a stored request whose source element can be swapped out while the modal is open (for example, the storage-status region refreshes out-of-band). In that case `issueAjaxRequest` silently drops it (htmx.js:4256-4259).

## Files to touch
- `e-footprint-interface/theme/static/scripts/side_panel_utils.js`:
  - remove `pendingRequest` (`:2`, resets at `:61` and `:77`), the `htmx:beforeRequest` guard (`:127-139`, including the `hideLoadingBar` timeout) and `proceedWithPendingRequest()` (`:199-220`);
  - extend the `htmx:confirm` listener (`:162-171`). Add a branch that intercepts, while `formModified`, a request whose `detail.elt.getAttribute("hx-target") === "#sidePanel"`. It shows `#unsavedModal` with Continue wired to `closeWarningModalAndCloseSidePanel()` (`:222-225`). It never calls `issueRequest`. The existing `PANEL_DISCARDING_PATHS` branch and `proceedWithPendingNavigation()` stay as they are;
  - rewrite the guard comment (`:141-154`). It names the old beforeRequest guard; say the `#sidePanel` branch blocks and the path branch still re-fires, pending `server-rendered-state-follow-up`.
- `e-footprint-interface/model_builder/templates/model_builder/modals/warn_before_side_panel_closing_modal.html`:
  - `:9`: Cancel `onclick` becomes `closeWarningModal()`. Drop `hideLoadingBar()`: no remaining path opens the modal after `htmx:beforeRequest`. The navigation guard runs on `htmx:confirm`, the discard helper runs before its `htmx.ajax`, and close issues nothing;
  - `:12`: "No, Cancel" becomes "Keep editing";
  - `:20`: "Yes, Continue" becomes "Discard changes".
- `e-footprint-interface/model_builder/templates/model_builder/model_builder_main.html:84`: `message="The open side panel has unsaved changes. Discard them?"`.
- `e-footprint-interface/specs/design/journeys/build-a-model.html:358`: quote the new message. Mention that confirming discards and closes the panel, and that the user repeats the click.
- `e-footprint-interface/specs/design/journeys/compare-models.html:638`: quote the new message and the labels (**Keep editing** / **Discard changes**). The switch still proceeds after the discard.
- `e-footprint-interface/specs/architecture/workspace.html:41-43`:
  - `:41`: keep the navigation guard description ("Continue" re-fires) but use the new label;
  - `:43`: replace the "older `htmx:beforeRequest` guard" sentence. The same `htmx:confirm` listener also catches elements with their own `hx-target="#sidePanel"`, and those block: Discard closes the panel, nothing is issued, and the user repeats the click.
- `e-footprint-interface/specs/features/server-rendered-state-follow-up/kickoff.md:40`, "Deferred side-panel request replay" row. Narrow it to the two remaining continuations:
  - the `htmx:confirm` navigation guard with `proceedWithPendingNavigation()`/`issueRequest(true)`;
  - `runAfterSidePanelDiscardConfirmation()` with `pendingSidePanelReplacement`/`proceedWithPendingSidePanelReplacement()`.

  Note that the `#sidePanel` guard already blocks (bug-fixes-2026-10). Drop the references to the beforeRequest guard, `proceedWithPendingRequest()`, hand-parsed attributes and `eval`.

## Tests
- **Jest, extend `js_tests/side_panel_switch_guard.test.js`.** Fire a cancelable `htmx:confirm` whose `detail.elt` carries `hx-target="#sidePanel"`, as `fireNavConfirm` does with a stub `elt`:
  - modified: the event is default-prevented, the modal is shown, and the Continue `onclick` is `closeWarningModalAndCloseSidePanel()`, not a replay;
  - unmodified: not intercepted;
  - an element without its own `hx-target="#sidePanel"`, with a path outside `PANEL_DISCARDING_PATHS`: not intercepted;
  - after Continue: `formModified` is false, `#sidePanel` is emptied, and nothing is re-issued (the stub `issueRequest` is not called);
  - an event that matches both branches (own `hx-target="#sidePanel"` and a path in `PANEL_DISCARDING_PATHS`) shows the modal once. The navigation tests (`:43-112`) stay unchanged.
- **E2E, rewrite `tests/e2e/test_forms.py::TestUnsavedChangesWarning::test_pending_request_preserves_hx_vals` (`:67-114`).** It encodes the replay. New outcome: modified Job form, click Server "add service", modal, `#continue-unsaved-modal` ("Discard changes"). The side panel is closed and no `open-create-object-panel/Service` request is sent. Clicking the button again sends the request with `efootprint_id_of_parent_to_link_to` and disables the button until the response. Suggested name: `test_continue_discards_and_next_click_opens_panel`.
- **E2E, new: boosted Data & privacy while dirty.** Modified form, Help, Data & privacy, modal, Continue. The panel is closed and no request for `/model_builder/` is sent. Clicking Data & privacy again shows `.data-privacy-card`. Use `tests/e2e/pages/model_builder_page.py:119` (`open_data_privacy_from_help_menu`). Today this test fails: the builder page lands in `#sidePanel`.
- **E2E copy check:** assert the modal message and both labels once, for example in `test_warns_when_closing_panel_with_unsaved_changes` (`test_forms.py:26-44`).
- **Keep:**
  - `test_warns_when_closing_panel_with_unsaved_changes` and `test_warns_when_opening_new_panel_with_unsaved_changes` (`test_forms.py:26-65`), whose Cancel path is unchanged;
  - the navigation tests in `js_tests/side_panel_switch_guard.test.js` and `tests/e2e/test_model_comparison.py:501-538`;
  - the `#unsavedModal` checks in `test_simplified_inputs.py`, `test_source_metadata.py`, `test_weekly_pattern_builder.py` and `test_help_drawer_overlay.py`.

  All of them select by id and need no change.

## Acceptance criteria
- A dirty side panel plus a click on any element with `hx-target="#sidePanel"` shows the unsaved modal, and no request is sent (loading bar not started).
- "Discard changes" discards the edits and closes the side panel, with no request. The next click on the same element opens the requested panel with its own `hx-vals` (ancestor ones included) and its `hx-disabled-elt` lock.
- "Keep editing" leaves the panel and its edits untouched.
- The shared modal reads "The open side panel has unsaved changes. Discard them?" with "Keep editing" / "Discard changes" on every path. Switching models, +Add, Simplified entry and Support still proceed after "Discard changes", as today.
- Help → Data & privacy (and the storage-warning link) with a dirty panel never loads the builder page into `#sidePanel`.
- `side_panel_utils.js` contains no `eval`, no `pendingRequest` and no `htmx:beforeRequest` listener.

## Risks and side effects
- **Behavior change (intended, mission-mandated):** after confirming, the user clicks the target again instead of seeing it open. The mission accepts this as a rare path.
- **Pre-existing, not addressed:** card triggers run hyperscript `on click … add .model-builder-card-opened` even when the request is blocked, so on Cancel the highlight moves to the clicked card while the old panel stays. Continue clears highlights through `closeAndEmptySidePanel()` (`side_panel_utils.js:79`).
- **Order of listeners:** the `htmx:confirm` listener in `model_comparison.js:262-273` (remove-model) and the one in `model_builder_main.js` (`data-confirm-when-model-not-empty`) match different elements. None of them carries `hx-target="#sidePanel"`, so no dialogs stack.
- **Two semantics on one modal (accepted with option a):** the `#sidePanel` branch blocks while navigation and the discard helper still carry on. The neutral copy keeps both true. Document it in `workspace.html` until the follow-up lands.

## Flags
- **Mission invariant:** `specs/mission.md:26-28`, guards block. Constitution §1.4 is unaffected: no server response is softened.
- **JavaScript convention:** `specs/conventions.md:28,30`. No request continuations. User requests keep their own `hx-disabled-elt`, which a fresh click honors natively.
- **Overlap:** `specs/features/server-rendered-state-follow-up/kickoff.md:40` keeps the navigation and discard-helper continuations. This task narrows that row.
- **No migration, serialization or cross-repository change.** Interface-only JavaScript and templates.
- **Local-only validation:** `npm run jest` and `poetry run pytest tests/e2e -n 4` against a local server. The boosted-link misfire was shown in a jsdom probe with the real htmx; confirm it in the browser as part of the new E2E test.

## Decisions
- 2026-10-21: Scope (a). Convert only the `#sidePanel` `htmx:beforeRequest` guard into a blocking `htmx:confirm` branch. The navigation guard and `runAfterSidePanelDiscardConfirmation` stay for `server-rendered-state-follow-up`, and this task narrows its kickoff row (`kickoff.md:40`).
- 2026-10-21: Modal copy uses discard wording on the shared `#unsavedModal`: message "The open side panel has unsaved changes. Discard them?", buttons "Keep editing" / "Discard changes". It names only the discard, so it stays true for the paths that still proceed. Button ids are unchanged.
