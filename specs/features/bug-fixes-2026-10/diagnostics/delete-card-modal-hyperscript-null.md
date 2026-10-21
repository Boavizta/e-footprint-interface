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

**What the response removes** (`present_deleted_object`, `htmx_presenter.py:301-342`):

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
`htmx_presenter.py:336-342` is therefore unreachable in production. Only the synthetic presenter
unit test, with `oob_regions=[]`, reaches it (`tests/unit_tests/adapters/presenters/test_htmx_presenter.py:47-57`).

**A second, unverified weakness.** `specs/conventions.md:35` documents that hyperscript wires
handlers on swapped content asynchronously after `htmx:load`. The "Yes, delete" button arrives in a
swapped modal. A click inside that window would delete server-side but skip the only remover on the
load-bearing path. The fix removes that window. It was not reproduced.

## Fix approach

Make the server the sole owner of card removal and delete the client remover:

1. `DeleteObjectOutput` (`model_builder/application/use_cases/delete_object.py:35`) gains `web_id`,
   matching `CreateObjectOutput` and `EditObjectOutput`. The normal-deletion branch fills it from
   `web_obj.web_id` before `self_delete()` (`:226`), while the system prefix is still resolvable.
   The presenter cannot compute it after deletion, and rebuilding the `sys-…` format in the adapter
   would duplicate the domain chokepoint.
2. In `present_deleted_object`, replace the `if output.oob_regions:` branch and the dead `HX-Reswap`
   branch (`:331-342`) with one `_build_oob_response`. For a non-list deletion that is not
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
  to `DeleteObjectOutput` (`:35`). Set it in the normal-deletion return (`:231-235`) from `web_obj.web_id`,
  captured before `self_delete()` (`:226`).
- `e-footprint-interface/model_builder/adapters/presenters/htmx_presenter.py`: in `present_deleted_object`
  (`:331-342`), prepend the OOB delete for non-list, non-`canvas_oob` deletions and drop the
  unreachable `HX-Reswap` branch. In `present_delete_confirmation`, drop `remove_card_with_hyperscript`
  (`:381`, `:402`).
- `e-footprint-interface/model_builder/templates/model_builder/modals/delete_card_modal.html`: remove the
  `script=` attribute (`:9-10`).
- `e-footprint-interface/tests/unit_tests/adapters/presenters/test_htmx_presenter.py`: replace the
  `HX-Reswap == "none"` assertion (`:57`) and add the branch cases below.
- `e-footprint-interface/specs/architecture/rendering.html`: one line next to "Mutation entry points"
  (`:37`) saying that the server owns card removal on delete (OOB `delete` for an uncovered top-level
  card) and that no client-side remover exists.
- `e-footprint-interface/CHANGELOG.md`: an `## [Unreleased]` fix entry (constitution §6). Card
  deletion no longer logs a console error, and top-level cards are removed by the server response.

## Tests
- **Presenter unit** (`tests/unit_tests/adapters/presenters/test_htmx_presenter.py`):
  - a non-list output with `web_id` and `[OobRegion("results_buttons")]` gives a body that contains
    exactly one `hx-swap-oob="delete"` element with that id, placed before the results-button regions;
  - the same output plus `OobRegion("model_canvas")` gives no delete element;
  - a non-list output with `edge_device_lists` gives the delete element before
    `#edge-device-groups-list`;
  - a `was_list_deletion=True` output gives no delete element.
- **View** (`tests/unit_tests/adapters/views/test_views_deletion.py`, Django client plus session, like
  the existing test):
  - the `ask-delete-object` modal body contains no `script=` and no `remove #`, both for a
    non-mirrored and for a mirrored object;
  - loading `model_builder/domain/reference_data/modeling_examples/introductory/iot_industrial.json`
    and POSTing delete for the `UsagePattern` (a no-flip top-level deletion in the probe) gives a body
    with `id="sys-…-UsagePattern-<id>" hx-swap-oob="delete"`, and no `model-canva` target;
  - deleting a `Job` gives no delete element and still contains its top-parent journey card swap.

  This shares the iot loader with #151's regression in the same file.
- **Integration** (`tests/integration/test_deletion.py`): `DeleteObjectUseCase.execute` on an unused
  top-level object returns `output.web_id` equal to the pre-deletion card id.
- **E2E**: in `tests/e2e/objects/test_usage_journeys.py::test_delete_usage_journey` (the load-bearing
  path) and the job deletion in `tests/e2e/objects/test_jobs.py` (around `:150-156`, the nested
  "never in DOM" path), capture `console` errors and `pageerror` the way
  `tests/e2e/test_model_comparison.py:201-203` does, and assert none were raised. The card must
  still disappear. The existing
  `test_model_comparison.py::test_delayed_object_deletion_keeps_native_buttons_and_count_controls_independent[True]`
  and `test_full_journey.py:143-165` already cover card removal for an unused journey (including on
  the prefixed comparison canvas) and must keep passing. They are the regression gate that a
  hyperscript-only removal would fail.

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
