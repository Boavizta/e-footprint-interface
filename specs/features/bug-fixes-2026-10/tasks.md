# bug-fixes-2026-10 — tasks

**Status:** intake only. Three reports were parked during the `request-lifecycle-simplification`
runs (see its `tasks.md`, "Gates and prerequisites"). They ride along the next `bug-fixes` session,
which will diagnose them with the other reports collected by then: one `diagnostics/<bug-slug>.md`
per report, then the tasks below get their final form and ordering. Nothing here has been
implemented.

Evidence below was gathered at review time on `dev` at `2eced3c0` (2026-10-20); re-check anchors
before relying on them.

## Reports awaiting diagnosis

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

## Execution plan

<!-- Tasks appended during diagnosis; final ordering pass pending. -->
