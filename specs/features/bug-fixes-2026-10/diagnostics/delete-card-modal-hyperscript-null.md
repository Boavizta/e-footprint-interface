# Delete-card hyperscript logs "is null": a client-side remover whose selector is wrong for nested cards and redundant after canvas re-renders, yet still the only remover for plain top-level deletions

- **Status:** CONFIRMED
- **Confidence:** high. Code trace on `dev` at `7f78a329`, plus a scratch probe that drove the real
  `ask-delete-object` and `delete-object` views over the minimal fixture, three introductory examples,
  an edge-group fixture and a mirrored-step fixture. For each deletion it compared the modal's
  `remove #…` selector and the response's OOB targets against the rendered canvas ids. The probe
  lives at `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/test_probe_delete_hyperscript.py`
  (output `probe_results.txt` beside it). It was not run in a browser.
- **Reported:** request-lifecycle Task 3 review (intake report 3). After a card deletion, hyperscript
  logs an "is null" error. The intake said the response has already removed the card when
  `remove #<web_id>` runs on `htmx:afterRequest`, and proposed a server-emitted OOB delete in place of
  the hyperscript and its `remove_card_with_hyperscript` flag. **The symptom holds, but the
  hypothesis holds only in part.** The hyperscript is not dead. For nested child cards the selector
  never matched anything, because it uses the root-form id while nested cards carry `…_in_<parent>`
  ids. For top-level cards whose deletion re-renders the canvas or the edge lists, the response
  removes the card first. For a plain top-level deletion with no constraint flip (an unused journey,
  a second usage pattern, an ungrouped edge device, a job-less server or API, an edge usage pattern),
  the response leaves the card alone and the hyperscript is the **only** thing that removes it.
  Simply dropping it would leave stale cards. The fix the intake proposed (server OOB delete) is
  right, and it is required rather than optional cleanup.

## Root cause

**Selector.** The confirmation modal gets `web_obj` from
`model_builder/adapters/views/views_deletion.py:18` (`get_web_object_from_efootprint_id`). That call
wraps the object without a container (`model_builder/domain/entities/web_core/model_web.py:288-290`,
then `model_builder/domain/efootprint_to_web_mapping.py:84-89`), so
`web_id` always takes the root form `sys-<system>-<Class>-<id>`
(`model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:158-160`). A nested
card renders `<Class>-<id>_in_<parent web_id>` (same lines, `parent_container` branch). The modal emits
`remove #{{ obj.web_id }}` when the flag is set
(`model_builder/templates/model_builder/modals/delete_card_modal.html:9-10`). The presenter sets the
flag to `True` (`model_builder/adapters/presenters/htmx_presenter.py:381`) and clears it only for
mirrored objects (`:401-402`), meaning objects with more than one card
(`model_builder/application/use_cases/delete_object.py:127`).

**What the response removes** (`present_deleted_object`, `htmx_presenter.py:301-343`):

| Deletion kind | Response branch | Card removed by response? | Hyperscript |
|---|---|---|---|
| Child in a list/dict container (job, step, edge function, need), not mirrored | `:318-329`: OOB `outerHTML` of each container's top-parent card (`_render_top_parent_cards`, `:267`), or the canvas `innerHTML` when a constraint flips | yes | `remove #sys-…` never matches → **"is null"** |
| Child, mirrored | same | yes | flag cleared, no script |
| Top-level object, deletion flips a creation constraint (last server, last journey, last UP, …) | `:331-335` with a `model_canvas` region | yes (canvas `innerHTML`) | target already gone → **"is null"** |
| Root `EdgeDeviceGroup` | `:331-335` with `edge_device_lists` (`edge_device_group_web.py:55-59`) | yes (list `outerHTML`) | target already gone → **"is null"** |
| Top-level object, no flip (unused UJ, extra UP, `EdgeUsagePattern`, ungrouped `EdgeDevice`, job-less server or external API) | `:331-335` with only `results_buttons` (plus maybe `edge_modeling_toggle`) | **no** | **load-bearing**: it is the only remover |

The probe confirmed every row. Examples: `Job` and `UsageJourneyStep` in all examples are
`NULL(selector never in DOM)`. Minimal `UsagePattern`, `Server` and `UsageJourney` are
`NULL(response removed it)` via `model-canva-0`. Root groups Alpha and Beta are
`NULL(response removed it)` via `edge-device-groups-list`. iot `UsagePattern`, iot
`EdgeUsagePattern`, the "UJ two" unused journey, the ungrouped "Lone sensor", the ai_chatbot server
and "Small LLM API" are all `LOAD-BEARING`. In every case the response plus the hyperscript left no
stale card. Grouped edge devices and sub-groups are blocked by the confirmation (cant-delete
modal), so they never reach this path.

