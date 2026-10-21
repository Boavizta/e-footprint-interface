# Nested and mirrored cards get no pulse, scroll or "opened" highlight: the client expands the canonical id by a prefix that the `sys-` system prefix broke

- **Status:** CONFIRMED
- **Confidence:** high. The id shapes come from Python probes over the introductory examples. A Playwright run against
  the local server shows the pulse on a root card and none on a nested or mirrored card. Git history dates both halves
  of the regression.
- **Reported:** smell sweep S2. Commit `cc9611c3` broke the client's id prefix match, so nested create and edit get no
  pulse or scroll-into-view, mirrored cards lose the "opened" highlight, and no test covers it. The hypothesis holds.
  The proposed fix (scope matching to a canvas and add a Jest test with real ids) is right in direction. This diagnostic
  picks which canvas to scope to and where the unprefixed id comes from.

## Root cause

Two commits, twelve days apart, made incompatible assumptions:

1. `0b2f361b` (2026-06-04, nginx 502 fix) stopped sending one id per mirror in HTMX headers. It now sends only the
   object's canonical `web_id` and expands it on the client.
   `theme/static/scripts/model_builder_main.js:205-208` (`cardButtonsForWebId`) matches
   `[id="button-<webId>"], [id^="button-<webId>_in_"]`. That match assumes a nested id begins with the canonical id.
2. `cc9611c3` (2026-06-16, model comparison) prefixed only the **root** branch of `web_id` with `sys-{system id}-`
   (`model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:151-160`, `:163-172`). The
   nested branch is `Class-id_in_<parent web_id>`. It carries the prefix only at its root ancestor, at the end.

The senders always pass the root-wrapped object's canonical id. `get_web_object_from_efootprint_id` /
`wrap_efootprint_object` build it without a container:
`model_builder/application/use_cases/create_object.py:182`, `model_builder/application/use_cases/edit_object.py:116`.
That id then reaches `model_builder/adapters/presenters/htmx_presenter.py:97,129,158,186,208` and
`model_builder/adapters/views/views_edition.py:44`. As a result, for every nested object:

| Shape | Example (ai_chatbot / synthetic mirrored edge function) |
|---|---|
| canonical id sent | `sys-AI-chatbot-system-Job-Serve-chat-interface` |
| nested card button | `button-Job-Serve-chat-interface_in_UsageJourneyStep-Open-the-assistant_in_sys-AI-chatbot-system-UsageJourney-Chatbot-conversation` |
| root card button (works) | `button-sys-AI-chatbot-system-UsagePattern-Daily-conversations` |
| mirrored, sent on open | `sys-uuid-system-1-EdgeFunction-01a6be14-fab` |
| its two card buttons | `button-EdgeFunction-01a6be14-fab_in_sys-uuid-system-1-EdgeUsageJourney-c3c1213f-1f2`, `…_in_sys-uuid-system-1-EdgeUsageJourney-05c97392-b52` |

A probe over all introductory examples (`scratchpad/smell/s2_ids.py`) gives the same shapes for `Job`, the EcoLogits
jobs, `UsageJourneyStep`, `EdgeFunction`, `RecurrentEdgeProcess`, `RecurrentServerNeed` and the edge components. The
match fails for every one of them. Root cards still match exactly.

**Browser (local server, `scratchpad/s2/browser_probe.py`):**
- Root `UsagePattern` edit: the toast id is canonical and the root button pulses.
- Nested `Job` edit: the toast id is `sys-AI-chatbot-system-Job-Serve-chat-interface`, and no element gets
  `border-pulse-after-add-edit-object`.
- Mirrored `EdgeFunction` (one function in two journeys): opening sends
  `highlightOpenedObjects: "sys-uuid-system-1-EdgeFunction-01a6be14-fab"`. Only the clicked mirror has
  `model-builder-card-opened`, set by the card's own hyperscript, not by the trigger. The other mirror stays plain. The
  following edit pulses neither mirror.

The scroll-into-view (`model_builder_main.js:239-247`) keys on the first match, so it is dead for nested objects too.
This matters most for nested creation, where the new card may be off-screen.

