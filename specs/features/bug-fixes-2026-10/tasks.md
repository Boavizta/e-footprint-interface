# bug-fixes-2026-10 — tasks

**Status:** Run A implemented and reviewed (2026-11-03); Runs B and C remain planned.
Completed walkthrough: [`run-a-review.html`](run-a-review.html). Remaining work:
[`plan.html`](plan.html). Each task keeps its original number and diagnostic below.

| Run | Tasks in execution order | Prerequisites / release boundary |
|---|---|---|
| A — complete | 5 → 4 → 6 → 8 → 11 → 3 | Independent release checkpoint: publish the Run A library changes, restore a PyPI pin in the interface, and validate the published package before merging the interface to `main`. No dependency on B/C or Task 16. |
| B — planned | 9 → 10 → 12 → 2 → 1 → 7 → 16 | Run A implementation; Task 16 is the newly recorded group-member confirmation follow-up. |
| C — planned | 13 → 14 → 15 | Run B; Task 13 follows Task 16 in the shared deletion use case. |

Use a fresh `feature-implement` session for each remaining run. Release each completed run
independently using the [Run A checkpoint](run-a-review.html#merge-checkpoint) as the first boundary.

The original intake for Reports 1–3 (parked during `request-lifecycle-simplification`, evidence on
`dev` at `2eced3c0`) is kept below for traceability; the diagnostics supersede it where they differ.

## Original intake (Reports 1–3)

### Report 1 — side-panel unsaved-changes replay hand-parses htmx attributes

- **Kind:** cleanup, no user-visible defect.
- **Symptom:** none. `proceedWithPendingRequest()` in `theme/static/scripts/side_panel_utils.js`
  (around lines 199–219) re-issues a deferred `#sidePanel` request by reading `hx-get`,
  `hx-target`, `hx-swap` and `hx-vals` itself, evaluating a `js:` prefix with `eval`, and passing
  all of it to `htmx.ajax`.
- **Why it is redundant:** the request-lifecycle run (Task 6) added `source: pendingRequest` to that
  call so the replay inherits the element's `hx-disabled-elt` and `hx-indicator`. With a `source`,
  htmx already resolves target, swap and `hx-vals` from that element. The hand parsing and the
  `eval` can go.
- **Fix direction:** shrink the call to the url and the source. A better option is to retire the
  `htmx:beforeRequest` guard (lines 127–139) in favour of the `htmx:confirm` + `issueRequest`
  pattern the navigation guard in the same file already uses (lines 164–181), so the deferred
  request is replayed exactly as issued.
- **Proposed slug:** `side-panel-replay-hand-parsing`.

### Report 2 — `htmx:oobErrorNoTarget` logged by membership-section out-of-band regions

- **Kind:** console error, no user-visible defect. Pre-existing: the request-lifecycle Task 3
  reviewer confirmed it predates `a12771fe`.
- **Symptom:** canvas inline count edits and model-comparison count saves log
  `htmx:oobErrorNoTarget`; so does edge device-group linking.
- **Mechanism:** `_run_edit_and_present()` in
  `model_builder/adapters/views/views_dict_mutation.py` (around line 52) always adds a
  `dict_membership_section` out-of-band region for the child object, even when no edit panel is
  open, so the fragment has no `#dict-membership-section-<id>` target. The list-membership path in
  `model_builder/adapters/views/views_list_mutation.py` (around line 36) does the same with
  `list_membership_section`. Both are rendered by
  `model_builder/adapters/presenters/oob_regions.py`.
- **Fix direction:** emit the membership-section region only when the client reports the panel
  open (the request can carry the open panel's object id), or tolerate the missing target. Decide
  during diagnosis; the first keeps responses smaller.
- **Proposed slug:** `membership-section-oob-no-target`.

### Report 3 — delete-card modal hyperscript removes a card the response already removed

- **Kind:** console error, no user-visible defect. Pre-existing (same confirmation as report 2).
- **Symptom:** after a card deletion, the browser logs an "is null" error from hyperscript.
- **Mechanism:** `model_builder/templates/model_builder/modals/delete_card_modal.html` (lines 9–10)
  runs `remove #<card web id>` on `htmx:afterRequest` when `remove_card_with_hyperscript` is set
  (`model_builder/adapters/presenters/htmx_presenter.py` line 381, cleared for mirrored objects at
  line 402). By then the response has already removed the card, so the selector resolves to null.
- **Fix direction:** have the server emit an out-of-band delete for the card and drop the
  hyperscript and its context flag. Diagnosis should check whether the mirrored case (flag
  cleared) already relies on the response alone, which would confirm the hyperscript is dead.
- **Proposed slug:** `delete-card-modal-hyperscript-null`.

## Tasks

Task numbers follow arrival order: Tasks 1–3 are parked Reports 1–3, Task 4 is GitHub #151, Task 5
is GitHub #146, Task 6 was found while diagnosing #151, Task 7 is GitHub #150, Tasks 8–9 were found while
diagnosing Task 6, Task 10 while diagnosing Task 9, Tasks 11–12 are smell-sweep bugs S1 and S2, and
Tasks 13–15 are user-approved smell-sweep refactors. Task 16 is the pre-existing grouped-member
confirmation bug discovered during Run A review and planned as a Run B follow-up.

## Task 1 — One dirty-side-panel guard: discard, close, repeat

**Goal:** Every user action that would abandon unsaved side-panel edits uses one discard-and-repeat
rule. Block the action before its request or destructive UI change, show "The open side panel has
unsaved changes. Discard them?", and offer "Keep editing" / "Discard changes". Keep editing leaves
the panel and edits intact. Discard changes closes and clears the panel, issues no interrupted
request and performs no interrupted action. The user repeats the action, which then runs as authored.
This fixes the boosted Data & privacy replay misfire and applies the mission's guards-block rule.

Review decision 2026-11-03: unify all dirty-side-panel handling now. This supersedes the 2026-10-21
scope limited to own-`hx-target="#sidePanel"` elements. Include card/add/edit and Data & privacy
openers, Feedback, +Add (blank/duplicate/import), model switching (including cross-slot Compare
dismissal), entry into Simplified inputs, close/cancel, model removal, reset and example loading.
Opening Compare, returning to the same model, help-drawer use and export preserve the draft and
need no warning. Save and validation/preview requests must remain usable while dirty. Keep
Configure's existing separate unsaved-draft rules; this task unifies the side-panel draft only.

**Diagnostic:** [`diagnostics/side-panel-replay-hand-parsing.md`](diagnostics/side-panel-replay-hand-parsing.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `theme/static/scripts/side_panel_utils.js` — one boolean blocking helper (for example,
  `blockIfSidePanelDirty()`: clean → false; dirty → show the shared modal and return true), one
  `htmx:confirm` entry point for panel replacement/navigation, and thin JS/close entry points.
  Resolve the actual HTMX destination so inherited targets, boosted links and `htmx.ajax` are
  covered; also classify full-builder replacements and model exits. Exclude current-form Save,
  validation and previews from discard actions. Remove `pendingRequest`, `pendingNavRequest`,
  `pendingSidePanelReplacement`, all three `proceedWithPending…` functions, the callback-taking
  `runAfterSidePanelDiscardConfirmation`, and the beforeRequest guard/loading-bar timeout.
  No source element, event detail or callback is stored for later execution.
- `theme/static/scripts/support.js` — Feedback checks the boolean helper before setting busy state
  or starting its request; remove the deferred callback wrapper. HTMX guards must not turn a blocked
  opener into a completed request, fallback navigation or panel-open side effect.
- `theme/static/scripts/simplified_inputs/workspace.js` — check before closing the panel, changing
  base view or sending the entry/configure read; Discard alone never enters Simplified inputs.
- `theme/static/scripts/model_comparison.js` — keep model navigation under the same dirty gate.
  Model removal must stop at that gate before its destructive confirmation: first click shows only
  the shared dirty warning; Discard only closes the panel; repeated Remove shows the ordinary
  destructive confirm. Remove its separate dirty-message concatenation. Retain normal clean-panel
  destructive confirmation; no interrupted removal is resumed.
- Audit reset/example-load and any other UI exits that clear the panel: apply the same gate before
  separate confirms or destructive changes. Include `theme/static/scripts/model_builder_main.js`
  (the existing `htmx:confirm` reset confirmation), and affected templates such as
  `onboarding/template_picker.html` / reset controls if intent markup is needed. Coordinate listener
  ordering explicitly so a prevented dirty exit cannot also open a native confirmation.
- `model_builder/templates/model_builder/modals/warn_before_side_panel_closing_modal.html` — fixed
  button handlers: Keep editing closes only the warning; Discard calls
  `closeWarningModalAndCloseSidePanel()`. No per-opener rewiring or `hideLoadingBar` call.
- `model_builder/templates/model_builder/model_builder_main.html` — new modal message. Audit close
  and Cancel controls, including `simplified_inputs/timeseries_panel.html`, so user abandonment
  goes through the shared gate. Successful Save and server-directed cleanup still use the low-level
  close function directly; never guard cleanup after a successful operation.
- `specs/architecture/workspace.html`, `specs/architecture/rendering.html` and the build-a-model /
  compare-models design journeys — document the shared rule, all entry points and the second click;
  remove replay language and reset/example/remove special dirty handling.
- `specs/features/server-rendered-state-follow-up/kickoff.md` — remove the deferred side-panel replay
  row because Task 1 now owns all of it. Keep the independent dirty-detection improvement deferred.
- `CHANGELOG.md` — `## [Unreleased]` fix entry covering the unified behavior.

**Tests added/changed:**
- `js_tests/side_panel_switch_guard.test.js` — rewrite replay expectations around the shared helper
  and HTMX entry point: clean/dirty, Keep editing, Discard issues nothing, repeat runs normally,
  resolved/inherited target and programmatic request, navigation, close/cancel, and one modal per click.
  Assert no dirty requests reach the request/loading-bar stage; Save/preview and non-destructive
  actions remain allowed. Cover reset/example/removal ordering with their ordinary confirmations.
- `js_tests/support.test.js`, `js_tests/simplified_inputs.test.js`, `js_tests/model_comparison.test.js`
  and existing reset-confirm tests — replace callback/replay mocks and expectations. Blocked Feedback
  and Simplified entry have no request, fallback, busy-state or base-view changes; Discard alone
  performs none of these actions. Dirty removal does not show its native confirm or remove a model.
- `tests/e2e/test_forms.py::test_pending_request_preserves_hx_vals` — rewrite: Discard closes the
  panel and sends nothing; the repeated click carries the original `hx-vals` and button lock.
  Add dirty-panel Data & privacy and close/cancel checks; verify the new copy once.
- `tests/e2e/test_model_comparison.py` — rewrite the cross-slot Continue-switches regression:
  Discard stays on the current slot; repeating the switch navigates. Keep same-slot/Compare draft
  preservation; cover +Add and the dirty-then-clean removal sequence.
- Extend `tests/e2e/test_data_privacy.py` Feedback coverage and Simplified-input entry E2E coverage for Keep editing, Discard-only
  close and successful repeated action. Cover dirty reset/example-load without stacking confirms.
  Reuse existing fixtures; assert requests and visible state, not just modal text.

**Acceptance:**
- Every supported dirty-panel exit follows the same block → discard/close → repeat contract.
  No pending request/event/callback state or dirty-action replay remains in these paths.
- A click produces at most one confirmation. Dirty removal/reset/example loading cannot execute
  from Discard; ordinary destructive confirmation remains required on the repeated clean action.
- Actual destinations, not only the source's own `hx-target`, determine panel replacement. All
  declarative, boosted, inherited-target and JS entry points use the same dirty decision.
- Save, validation/preview, export, opening Compare and same-slot return preserve their intended
  behavior. Keep editing retains the draft. Clean-panel actions proceed normally.
- The guard path has no `eval`, hand-parsed request or `htmx:beforeRequest` listener. The separate
  Save-path `eval` in `setRecomputationToTrueIfResultPaneIsOpen` remains outside scope (decision 1).
- No deferred side-panel replay task remains in the follow-up kickoff. Retain the current dirty
  flag for this task; improving how dirty state is detected is separate work.

**Depends on:** none. Run next to Task 2 (shared `side_panel_utils.js`).

**Implementation:** standard — one decision/modal implementation and small entry points; migrate
all existing callers and their tests. Run affected Jest suites, then full Jest and E2E guard flows.

## Task 2 — Emit the dict membership-section OOB region only when that section is mounted

**Goal:** Dict count edits and unlinks posted from the canvas (inline step/job counts, edge
device-group entry count and ✕, model-comparison count saves) no longer log
`htmx:oobErrorNoTarget`. Settled 2026-10-21: keep the canvas → open-child-panel count sync. A
`dictMembershipVals(id)` helper beside `recomputationVals()` posts `membership_section_mounted`
when `#dict-membership-section-<id>` is in the DOM, and `_run_edit_and_present` adds the
`dict_membership_section` region only when that flag is posted. The list-membership path is not
affected (its endpoints are posted only from inside the mounted section) and stays unchanged.

**Diagnostic:** [`diagnostics/membership-section-oob-no-target.md`](diagnostics/membership-section-oob-no-target.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `theme/static/scripts/side_panel_utils.js` — `dictMembershipVals(id)` helper (bookmarks
  `mounted` precedent, `bookmarks.js:105-111`).
- `model_builder/templates/model_builder/object_cards/partials/dict_entry_count_unlink.html`
  (around lines 15, 24) and `model_builder/templates/model_builder/side_panels/edit/dict_membership_section.html`
  (around line 28) — spread the helper into `hx-vals`.
- `model_builder/adapters/views/views_dict_mutation.py` — add the region only when the flag is
  posted (around line 52).
- Run `npm run jest` once: it rebuilds the gitignored `js_tests/fixtures/inline_count_autosave.html` from the changed template.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/e2e/test_model_canva.py::TestModelCanvas::test_canvas_dict_count_edits_and_unlinks_log_no_console_error`
  — reproduction; remove its expected-failure marker. No other tests (no Jest case: `dictMembershipVals` is an
  `hx-vals` transport detail the reproduction drives both ways).

**Acceptance:**
- The reproduction passes with its marker removed.
- No `htmx:oobErrorNoTarget` on any listed path, with or without a panel open, in one- and
  two-model workspaces.
- With the child's edit panel open, a canvas count edit still updates the panel's count.

**Depends on:** none.

**Implementation:** easy — known cause, one helper, one server condition; tests are specified.

## Task 3 — The server owns card removal on delete; drop the delete-modal hyperscript

**Status:** complete (Run A).

**Goal:** No card deletion logs hyperscript `'#…' is null` or `htmx:oobErrorNoTarget`, and every
deleted card leaves the active canvas without a reload. The modal hyperscript is not dead: for a
plain top-level deletion with no constraint flip (unused journey, non-last usage pattern,
`EdgeUsagePattern`, ungrouped edge device, job-less server or API) it is the only remover, while
for nested cards its root-form selector never matches. `DeleteObjectOutput` carries the card's
`web_id`, captured before `self_delete()`. For a non-list deletion without a `model_canvas` region,
`present_deleted_object` emits `<div id="{web_id}" hx-swap-oob="delete"></div>` first in the
response. The modal's `script=` attribute, the `remove_card_with_hyperscript` flag and the
unreachable `HX-Reswap: none` branch go.

**Diagnostic:** [`diagnostics/delete-card-modal-hyperscript-null.md`](diagnostics/delete-card-modal-hyperscript-null.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/application/use_cases/delete_object.py` — `web_id` on `DeleteObjectOutput`
  (around line 35), set in the normal-deletion return (around lines 226–235).
- `model_builder/adapters/presenters/htmx_presenter.py` — `present_deleted_object` (around lines
  331–342): prepend the OOB delete, drop the `HX-Reswap` branch; `present_delete_confirmation`: drop
  `remove_card_with_hyperscript` (around lines 381, 402).
- `model_builder/templates/model_builder/modals/delete_card_modal.html` — remove `script=` (lines
  9–10).
- `specs/architecture/rendering.html` — one line beside "Mutation entry points": the server owns
  card removal on delete; no client-side remover.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/e2e/objects/test_jobs.py::TestJobs::test_deleting_nested_and_top_level_cards_logs_no_console_error`
  — reproduction; remove its expected-failure marker. No other tests.
- `tests/unit_tests/adapters/presenters/test_htmx_presenter.py::test_successful_crud_presentations_append_one_metadata_status_oob`
  — drop the `HX-Reswap == "none"` assertion and give its `DeleteObjectOutput` a `web_id`.
- Existing comparison, full-journey and `test_usage_journeys.py::test_delete_usage_journey` deletion E2E keep passing.

**Acceptance:**
- The reproduction passes with its marker removed.
- Deleting any card (top-level, nested, mirrored, constraint-flipping, root edge group) logs no
  console error.
- Top-level no-flip deletions remove the card from the active canvas only; a parked comparison
  canvas is untouched.

**Depends on:** Task 11 (soft: it narrows list/dict deletion to nested-card containers) and Task 4
(soft: after it, nested-need deletions stop crashing and rely on this removal too). Shares
`CHANGELOG.md` with both.

**Implementation:** standard — small diff, but an HTMX/OOB transition (full review surface).

## Task 4 — Deleting a recurrent need: a detached wrapper leaves its target's container list

**Status:** complete (Run A).

**Goal:** Deleting a `RecurrentServerNeed` or any recurrent edge need (e.g. `RecurrentEdgeProcess`)
re-renders the parent edge usage journey card without the deleted need, with no error modal. The
library keeps `contextual_modeling_obj_containers` to exactly the attached wrappers: a contextual
wrapper registers on its target when attached and removes itself when detached, the rule dict keys
already follow. The readers' `is not None` filters go, and the interface needs no filter of its own.
Fixes GitHub #151, and the latent same-crash after an `edge_device` relink. Settled 2026-11-02: fixed
in the library, not in `ModelingObjectWeb`
([decision 3](run-a-review.html#decision-task-4)).

**Diagnostic:** [`diagnostics/recurrent-need-delete-render-error.md`](diagnostics/recurrent-need-delete-render-error.md)

**Repository:** cross-repo. Both parts land in the same run, the library part in `e-footprint` first.
`dev` carries the committed path dependency on `../e-footprint` until the independent Run A release
checkpoint. Publish the Run A library changes and restore a published PyPI pin before the interface
reaches `main` or preprod; Runs B/C need not be complete. No implementer publishes.

**Files touched — library part (`e-footprint`):**
- `efootprint/abstract_modeling_classes/contextual_modeling_object_attribute.py` — `__init__` (around
  line 17) registers only when given a container; `set_modeling_obj_container` (around line 25)
  registers on `None` → container and removes on container → `None`.
- `efootprint/abstract_modeling_classes/modeling_object.py` — new
  `remove_from_contextual_modeling_obj_containers` beside `add_to_…` (around line 482). It rebuilds the
  list with an `is not` comparison: `ContextualModelingObjectAttribute.__eq__` compares `_value`, so
  every wrapper in the list is "equal" and `list.remove` would drop a sibling's wrapper. Drop the
  filters in `modeling_obj_containers` (around line 460) and `nb_of_occurrences_per_container` (around
  line 801).
- `efootprint/abstract_modeling_classes/reactive_core/reverse_relationships.py` — drop the filter in
  `_containers_of_member_type` (around line 84).
- `specs/architecture/relationships.html` — one line in "Three relationship types": the list holds
  exactly the attached wrappers.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Files touched — interface part (`e-footprint-interface`):**
- `CHANGELOG.md` — `## [Unreleased]` fix entry.
- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` — no change.

**Run A release checkpoint, before the interface merges to `main`:** the user publishes the release, then `pyproject.toml` and
`poetry.lock` pin it, following `RELEASE_PROCESS.md`, and the interface `CHANGELOG.md` entry names the
upgrade.

**Tests added/changed:**
- `e-footprint`: `tests/abstract_modeling_classes/test_contextual_modeling_object_attribute.py` — a
  wrapper never attached is not registered; detaching removes only that wrapper among siblings on one
  target; re-attaching registers it again; `self_delete` leaves no entry on a shared target.
- `e-footprint`: `tests/abstract_modeling_classes/test_modeling_update.py` — an accepted list update
  leaves no entry from the old list; a rejected one restores the same wrapper objects (the scratch
  check's shape: `EdgeFunction.recurrent_edge_device_needs` plus a rejected sibling change).
- `e-footprint-interface`:
  `tests/unit_tests/adapters/views/test_views_deletion.py::test_recurrent_need_deletion_rerenders_its_edge_usage_journey_card`
  — reproduction; remove its expected-failure marker, running against the local dependency.

**Acceptance:**
- After any unlink, no entry of `contextual_modeling_obj_containers` has a `None` container, and a
  rejected `ModelingUpdate` restores the list's wrappers.
- `modeling_obj_containers`, `nb_of_occurrences_per_container` and reverse relationships return what
  they returned before, without their filters. `tests/performance_tests/benchmark_baselines.py` shows
  no meaningful regression.
- The reproduction passes with its marker removed, against the local dependency.
- Deleting a recurrent server or edge need on the Industrial IoT example shows no error modal; the
  canvas immediately matches what a reload shows.
- Deletion of jobs, steps, usage patterns and edge components is unchanged.

**Depends on:** none. Once shipped, nested-child deletions surface Task 3's hyperscript "is null" console error (previously masked by the
crash).

**Implementation:** standard — small diff with a verified cause, but it changes core link
bookkeeping across two repositories.

## Task 5 — Round daily chart emissions to significant figures so totals match the library

**Status:** complete (Run A).

**Goal:** The cumulative results chart ends at the same total as the Sankey and the library
(`system.total_footprint`), and small categories no longer show 0 in tooltips. Settled 2026-10-21:
`to_rounded_daily_values` rounds each daily value to 6 significant figures (vectorized NumPy)
instead of a fixed 5 decimals of the display unit. That costs about +68 % raw inline JSON at the
reporter's scale (259 KB → 436 KB) and bounds the total error at about 19 kg on 9.55 kt. JS display
rounding is unchanged. Fixes GitHub #146 (regression from `479e9a7f`) and helps #106.

**Diagnostic:** [`diagnostics/daily-emissions-rounding-drift.md`](diagnostics/daily-emissions-rounding-drift.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/domain/entities/web_core/model_web_utils.py` — `to_rounded_daily_values` (around
  lines 46–78): significant-figure rounding, docstring.
- `specs/architecture/layers-and-wrappers.html` — optional one-liner: chart daily series are rounded
  to significant figures so sums stay faithful to the library total.
- `CHANGELOG.md` — `## [Unreleased]` fix entry referencing #146.

**Tests added/changed:**
- `tests/unit_tests/domain/entities/web_core/test_model_web.py::TestModelWeb::test_system_emissions_daily_values_sum_to_library_total_over_long_large_unit_period`
  — reproduction; remove its expected-failure marker. No other tests.
- `tests/unit_tests/domain/entities/web_core/test_model_web_utils.py::test_to_rounded_daily_values_respects_aggregation_strategy`
  — drop or rename its `rounding_depth=1` keyword after the rename; expected values unchanged.

**Acceptance:**
- The reproduction passes with its marker removed.
- The cumulative chart's final point equals the Sankey total at the displayed 3 significant figures
  (the reporter's model shows 9.55 kt on both).
- No 0 tooltip for a category the library reports as non-zero.
- `window.emissions` keeps its shape (`dates`, `values`, `display_unit`).

**Depends on:** none. The draft `results-analysis` feature plans to retire
`EmissionsCalculationService`; the regression tests must carry over to its replacement.

**Implementation:** easy — one function, verified cause and settled precision.

## Task 6 — Internally held objects open a small read-only inspection panel

**Status:** complete (Run A).

**Goal:** Calculated-attribute links to internally held objects open one generic inspection panel
instead of an edit form. Show the object's name, “This object is managed automatically by
[parent name]. Edit its parent to change its inputs.”, links to its internal containers, and the
existing calculated-attributes section with formulas and charts. No input form, Save, Delete,
bookmarks or editable membership controls. Branch before form-context generation, deletion checks
and mirrored-card highlighting. This covers edge computer CPU/RAM, appliance components,
recurrent process/workload component needs and external API servers. Settled by user review
2026-11-03; replaces the 2026-10-21 editable-panel proposal. Objects classified as ordinary
retain their editable panels; their saves must also work when they have no canvas card.

**Diagnostic:** [`diagnostics/check-can-delete-keyerror.md`](diagnostics/check-can-delete-keyerror.md)
— recorded failures remain evidence; its previous fix/copy decisions are superseded by
[`PLAN-UPDATE-01`](run-a-review.html#plan-update-01).

**Repositories:** `e-footprint` (relationship metadata), `e-footprint-interface` (inspection panel
and saving editable objects that have no canvas card).

**Files touched:**
- Library `efootprint/abstract_modeling_classes/modeling_object.py` — add the derived property
  `internal_modeling_obj_containers`: distinct live parents that reference the object only through
  attributes absent from that parent's concrete `__init__` parameters. Group live contextual
  relationships by parent and inspect their attribute names with `get_init_signature_params`.
  A constructor-input relationship from that same parent makes the object ordinary relative to
  that parent, even if an additional non-constructor relationship exists. Constructor relationships
  from other parents do not cancel internal ownership. Ignore detached wrappers. Thus edge-computer
  storage remains ordinary through its `storage` input despite also belonging to `components`;
  CPU/RAM remain internal even when a separate need references them. This is a general rule, not a
  storage exception, creation-history flag or global library edit ban. No JSON change.
- `model_builder/adapters/views/views_edition.py` — early inspection branch using that property;
  retain ordinary editing for objects without internal containers. Supply wrapped parent links and
  the object for the existing calculated-attributes partial; bypass form generation and card
  highlighting rather than creating a disabled form.
- `model_builder/templates/model_builder/side_panels/edit/internal_object_panel.html` — new small
  generic panel, reusing the existing panel shell and calculated-attributes section.
- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` — retain
  Task 6's `.get(attr_name)`/skip for non-constructor entries in generic list-container discovery
  where other callers still need it; no new internal-component placement override.
- `model_builder/application/use_cases/edit_object.py` and
  `model_builder/adapters/presenters/htmx_presenter.py` — make the card-refresh path respect actual
  canvas placement: an editable object with no rendered card supplies no card-refresh targets.
  Decide this before mirror traversal or card-template lookup, including automatic-repair owners.
  Preserve persistence, success notifications, constraint OOB regions and result recomputation.
  Server storage and edge-computer storage have no canvas card; neither their own card nor the
  parent's card needs rendering on an ordinary storage edit. Do not add a storage-card template,
  redirect refreshes to the parent, or catch missing-template errors. Preserve refreshes for
  custom-device components that do have visible cards, including storage components.
- Library `specs/architecture/relationships.html` and interface
  `specs/architecture/forms-and-relationships.html` — document internal relationship metadata and
  the distinction between standalone inspection and parent-owned editing; interface
  `specs/architecture/rendering.html` records that panel availability and canvas-card presence
  are independent. Suggest a short pointer in the affected `AGENTS.md` / `CLAUDE.md` when implementing this pattern.
- Both `CHANGELOG.md` files — consolidated `## [Unreleased]` entries when implemented.

**Tests added/changed:**
- Library `tests/abstract_modeling_classes/test_modeling_object.py` — new public property contract:
  internal and constructor-held links, same-parent constructor references taking precedence over
  non-constructor references, separate referencing parents not exempting an internal object,
  detached wrappers, and the same result after a serialization round-trip.
- Rewrite the existing Task 6 reproduction in
  `tests/unit_tests/adapters/views/test_views_edition.py` for the agreed inspection behavior and
  remove its marker; extend its cases to CPU/RAM and appliance components. Assert parent links,
  calculated results, no editable controls and no form-context/mirror traversal. Existing formula
  and chart paths remain usable; Tasks 9/10 retain their separate known fixes.
- Add a focused direct-storage save regression in the same view-test module for server storage
  and edge-computer storage: open an editable panel, change a value/name, save without an error
  modal, reload to verify persistence, and assert no storage/parent-card OOB swap. Retain normal
  success feedback and result-update behavior. Verify a custom-device storage component still
  refreshes its visible card when renamed.
  The user observed the server save modal naming `model_builder/object_cards/storage_card.html`;
  source inspection confirms the unconditional card-render path, after persistence, and the absent
  template. The edge-storage reproduction previously demanded a parent-card swap; replace that
  expectation with a successful save without a card swap.
- The former `ExternalAPIServer` mapping addition and exclusion-test change are no longer required
  here: the inspection branch bypasses form resolution. Task 13 still owns resolver consistency.

**Acceptance:**
- All listed internal panels open from calculation links with no error modal, preserve inspection
  of results, and direct users to their parent for inputs.
- Server storage and edge-computer storage retain their own editable panels naturally under the
  membership rule; standalone saves persist and report success without rendering a nonexistent
  card or refreshing the parent. Existing result updates remain supported.
- Ordinary custom-device components retain normal editing and visible-card refreshes. The edge
  computer's own form still edits its nested storage, including metadata. No global edit ban.
- No new mirroring or card-refresh machinery is introduced for standalone internal-object edits.

**Depends on:** Task 4 (soft ordering: establishes live-wrapper bookkeeping). Ship immediately
before Task 8 in the same run so the inspection-only UI and direct-request guards land together.
Task 8 depends on the property added here; the previous wrong-card-refresh dependency is retired.

**Implementation:** standard — one library property and a small generic panel; cross-repository
contract and cardless-save regression with focused verification. The old editable-panel prototype
does not validate this design.

## Task 7 — Recurrent constant editor: show "each hour" after the unit

**Goal:** Every recurrent constant editor reads as a per-hour value. The unit box shows
`<unit> each hour`, for example "occurrence each hour" for the recurrent volume per edge device,
"GB_stored each hour" for storage and "cpu_core each hour" for compute. The helper text becomes "All
hours of the canonical week (168 hours) will use this value." "each hour" is display-only: it is not part
of the submitted `__constant_unit` value. Settled 2026-10-21: fix in the interface only (library units and
timeseries generation unchanged); keep raw pint unit notation; use one suffix for all fields; leave the
weekly-pattern editor unchanged. Fixes GitHub #150.

**Diagnostic:** [`diagnostics/recurrent-unit-each-hour.md`](diagnostics/recurrent-unit-each-hour.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/recurrent_quantities_from_constant.html`:
  move the unit box styling (lines 19-25) to a wrapper that holds the existing readonly input (borderless,
  `name`/`id`/`value` unchanged) and a `span` "each hour". Widen it from `w-25` if needed. New helper text
  (lines 28-30).
- `CHANGELOG.md`: `## [Unreleased]` fix entry referencing #150.

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_addition.py::test_recurrent_constant_editor_reads_as_a_per_hour_value`
  — reproduction; remove its expected-failure marker. No other tests.

**Acceptance:**
- The reproduction passes with its marker removed.
- Server-need, edge-process and component-need constant editors show `<unit> each hour` in one visual
  box, plus the new helper text.
- Posted units, saved models and results are unchanged.

**Depends on:** none.

**Implementation:** easy — one template and copy change; decisions settled.

## Task 8 — Internally held objects reject standalone edits and deletion

**Status:** complete (Run A).

**Goal:** Enforce Task 6's inspection-only rule for direct requests as well as the visible UI.
If `internal_modeling_obj_containers` is nonempty, a standalone edit is rejected before any
mutation or pre-edit hook; deletion confirmation blocks naming the internal parents, and deletion
execution rejects before container-removal discovery, unlinking or pre-delete hooks. Leave saved
state unchanged. The panel itself has no Delete control. Settled by user review 2026-11-03;
replaces the old “Delete stays visible” decision and standalone rename/card-refresh support.

**Diagnostic:** [`diagnostics/edge-component-delete-silent-noop.md`](diagnostics/edge-component-delete-silent-noop.md)
— the silent-delete evidence remains valid; the previous fix and rename acceptance are superseded
by [`PLAN-UPDATE-01`](run-a-review.html#plan-update-01).

**Repository:** `e-footprint-interface` (consumes Task 6's library property).

**Files touched:**
- `model_builder/application/use_cases/edit_object.py` — reject standalone edits of internally held
  objects immediately after lookup and before `pre_edit`, mutation or persistence. Use the existing
  exception-modal path, with wording explaining that the parent manages this object.
- `model_builder/application/use_cases/delete_object.py` — use the same property in
  `check_can_delete` before removal-target discovery, returning the internal parents' names; reject
  at the start of `_delete` before any unlinking or hooks, even without a confirmation request.
- `specs/architecture/forms-and-relationships.html` — standalone mutation guards apply to internal
  relationships; parent-owned edits and deletion cascades remain allowed.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- Rewrite the Task 8 reproduction in `tests/unit_tests/adapters/views/test_views_deletion.py`
  (now `test_internally_managed_objects_reject_standalone_edits_and_deletion`)
  and remove its marker. Replace the successful rename/card-swap assertion with refusal of a
  direct edit POST; keep blocked confirmation, refused delete POST and unchanged-state assertions.
  Cover CPU, RAM and appliance component, plus generated process/workload needs and an external
  API server using existing programmatic fixtures. Storage is an ordinary editable object under
  the refined rule; its successful standalone save belongs to Task 6's regression, not this
  internal-object rejection matrix.
- Existing device/API/process/workload deletion cascades and the custom-edge-device component flow
  must keep passing. Verify parent-form storage editing remains allowed, including metadata.
- Keep the three component wrappers and their existing container-override tests unchanged. There
  is no base-class swap, new `EdgeComponentWeb.mirrored_cards`, or internal rename/refresh support.

**Acceptance:**
- Direct standalone edit/delete requests cannot mutate an internally held object or persist a
  partial result; the user sees the existing error modal with the parent-management explanation.
- Direct deletion confirmation names the internal parents and never offers “Yes, delete”.
- The internal-object guards do not reject standalone server/edge-computer storage edits. Storage
  deletion still follows ordinary reference checks while its server/computer references it.
- Parent-owned storage edits and deletion with the parent still work: guards live at standalone
  use-case entry points, not in low-level library edits or cascade cleanup.
- Custom-device components without internal containers retain existing editing/deletion behavior,
  subject to Task 11's ordinary reference checks.

**Depends on:** Task 6 (hard: shared library metadata and inspection-panel contract). Ship in the
same run, immediately after it. Task 11 follows and preserves these guards.

**Implementation:** easy — early guards using Task 6's property and the existing error path;
rewrite the regression around the newly agreed behavior. Internal-object edits need no rendering
correction; Task 6 separately fixes successful saves of editable objects with no canvas card.

## Task 9 — Empty calculated dict entries render "no value" without a chart button; chart views show the error modal

**Goal:** Calculated dict entries the library leaves empty on purpose (e.g. `EdgeStorage`
`unitary_power_per_usage_pattern`, storage power treated as negligible, and the energy and
use-footprint dicts derived from it) render "no value" with formula and calculus-graph buttons and
no timeseries-chart button. `explainable_object_dict.html` picks each entry's template by
`sub_item.class_as_snake_str`, as the top-level calculated-attributes section already does. Any
unexpected failure in a calculated-attribute read view shows the standard exception modal instead
of an invisible raw 500 (constitution §1.4). Settled 2026-10-21: all four read views get
`@render_exception_modal_if_error`; smell-sweep S5 is folded in, so the other undecorated HTMX
fragment views get it too.

**Diagnostic:** [`diagnostics/hourly-chart-empty-timeseries-500.md`](diagnostics/hourly-chart-empty-timeseries-500.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/templates/model_builder/side_panels/edit/calculated_attributes/explainable_object_dict.html`
  — dynamic include by `sub_item.class_as_snake_str` (around lines 23–29).
- `model_builder/adapters/views/views.py` — `@render_exception_modal_if_error` on the hourly chart
  view (around line 569) and its siblings (around 584, 599, 612).
- Smell-sweep S5 ([`smell-sweep.md`](smell-sweep.md)): also decorate `ask_delete_object`
  (`views_deletion.py:14-15`), `get_calculus_graph`/`display_calculus_graph` (`views.py:438,448`),
  `source_table`/`source_table_row_editor` (`views.py:543,562`), `sankey_form`/`sankey_cards`/
  `sankey_delete_card` (`sankey_views.py:439,459,498`) and `open_help_drawer` (`views_help.py:8`).
  Leave a view undecorated only if it is a full page, a download, or a JSON/fetch endpoint with its
  own rejection path (check each, e.g. Sankey card deletion keeps its own completion), and note why.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_calculated_attributes.py::test_empty_calculated_dict_entries_render_no_chart_and_fragment_views_never_fail_silently`
  — reproduction; remove its expected-failure marker. No other tests: the other S5 views have no reachable defect on
  `dev`, and their decoration relies on the decorator's existing modal tests.

**Acceptance:**
- The reproduction passes with its marker removed.
- In the iot Factory-sensor panel, the three Sensor local storage dict entries show "no value",
  a working formula button and a calculus-graph link, and no chart button.
- Every hourly-chart link rendered on the four introductory examples returns 200 (rerun the
  diagnostic's crawl once Task 6 has also landed, since it unblocks more panels).
- An exception in any calculated-attribute chart or explanation view, `ask_delete_object` or the
  other decorated fragment views shows the exception modal.

**Depends on:** none (Task 6 only widens the set of panels the acceptance crawl reaches).

**Implementation:** easy — one template include and a set of decorators, cause verified.

## Task 10 — Calculated-attribute explanation ids are scoped per item, not per attribute name

**Goal:** In panels that render several objects' calculated attributes (edge computer with CPU, RAM
and storage; servers with storage; edge appliance; external API), every formula button opens its
own object's explanation. Today the collapse id is built from the attribute name only, so the
Factory-sensor panel has `collapse-calculated_attributes-carbon_footprint_manufacturing` three times
and each Boavizta cloud server panel twice: HTMX swaps a RAM explanation into the CPU row, Bootstrap
toggles every match, and `click once` then makes the RAM explanation unreachable until reopen.
Build every per-item id and reference from `item.web_id` (already attribute + dict key + container,
and already used by the dict toggle and `ancestors-formula-and-children-*`).

**Diagnostic:** [`diagnostics/calculated-attribute-collapse-id-collision.md`](diagnostics/calculated-attribute-collapse-id-collision.md)

**Repository:** `e-footprint-interface`

**Files touched** (all under `model_builder/templates/model_builder/side_panels/edit/`):
- `calculated_attributes/explainable_object_template.html` — collapse id (around line 29), input id
  and label `for` (around 3, 15).
- `calculated_attributes/components/get_calculated_attribute_explanation_button.html` —
  `hx-target`, `data-bs-target`, `aria-controls` (around 8, 14, 16).
- `calculated_attributes/eco_logits_explainable_quantity.html` — same three references (around 7,
  13, 15) and input id (around 23).
- `calculated_attributes/explainable_quantity.html` — input id (around 6).
- Optional: `calculated_attributes_section.html` — constant `aria-controls` (around 7).
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_calculated_attributes.py::test_edit_panel_explanation_buttons_target_their_own_row`
  — reproduction; remove its expected-failure marker. No other tests.
- E2E selector updates to `^=` prefixes (the ids change): `tests/e2e/test_calculus_graph.py:59`,
  `tests/e2e/objects/test_external_api_objects.py:70,74`,
  `tests/e2e/objects/test_video_external_api_objects.py:147,149`; run those three files.

**Acceptance:**
- The reproduction passes with its marker removed.
- No duplicate ids in any shipped example's panels (rerun the diagnostic's sweep after Task 6, which
  unblocks the component and storage panels).
- In the Factory-sensor panel, each CPU/RAM/storage formula button opens only its own explanation,
  and each stays reachable.

**Depends on:** Task 9 (shared new test file; also gives Task 9's empty dict entries distinct ids).

**Implementation:** easy — template id changes plus E2E selector updates.

## Task 11 — Deletion confirmation blocks every remaining reference

**Status:** complete (Run A).

**Goal:** Deletion confirmation blocks a journey while any pattern holds it, naming every holding
pattern; the user detaches it first with the membership ×. A custom edge-device component
referenced by a recurrent component need is blocked, naming the need. Today every list/dict
container is a removal target, so `check_can_delete` skips independent references whenever any
such container exists. Only containers that nest their child
(`renders_relationship_children_as_nested_cards`) count as removal targets. Remove the redundant
sole-member check and block references outside those removal targets. Copy fixes remain deferred
with smell-sweep S12. Folds in S7's redundant `mirrored_cards` override cleanup.

Review decision 2026-11-03: test the normal check → execute flow. Blocked cases test the check
without forcing execution; allowed cases assert permission before deletion and verify saved state.
Leave `_delete` and its existing cascade cleanup unchanged unless an allowed-deletion regression
reveals a defect. The shared deletion tail and execution-without-confirmation requirement are dropped.
Task 3's OOB-delete rule is unchanged.

**Diagnostic:** [`diagnostics/list-deletion-only-unlinks.md`](diagnostics/list-deletion-only-unlinks.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/application/use_cases/delete_object.py` — nesting-only removal targets (around
  lines 61–73); delete the sole-member block (around 92–103); block references outside the removal
  targets (around 105–118). Leave `_delete` unchanged.
- `model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py` — remove the
  redundant `mirrored_cards` override (around 42–45); reword comments (around 47–60).
- `specs/architecture/forms-and-relationships.html` (around 168–181) — journeys are blocked while any
  pattern holds them, naming every pattern; a container that does not nest its child is a reference,
  not a removal target; `required_non_empty_relationships` now only guards last-member removal in
  widgets and membership sections.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/unit_tests/application/use_cases/test_delete_object.py::TestDeleteObjectUseCase::test_check_can_delete_blocks_referenced_objects_naming_every_holder`
  — four blocked-confirmation cases; assert refusal, every blocking name, and unchanged request-local
  and saved state. Remove the expected-failure marker when the fix lands. Do not execute refused deletions.
- `test_detached_journey_passes_check_and_deletes_with_unshared_children` — ordinary and edge
  journeys: detach from the pattern while keeping another journey, reload, assert permission, execute,
  and verify the journey and its unshared steps/functions are absent from saved state. Other journeys survive.
- `test_component_without_need_passes_check_and_deletes_from_device` — a custom component held
  only by its device passes the check and is removed from both the saved model and device membership
  by the existing cascade cleanup.
- Existing E2E unused-journey deletions (`test_usage_journeys.py::test_delete_usage_journey`, `test_full_journey.py:143-165`)
  and the deletion suites keep passing.

**Acceptance:**
- The reproduction passes with its marker removed.
- A journey or edge journey held by any pattern shows the blocking modal naming every holding
  pattern, never "Yes, delete"; after the membership × removes it from all patterns, it deletes
  with its unshared steps or functions.
- A need-referenced custom component is blocked naming the need; without the need it deletes.
- On the four shipped examples, nothing survives a confirmed delete (Default-laptop and
  Factory-sensor CPU/RAM become blocked).
- Pattern, job, step, edge function, need, server and edge-group deletions behave as before.

**Depends on:** Task 8 (hard: internal-parent confirmation and execution guards must precede
Task 11's generic removal-target handling); Tasks 3, 4, 6 (soft; shared `delete_object.py`,
`test_views_deletion.py`, `test_delete_object.py`, `CHANGELOG.md`).

**Implementation:** standard — confirmation rules on a full review surface; verify allowed deletions before
considering any execution-path change.

## Task 12 — Put the system prefix first in every card id

**Goal:** Every card id has one consistent shape: `sys-{system}-Class-id`, optionally followed
by `_in_<unprefixed parent containment path>`. A job nested in a step and journey becomes
`sys-system-Job-job_in_UsageJourneyStep-step_in_UsageJourney-journey-1`. Every appearance of an
object therefore starts with its canonical id, and the existing `cardButtonsForWebId` matcher
finds its root and mirrored cards without parsing system prefixes or locating a canvas.
Creating/editing an editable nested object pulses its cards and scrolls the first into view;
opening a mirrored object's edit panel marks its mirrors as opened. Root cards retain their ids,
and the other model's cards remain untouched even when object ids are identical. Task 6's
inspection-only panels keep their existing behavior.

Review decision 2026-11-03: build an unprefixed containment path in Python, then add
`_system_web_id_prefix` once at the beginning of `web_id`. This replaces the earlier owner-canvas
lookup/prefix-stripping proposal. Keep the existing document-wide exact-or-`_in_` highlight
matcher and the single canonical id in headers (the nginx limit fixed by `0b2f361b`).

**Diagnostic:** [`diagnostics/card-highlight-id-mismatch.md`](diagnostics/card-highlight-id-mismatch.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` — a private
  unprefixed containment-path helper; `web_id` adds the system prefix to the completed path.
  Update the root-only prefix comments. Preserve `route_id`, equality/hash semantics and mirror enumeration.
- `tests/e2e/pages/model_builder_page.py` — adapt `card_id_selector` to the uniform system-prefixed
  shape, matching the card's own class rather than a class embedded in its parent path. Audit
  remaining literal selectors and ID construction in templates, leader lines, HTMX and E2E helpers;
  most derive from `web_id` and need no manual rewrite. Update any actual format assumptions found.
- `specs/architecture/workspace.html` — document the prefix at the beginning of every completed
  containment path; remove the root-only/inherited-through-parent description.
- `specs/architecture/rendering.html` — document single-id headers and the exact-or-`_in_`
  expansion, with the system namespace already present in every matching card's prefix.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/unit_tests/domain/entities/web_abstract_modeling_classes/test_modeling_object_web.py` —
  update list/dict nested-ID expectations; extend the existing ID tests to cover multiple nesting
  levels, exactly one leading system prefix, unchanged root ids, and distinct system namespaces.
- `js_tests/model_builder_main.test.js › pulse and opened highlights cover every card of the object on its own canvas only`
  — switch the reproduction from `test.failing` to `test` and regenerate its Python-rendered fixture
  with `npm run jest`. Keep the nested job, mirrored step, `job-2` boundary, root, unknown-system
  and parked-model cases. Expected mirrors come from Python, not copied old ID strings.
- Update existing format-sensitive E2E assertions and run the job, journey-step, edge-object and
  model-comparison flows, checking card targeting, leader lines and HTMX swaps. Manually verify
  off-screen nested create/edit scrolling; jsdom does not provide real element geometry.

**Acceptance:**
- A nested id starts with its object's canonical id followed by `_in_`; the system prefix appears
  exactly once at the beginning, including at multiple nesting levels and for list/dict containers.
- The reproduction passes as a plain `test`; all mirrors on the owning model are highlighted and
  no sibling object or other model's card is highlighted.
- Existing exact-or-`_in_` JS matching and single-id header payloads stay unchanged; no canvas lookup,
  prefix stripping, additional transport field or legacy-ID compatibility branch is introduced.
- Root IDs, routing, card targeting, leader lines, model switching and Task 3's server-side removal
  remain correct. Architecture documentation describes the new ID invariant.

**Depends on:** no hard prerequisite. Keep Run B ordering after Run A, then before Tasks 13/14:
Tasks 6, 12, 13 and 14 share `modeling_object_web.py`. Task 3's deletion behavior must remain covered.

**Implementation:** standard — one ID-construction rule, selector audit and existing-test updates;
validate Python ID tests, `npm run jest`, non-E2E checks and affected E2E flows.

## Task 13 — One web-class resolver and a `has_edit_panel` property (refactor)

**Goal:** One rule maps a library class to its web class: exact name, else the nearest mapped MRO
ancestor, else `ModelingObjectWeb`. `wrap_efootprint_object`, form generation and the use cases
use it (use cases read `type(web_obj)` instead of re-looking up `MAPPING`). Today three lookups
disagree on 10 concrete classes: the underlying resolver disagreement affects `RecurrentEdgeProcess{CPU,RAM,Storage}Need` and
`RecurrentEdgeWorkloadNeed`. Task 6 bypasses form generation for their inspection panels but does
not remove that disagreement. A `has_edit_panel` wrapper property derived from the
resolver replaces the hard-coded class-name lists in the calculated-attribute templates (S11).
Panel-link availability includes Task 6's read-only inspection panels despite the property name.
Behavior-preserving except that those four need classes now use one wrapper everywhere.

**Diagnostic:** [`smell-sweep.md`](smell-sweep.md) — findings S4 and S11.

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/domain/efootprint_to_web_mapping.py` (around lines 84–111) — single resolver.
- `model_builder/application/use_cases/delete_object.py` (around 87, 175) and
  `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` (around 235,
  270, 554) — use the resolver or `type(web_obj)`; `has_edit_panel` property.
- `model_builder/templates/model_builder/side_panels/edit/calculated_attributes/components/ancestor_or_child_list_element.html`
  (around 4), `…/components/ancestors_formula_and_children.html` (around 39),
  `…/calculated_attributes/calculated_attribute_chart.html` and `recurrent_attribute_chart.html`
  (around 7–14) — use `has_edit_panel`.

**Tests added/changed:**
- A unit test pinning that, for every concrete library modeling class, the wrapping and form
  resolutions agree.
- View checks that the four recurrent process/workload need panels remain read-only, open correctly
  and retain formulas/charts under Task 6's contract; do not reintroduce standalone edits.

**Acceptance:**
- No two paths resolve a library class to different web classes; no rendered link points at a
  class without an edit panel.
- Full non-E2E suite and edge E2E files pass unchanged.

**Depends on:** Task 8 (and therefore Task 6; Task 4 remains soft ordering).

**Implementation:** standard — cross-cutting resolver swap with one deliberate behavior change to
verify.

## Task 14 — Calculated-attribute template dispatch by `template_kind` (refactor)

**Goal:** Calculated-attribute templates choose their partial from one `template_kind` property on
`ExplainableObjectWeb`, resolved by `isinstance` (quantity / eco_logits / hourly / recurrent / empty
/ default), instead of exact concrete class names (`class_as_snake_str` includes and hand-written
`if/elif` lists). One `wrap_explainable()` factory replaces the six duplicated wrapper choices (S10). Near-preserving: it
also adds the missing "(see graph)" link for input-timeseries ancestors (e.g. ai_chatbot
`utc_hourly_occurrences`), and a library subclass no longer raises `TemplateDoesNotExist`. The
domain must not reverse URLs. Settled 2026-10-21 (plan decision 2): S8's URL template tag is dropped;
the four dict/non-dict URL branches stay.

**Diagnostic:** [`smell-sweep.md`](smell-sweep.md) — findings S6 and S10 (S8 dropped).

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/domain/entities/web_abstract_modeling_classes/object_linked_to_modeling_obj_web.py`
  (around 70–72) and `explainable_objects_web.py` (around 33, 56, 67, 97) — `template_kind`,
  `wrap_explainable()`.
- `model_builder/domain/entities/web_core/explainable_timeseries_utils.py` (around 38–40) and
  `modeling_object_web.py` (around 79–86) — use `wrap_explainable()`.
- Templates under `model_builder/templates/model_builder/side_panels/edit/`:
  `calculated_attributes_section.html` (around 15), `calculated_attributes/explainable_object_dict.html`
  (as changed by Task 9), `calculated_attributes/components/ancestor_or_child_list_element.html`
  (around 16–46).

**Tests added/changed:**
- Unit: `template_kind` for each explainable subclass, including the nine without a template today.
- View: the ai_chatbot `utc_hourly_occurrences` explanation lists its input with "(see graph)", and
  the link returns 200.
- Tasks 9 and 10 view tests keep passing.

**Acceptance:**
- Every calculated value and ancestor renders with the partial matching its kind; input-timeseries
  ancestors are chartable from explanations.
- No concrete class-name comparison remains in the calculated-attribute templates.

**Depends on:** Task 10 (and therefore Task 9).

**Implementation:** standard — several templates and wrappers move to one dispatch.

## Task 15 — Example-wide invariant tests (test-only refactor)

**Goal:** Parametrized integration tests over the shipped introductory examples lock in three
invariants that most bugs in this batch broke: (i) every rendered `open-edit-object-panel` and
`get_*` fragment link returns 200; (ii) no edit panel contains duplicate `id`s; (iii) every delete
offered by `ask-delete-object` removes the object from the saved model. Add synthetic cases for
Task 11's shapes (shared journeys, referenced custom edge-device components). Task 9/10 one-panel
regressions may fold into these. `specs/testing.md` gains one line making the shipped examples an
explicit exception to the programmatic-fixtures rule (precedent:
`tests/integration/test_intro_examples_load_and_compute.py`).

**Diagnostic:** [`smell-sweep.md`](smell-sweep.md) — finding S3 (scratch sweeps to start from:
`scratchpad/hourly/test_hourly_sweep.py`, `scratchpad/silentdel/test_sweep.py`,
`scratchpad/smell/test_link_sweep.py` under `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/`;
they are temporary and may be gone, so rebuild from the diagnostics if needed).

**Repository:** `e-footprint-interface`

**Files touched:**
- `tests/integration/` — new invariant test module(s) over `INTRO_EXAMPLES`.
- `specs/testing.md` (around 140–142) — the examples exception.

**Tests added/changed:**
- The three invariant families above; the link crawl takes about 8 s over 632 fragments.

**Acceptance:**
- All three invariants pass on every introductory example once Tasks 1–14 have shipped.
- The suite runtime increase stays within about 10–20 s.

**Depends on:** Tasks 4, 6, 8, 9, 10, 11 (run last).

**Implementation:** standard — test-only, but needs crawl and delete harnesses that stay fast and
deterministic.

## Task 16 — Group-member deletion confirmation recognizes hook-managed memberships

**Status:** planned (Run B); not implemented and not a prerequisite for merging Run A.

**Goal:** A grouped custom edge device or otherwise unreferenced subgroup passes the normal
deletion confirmation, then deletes through the existing hook with its parent memberships removed.
Independent references still block confirmation and name their holders. Preserve Task 8's early
internal-parent guards and Task 11's reference checks.

**Diagnostic:** [`diagnostics/grouped-member-delete-confirmation-blocked.md`](diagnostics/grouped-member-delete-confirmation-blocked.md).
Confirmed on both the Task 11 baseline and its reviewed implementation; Run A did not introduce it.

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/application/use_cases/delete_object.py` — distinguish hook-managed parent-group
  memberships from blocking references during confirmation. Keep those memberships out of generic
  execution removal targets so the existing hook does not unlink them twice.
- `model_builder/domain/entities/web_core/hardware/edge/edge_group_member_mixin.py` — existing
  `handles_own_dict_memberships` / `pre_delete` contract; adjust only if needed to identify actual
  group memberships. Do not exempt every dict reference to a group member.
- `tests/unit_tests/application/use_cases/test_delete_object.py` and
  `tests/unit_tests/adapters/views/test_views_deletion.py` — focused normal-flow regressions.
- `specs/architecture/forms-and-relationships.html` — document confirmation of hook-owned memberships.
- `CHANGELOG.md` — consolidated `## [Unreleased]` fix entry when implemented.

**Tests added/changed (planned; not yet committed):**
- Grouped custom device and empty subgroup: confirm permission, execute, reload, and verify the
  object and its parent-dictionary entries are absent while siblings survive.
- Grouped custom device also referenced by a recurrent need: confirmation refuses, names the
  independent holder, and leaves request-local and saved state unchanged. Do not execute refusal.
- Confirmation view: grouped device/subgroup offers “Yes, delete”; independently referenced device
  does not. Reuse programmatic fixtures and existing edge-group deletion suites.
- Keep Run A's internal-object guards, holder-blocking regressions and allowed-deletion cases passing.

**Acceptance:**
- Hook-managed parent-group membership alone does not block confirmation.
- Unrelated references remain blockers; the exemption is relationship-specific.
- The normal check → execute → reload path removes the object and memberships exactly once.
- Existing execution hooks and cascades stay unchanged unless an allowed-deletion regression
  demonstrates a defect. No library, migration or saved-JSON change.

**Depends on:** completed Tasks 8 and 11. Run B ordering after Task 12 is soft for changed card IDs;
land before Task 13's resolver refactor in the same use case.

**Implementation:** standard — confirmation permission must distinguish hook-owned membership
from independent references without changing execution ownership. FULL review surface.

## Execution plan

Runs, ordering, deduplication verdicts and deferred items: [`plan.html#execution-plan`](plan.html#execution-plan).