**Ordering.** htmx 2.0.6 (`theme/static/scripts/external_librairies/htmx.min.js`) runs the response
handler, which swaps the OOB elements in document order, *before* it fires `htmx:afterRequest`
(`xhr.onload`: `M(r,H)` then `ae(r,"htmx:afterRequest",H)`). `defaultSettleDelay: 0`
(`theme/templates/base.html:14`) makes settle synchronous too. So by the time the hyperscript runs,
the canvas, top-parent and edge-list swaps are already in place. `hx-swap="none"` suppresses only
the main swap; OOB swaps still apply.

**Error text.** Hyperscript 0.9.12 (`_hyperscript.min.js`, `version:"0.9.12"`) gives `remove <expr>`
the op `t.nullCheck(r,a)`, which throws `new Error("'" + sourceFor() + "' is null")`. The console
shows `'#sys-…-<Class>-<id>' is null`. `#id` resolves through
`runtime.getRootNode(me).getElementById`, which falls back to `document` when the button is
detached. So the `hx-on::after-request` `dropModal` (registered first, because htmx wires `hx-on`
before hyperscript's `htmx:load` pass) does not change the outcome. The handler has no `from`, so
hyperscript's detached-owner guard (`n!==e&&!e.isConnected`) does not skip it either.

**Dead branch.** `delete_side_effects` always returns at least `results_buttons`
(`modeling_object_web.py:328`, `:354-356`). The trailing `HX-Reswap: none` branch at
`htmx_presenter.py:337-343` is therefore unreachable in production. Only the synthetic presenter
unit test, with `oob_regions=[]`, reaches it (`tests/unit_tests/adapters/presenters/test_htmx_presenter.py:47-59`).

**A second, unverified weakness.** `specs/conventions.md:35` documents that hyperscript wires
handlers on swapped content asynchronously after `htmx:load`. The "Yes, delete" button arrives in a
swapped modal. A click inside that window would delete server-side but skip the only remover on the
load-bearing path. The fix removes that window. It was not reproduced.

## Reproduction

- `e-footprint-interface/tests/e2e/objects/test_jobs.py::TestJobs::test_deleting_nested_and_top_level_cards_logs_no_console_error`
  — E2E (Playwright against the dev server); fails on `dev@624b9e44`. It is a sibling of
  `test_link_existing_job_to_step` reusing `model_with_two_steps_one_job`. It deletes the nested "Test Job" (the
  selector-never-matches row), then creates and deletes "Unused Journey" (the load-bearing no-flip row), checks that
  each card leaves the canvas, and asserts that no `console` error or `pageerror` was collected. E2E is the cheapest
  layer: the defect is the browser evaluating the modal's hyperscript after htmx's swaps, and a view test could only
  assert the fix's response shape. The journey half passes on `dev`. It is the guard that a hyperscript-only removal
  would fail. When the marker goes, the test stays as the deletion console guard beside
  `test_link_existing_job_to_step`.
- Assertion (trimmed), at `test_jobs.py:188`:
  ```
  AssertionError: assert ["'#sys-0c45ec1c-df3-VideoStreamingJob-c1d0680d-276' is null",
                          'hypertrace /// ', '  -> on htmx:afterRequest   - JSHandle@node'] == []
  ```
  Only the job deletion logs. The journey deletion logs nothing and its card is removed, by the hyperscript.
- Watch (values from a scratch Playwright probe over the same fixture against the same server; ids vary per run):
  - Rendered `script` attribute of "Yes, delete", the output of `remove #{{ obj.web_id }}` at
    `e-footprint-interface/model_builder/templates/model_builder/modals/delete_card_modal.html:9-10`, gated by
    `"remove_card_with_hyperscript": True` at
    `e-footprint-interface/model_builder/adapters/presenters/htmx_presenter.py:381` (not mirrored, so `:401-402` does not
    clear it) → job: `on htmx:afterRequest remove #sys-14671dba-efe-VideoStreamingJob-5c6e8e63-e08`; journey:
    `… remove #sys-14671dba-efe-UsageJourney-7186e2e8-f84`.
  - `document.getElementById('sys-14671dba-efe-VideoStreamingJob-5c6e8e63-e08')` in the browser before the click
    → `null`. The rendered job card is `VideoStreamingJob-5c6e8e63-e08_in_UsageJourneyStep-b5d229f0-732_in_sys-14671dba-efe-UsageJourney-20ee3d49-47e`
    (`e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:158-160`).
    For the journey, the same lookup → the card element.
  - OOB elements in the `delete-object` response, from `present_deleted_object` at
    `e-footprint-interface/model_builder/adapters/presenters/htmx_presenter.py:318-329` (job, a list deletion) and
    `:331-335` (journey) → job: `outerHTML:#sys-14671dba-efe-UsageJourney-20ee3d49-47e` (the top-parent journey card),
    then `#btn-open-panel-result`, `#show-results-toolbar-btn`, `#workspace-storage-status`; journey: only those three
    results/status regions, nothing that touches its card. In both cases, `HX-Reswap` is absent. The `:337-343` branch
    was not reached.
  - `document.getElementById(<selector id>) !== null`, sampled by a capture-phase `htmx:afterRequest` listener on the
    button, which fires just before the hyperscript handler → job: `false` (the hyperscript throws `'#…' is null`);
    journey: `true` (the hyperscript removes it, and it is `false` by the bubbled event on `#modal-container`).
- Debug recipe: run `poetry run pytest --runxfail "tests/e2e/objects/test_jobs.py::TestJobs::test_deleting_nested_and_top_level_cards_logs_no_console_error" --base-url http://localhost:8000 --headed`
  and break on `test_jobs.py:178`, after the job deletion's act at `:177`. `console_errors` already holds the three
  lines. Break on `:186` for the journey half.
- Discrimination: the settled fix was applied to a scratch copy served on port 8013 (`web_id` on `DeleteObjectOutput`,
  the OOB delete first unless `canvas_oob`, with the modal `script=`, the flag and the `HX-Reswap` branch removed).
  The test passed under `--runxfail` and reported XPASS(strict) without it. A "drop the hyperscript only" variant
  (no OOB delete) failed at `test_jobs.py:186`: the "Unused Journey" card stayed visible. The prototype was not
  committed.

## Fix approach

Make the server the sole owner of card removal and delete the client remover:

1. `DeleteObjectOutput` (`model_builder/application/use_cases/delete_object.py:35`) gains `web_id`,
   matching `CreateObjectOutput` and `EditObjectOutput`. The normal-deletion branch fills it from
   `web_obj.web_id` before `self_delete()` (`:226`), while the system prefix is still resolvable.
   The presenter cannot compute it after deletion, and rebuilding the `sys-…` format in the adapter
   would duplicate the domain chokepoint.
2. In `present_deleted_object`, replace the `if output.oob_regions:` branch and the dead `HX-Reswap`
   branch (`:331-343`) with one `_build_oob_response`. For a non-list deletion that is not
   `canvas_oob`, its HTML **starts with** `<div id="{output.web_id}" hx-swap-oob="delete"></div>`,
   followed by `render_oob_regions(...)`. Emitting it first lets the `EdgeDeviceGroup` case stay
   order-safe: the delete lands, then `#edge-device-groups-list` is replaced. Skipping it under
   `canvas_oob` avoids an `htmx:oobErrorNoTarget` on a target the canvas swap already covers (the
   failure class of report 2). The id-attribute form lets htmx `CSS.escape` the id. htmx 2.0.6
   supports the `delete` OOB style (`case"delete":je(n)`).
3. Remove the `script=` attribute from `delete_card_modal.html:9-10`, and remove
   `remove_card_with_hyperscript` from `htmx_presenter.py:381` and `:402`. The mirrored branch keeps
   its message text.

**Rejected:**
- *Drop the hyperscript only.* This regresses the load-bearing row: stale cards for unused journeys,
  extra usage patterns and ungrouped edge devices.
- *Fix the selector by emitting every `mirrored_cards` web_id.* The client would still own removal,
  the wiring window would remain, and it would still null on canvas and edge-list re-renders.
- *Emit the OOB delete unconditionally, last.* It would log `oobErrorNoTarget` whenever the canvas
  or edge lists already removed the card.
- *Always re-render the canvas on delete.* Heavier responses for no gain, against the mission's
  eco-design priorities.

## Files to touch
- `e-footprint-interface/model_builder/application/use_cases/delete_object.py`: add `web_id: str = ""`
  to `DeleteObjectOutput` (`:35`). Set it in the normal-deletion return (`:230-235`) from `web_obj.web_id`,
  captured before `self_delete()` (`:226`).
- `e-footprint-interface/model_builder/adapters/presenters/htmx_presenter.py`: in `present_deleted_object`
  (`:331-343`), prepend the OOB delete for non-list, non-`canvas_oob` deletions and drop the
  unreachable `HX-Reswap` branch. In `present_delete_confirmation`, drop `remove_card_with_hyperscript`
  (`:381`, `:402`).
- `e-footprint-interface/model_builder/templates/model_builder/modals/delete_card_modal.html`: remove the
  `script=` attribute (`:9-10`).
- `e-footprint-interface/tests/e2e/objects/test_jobs.py`: remove the strict-xfail marker from
  `test_deleting_nested_and_top_level_cards_logs_no_console_error`.
- `e-footprint-interface/tests/unit_tests/adapters/presenters/test_htmx_presenter.py`: required edit to an existing
  test (see Tests).
- `e-footprint-interface/specs/architecture/rendering.html`: one line next to "Mutation entry points"
  (`:37`) saying that the server owns card removal on delete (OOB `delete` for an uncovered top-level
  card) and that no client-side remover exists.
- `e-footprint-interface/CHANGELOG.md`: an `## [Unreleased]` fix entry (constitution §6). Card
  deletion no longer logs a console error, and top-level cards are removed by the server response.

## Tests
- The reproduction is this task's only test:
  `tests/e2e/objects/test_jobs.py::TestJobs::test_deleting_nested_and_top_level_cards_logs_no_console_error`.
  Remove its strict-xfail marker. No new presenter, view or integration tests.
- Required edit to an existing test that asserts the removed branch:
  `tests/unit_tests/adapters/presenters/test_htmx_presenter.py::test_successful_crud_presentations_append_one_metadata_status_oob`
  asserts `responses[-1]["HX-Reswap"] == "none"` (`:59`) for a `DeleteObjectOutput` with no `oob_regions`. Drop that
  assertion, and give the `deleted` output a `web_id` (e.g. `"Server-deleted"`) so the OOB delete it now emits has a
  real id. Its one-storage-status-OOB check stays. No other test asserts the modal's `script=` or
  `remove_card_with_hyperscript`. The other `HX-Reswap` assertions under `tests/unit_tests/` are for non-delete
  responses and do not change.
- These must keep passing:
  `tests/e2e/test_model_comparison.py::test_delayed_object_deletion_keeps_native_buttons_and_count_controls_independent[True]`,
  `tests/e2e/test_full_journey.py` (`:143-165`), `tests/e2e/objects/test_usage_journeys.py::test_delete_usage_journey`
  and `test_jobs.py::test_link_existing_job_to_step`. Together they cover unused-journey removal on the prefixed
  comparison canvas as well.

## Acceptance criteria
- Deleting any card (top-level, nested, mirrored, constraint-flipping, root edge group) logs no
  hyperscript `is null` error and no `htmx:oobErrorNoTarget`.
- After deleting an unused usage journey, a non-last usage pattern, an ungrouped edge device or a
  job-less server or API, the card disappears from the active canvas without a reload. The parked
  comparison canvas is untouched.
- The delete confirmation modal carries no hyperscript, and the presenter context has no
  `remove_card_with_hyperscript`.

## Risks and side effects
- The OOB delete assumes that a non-list deletion's root-form `web_id` is rendered. The probe found
  this true for every deletable top-level kind. Grouped edge devices and sub-groups (the nested
  non-list kinds) are blocked at confirmation. If a future kind breaks this, the cost is an
  `oobErrorNoTarget` log, not data loss.
- Card removal moves from after-settle (the hyperscript ran on `afterRequest`) into the swap. Leader
  lines are rebuilt 100 ms after `resetLeaderLines`
  (`theme/static/scripts/leaderline_utils.js:298-305`), and `updateLines` skips detached endpoints
  (`:72-82`), so lines are unaffected. Lines now see the final DOM earlier, if anything.
- Removing the `HX-Reswap: none` branch moves the delete toast from `HX-Trigger` to
  `HX-Trigger-After-Settle`, the same as every other mutation response. It is still shown.
- The modal keeps `hx-target="#modal-container"`, `hx-swap="none"` and `hx-on::after-request`
  (`rendering.html:37`), so the settlement-event invariant still holds.

## Flags
- **Overlap with #151** (`recurrent-need-delete-render-error.md`): no product file in common. #151
  edits `modeling_object_web.py` (container property); this task edits `delete_object.py`,
  `htmx_presenter.py` and `delete_card_modal.html`. They share `tests/unit_tests/adapters/views/test_views_deletion.py`
  (both add iot-example view tests, so a loader helper can be shared) and `CHANGELOG.md`. Either
  order works. Running #151 first is slightly preferable, because its fix makes recurrent-need
  deletions reach this presenter, and the E2E "no console error" assertions can then cover them.
- **Shared invariant with report 2** (`membership-section-oob-no-target.md`): never emit an OOB element
  whose target may be absent. The emission rule above respects it.
- HTMX/OOB state transition: a FULL review surface under `.agents/repository.md`.
- No migration or serialization impact, and the library is not involved.
- The browser console behavior is checked only by E2E (needs a local server). The probe covered the
  server side only.

## Decisions
- None needed from the user. 2026-10-21: chose the server-emitted OOB delete over dropping the
  hyperscript, because the hyperscript is the only remover on the no-flip top-level path.