**Two-model workspace.** Each resident canvas is `<div data-model-canvas="{slot}" data-system-id="{system id}">`
(`model_builder/templates/model_builder/model_builder_main.html:13`). The parked one has `d-none`
(`theme/static/scripts/model_comparison.js:178-181`). Slot system ids are distinct, but `add_slot` /
`distinctify_against_siblings` preserve **every object id** (`specs/architecture/workspace.html`, "Distinct-system-id
invariant"). A duplicated model's nested cards therefore differ from the active model's only in the `_in_sys-<other>-…`
tail. Any unscoped `[id^="button-Class-id_in_"]` matcher would also hit the parked canvas. Its hidden buttons could come
first in document order and take the scroll target (their rect is zero), and they would keep a stray "opened" class
until the next `removeAllOpenedObjectsHighlights()` (`model_builder_main.js:181-187`, document-wide).

**Why exact ids from the server are not an option.** The server does know every mirror (`mirrored_cards`), but that list
is what `0b2f361b` removed. It overflowed nginx's `proxy_buffer_size` and returned 502 for heavily mirrored objects. The
payload must stay constant-size.

**Coverage.** No Jest or E2E test references `cardButtonsForWebId`, `highlightOpenedObjects`, `model-builder-card-opened`
or `border-pulse-after-add-edit-object`. The two toast tests in `js_tests/model_builder_main.test.js:211-237` send no
`id`. `js_tests/model_comparison.test.js` (added by `cc9611c3`) does not cover highlighting.

## Reproduction

- `js_tests/model_builder_main.test.js › pulse and opened highlights cover every card of the object on its own canvas
  only` — Jest `test.failing`, on the fixture `card_highlight_two_canvases` rendered by
  `js_tests/build_fixtures.py` (`render_card_highlight_canvases`); fails on `dev@624b9e44`. The fixture renders the
  real `model_builder_main.html` for a two-slot `InMemoryWorkspaceRepository`: slot 0 (system `system`, active) and
  the same data added as slot 1 (fresh system id from `add_slot`, same object ids, parked). Step `step` sits in
  journeys `journey 1` and `journey 2`, and holds job `job` and its prefix-sharing sibling `job-2`. Python embeds,
  for each case, the canonical `web_id`, the expected `button-` ids (`mirrored_cards`) and the parked canvas's buttons
  for the same object. The test dispatches `displayToastAndHighlightObjects` and `highlightOpenedObjects` with each
  canonical id and compares the document-wide pulsed and opened sets.
- Assertion (trimmed, `expect(received).toEqual(expected)`): for `nested job` and `mirrored step`, `pulsed` and `opened`
  are expected to be the two `button-Job-job_in_UsageJourneyStep-step_in_sys-system-UsageJourney-journey-{1,2}` (and
  the two `button-UsageJourneyStep-step_in_sys-system-UsageJourney-journey-{1,2}`), received `[]`. `root journey`
  (`button-sys-system-UsageJourney-journey-1`), `unknown system` (`[]`) and every `parked` list match.
- Watch:
  - `obj_to_edit.web_id` at `model_builder/adapters/views/views_edition.py:44` (also `output.web_id` at
    `model_builder/adapters/presenters/htmx_presenter.py:208`, from `web_id=edited_obj.web_id` at
    `model_builder/application/use_cases/edit_object.py:116`) → `sys-system-Job-job` (fixture `canonical`, same
    `get_web_object_from_efootprint_id(...).web_id`).
  - nested `web_id` at
    `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:159` → card button
    `button-Job-job_in_UsageJourneyStep-step_in_sys-system-UsageJourney-journey-1` (and `…-journey-2`); the parked
    copy ends `_in_sys-<fresh id>-UsageJourney-journey-1`.
  - `` `[id="${base}"], [id^="${base}_in_"]` `` at `theme/static/scripts/model_builder_main.js:207` →
    `[id="button-sys-system-Job-job"], [id^="button-sys-system-Job-job_in_"]`.
  - match count of that query at `theme/static/scripts/model_builder_main.js:207` (consumed at `:213` and `:239`) →
    `0` for `sys-system-Job-job` and `sys-system-UsageJourneyStep-step`, `1` for
    `sys-system-UsageJourney-journey-1`.
- Debug: break in `cardButtonsForWebId` at `theme/static/scripts/model_builder_main.js:207`, or at
  `js_tests/model_builder_main.test.js:258` after both dispatches. Unmasked run: temporarily change `test.failing(` to
  `test(` and run `npx jest js_tests/model_builder_main.test.js -t "own canvas only"` (it then fails with the diff above;
  `npm run jest -- …` also rebuilds the fixture first). With the marker in place the same command reports the test as
  passing because it fails.
- Discrimination: against a scratch `model_builder_main.js` with the settled owner-canvas fix the unmasked test passes
  and the marked test reports "Failing test passed even though it was supposed to fail"; an unscoped
  `[id^="button-<local>_in_"]` variant still fails: it pulses and marks opened the parked canvas's two step and two job buttons.

## Fix approach

Fix only the client expansion and scope it to the canvas that owns the id. The server payload stays as it is: one
canonical id.

`cardButtonsForWebId(webId)` finds the resident canvas whose `sys-${dataset.systemId}-` prefixes `webId`. If more than
one matches, it takes the longest system id. It strips that prefix to get the unscoped `Class-id`. Inside that canvas
only, it returns `[id="button-${webId}"], [id^="button-${localId}_in_"]`. If no canvas matches, it returns an empty
list. Both listeners (`highlightOpenedObjects`, `displayToastAndHighlightObjects`) keep calling it unchanged. Update the
stale comment at `model_builder_main.js:200-204` and the matching one at `views_edition.py:38-40`.

Why this rule is safe:
- The `_in_` delimiter bounds `localId`. Ids `job` and `job-2` give `button-Job-job_in_` and `button-Job-job-2_in_`,
  which never match each other. A false match needs an efootprint id that itself contains `_in_`. Production ids are
  `uuid4()[:12]` (hex and dashes, `e-footprint/efootprint/abstract_modeling_classes/modeling_object.py:289`). Only
  name-as-id mode (examples, tests) could carry `_in_`, and none does.
- Scoping by owning system rather than by visibility is exact. It does not depend on which canvas is shown, and the
  parked canvas can never match.
- The header stays constant-size, so the 502 cannot come back.

Rejected alternatives:
- **Server sends every mirror's exact DOM id.** This is the pre-`0b2f361b` design and it causes the nginx 502.
- **Server also sends an unprefixed `local_web_id`, client scopes to the visible canvas.** This keeps the
  `sys-` format out of JS. But it needs a new `ModelingObjectWeb` property, new fields on `CreateObjectOutput` and
  `EditObjectOutput` (which tests build positionally), five presenter sites, `views_edition.py`, and a JS rule for the
  active canvas. That is a larger diff in `htmx_presenter.py`, which Task 3 also edits, and it adds no correctness: the
  Jest fixture below, rendered from Python, already pins Python and JS to the same id rule. It is acceptable if the
  reviewer prefers Python to own the stem.
- **Unscoped prefix `[id^="button-Class-id_in_"]` (the sweep's first suggestion, unscoped form).** This matches the
  parked canvas when slots share object ids.
- **Suffix or substring match on `-Class-id`.** This false-matches any object whose id ends in `…-Class-id`.
- **Prefixing nested ids with `sys-` as well.** This rewrites every derived id, selector, leaderline anchor and the E2E
  `card_id_selector` for a highlight-only bug.

## Files to touch

- `theme/static/scripts/model_builder_main.js` — `cardButtonsForWebId` (`:200-208`): owner-canvas lookup through
  `[data-model-canvas][data-system-id]`, prefix stripping, scoped query, and a corrected comment.
- `model_builder/adapters/views/views_edition.py` — comment only (`:38-40`): the client expands the id within its owning
  canvas. The code is unchanged.
- `js_tests/model_builder_main.test.js` — remove the `test.failing` marker and its task comment from the reproduction.
- `specs/architecture/rendering.html` — one line beside "Toast notifications and tooltips" (`:26`): the toast or opened
  highlight carries one canonical `web_id`, and `cardButtonsForWebId` expands it to the owning canvas's root and
  `_in_` mirrors. Constant-size header (nginx).
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

## Tests

- The reproduction above is the task's only test change: `js_tests/model_builder_main.test.js › pulse and opened
  highlights cover every card of the object on its own canvas only`, with its fixture `card_highlight_two_canvases`
  case in `js_tests/build_fixtures.py` (the generated HTML is gitignored and rebuilt by `npm run jest`). The fix removes the `test.failing` marker and
  the `bug-fixes-2026-10 Task 12` comment; no other tests are added. Scroll-into-view is not asserted (jsdom gives
  every element a zero rect), and the E2E mirroring assertion once suggested here is dropped.

## Acceptance criteria

- Creating or editing a nested object (job, step, edge function, recurrent need or process, edge component) pulses
  every one of its cards on the active canvas, and scrolls the first into view when it is off-screen.
- Opening the edit panel of a mirrored object marks every mirror on the active canvas as opened.
- Root cards behave as before.
- In a two-model workspace (including a duplicated model with identical object ids), no card on the parked canvas
  is pulsed or marked opened.
- The highlight headers stay one canonical id (constant size).

## Risks and side effects

- Scroll-into-view now fires for nested creates and edits that silently skipped it since 2026-06-16. This is intended,
  but users will notice it again.
- The JS now encodes the `sys-{system id}-` format next to `button-` / `_in_`. The Python-rendered Jest fixture is the
  guard that keeps the two sides agreeing. If `_system_web_id_prefix` changes, this test must fail.
- A canonical id whose system matches no canvas (stale response after a model switch) highlights nothing. That is the
  correct no-op.

## Flags

- `model_builder_main.js` is not on the file lists of Tasks 1 to 3. Tasks 1 and 2 edit `side_panel_utils.js`, not this
  file. Task 3 edits `htmx_presenter.py` (`present_deleted_object` and `present_delete_confirmation`). This fix leaves
  the presenter untouched (delete toasts carry no `id`), so there is no shared product file. It shares `CHANGELOG.md`
  with every task, and `js_tests/build_fixtures.py` with any task that adds fixtures. Ordering is free.
- The fix is client-only, with no serialization or migration impact and no library dependency.
- Validation needs `npm run jest`. Its `build:js-test-fixtures` step renders the fixture through Django.
- Constitution §1.4: the server still decides what to highlight (one canonical id). The client only maps that id to
  DOM nodes, which the nginx header limit requires.

## Decisions

- 2026-10-21: keep the constant-size single-id payload and fix the expansion on the client, scoped to the owning
  canvas by `data-system-id`. The `local_web_id` variant (the server sends the unprefixed stem) was rejected as a larger
  cross-layer diff for no extra correctness. It remains acceptable if the reviewer prefers Python to own the stem.
