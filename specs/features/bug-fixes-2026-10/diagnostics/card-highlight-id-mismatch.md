# Nested and mirrored cards get no pulse, scroll or "opened" highlight: the client expands the canonical id by a prefix that the `sys-` system prefix broke

- **Status:** CONFIRMED
- **Confidence:** high. The id shapes come from Python probes over the introductory examples. A Playwright run against
  the local server shows the pulse on a root card and none on a nested or mirrored card. Git history dates both halves
  of the regression.
- **Reported:** smell sweep S2. Commit `cc9611c3` broke the client's id prefix match, so nested create and edit get no
  pulse or scroll-into-view, mirrored cards lose the "opened" highlight, and no test covers it. The hypothesis holds.
  The original proposal scoped matching to a canvas. Review on 2026-11-03 instead chose a consistent Python ID
  format: add the system namespace before the completed unprefixed containment path, preserving the existing matcher.

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
- Historical discrimination (earlier proposal): against a scratch `model_builder_main.js` with an owner-canvas fix the unmasked test passes
  and the marked test reports "Failing test passed even though it was supposed to fail"; an unscoped
  `[id^="button-<local>_in_"]` variant still fails: it pulses and marks opened the parked canvas's two step and two job buttons.

## Fix approach

Review decision 2026-11-03: normalize card IDs in Python. Construct the complete unprefixed containment path,
then prepend `_system_web_id_prefix` once. Every appearance of an object starts with its canonical ID:

```text
canonical: sys-system-Job-job
nested:    sys-system-Job-job_in_UsageJourneyStep-step_in_UsageJourney-journey-1
mirror:    sys-system-Job-job_in_UsageJourneyStep-step_in_UsageJourney-journey-2
```

Illustrative implementation in `ModelingObjectWeb`:

```python
@property
def _containment_path(self):
    path = f"{self.class_as_simple_str}-{self._modeling_obj.id}"
    if self.parent_container is not None:
        path += f"_in_{self.parent_container._containment_path}"
    return path

@property
def web_id(self):
    return f"{self._system_web_id_prefix}{self._containment_path}"
```

Keep `cardButtonsForWebId` unchanged: document-wide matching of `button-<canonical>` and
`button-<canonical>_in_…` now works for root, nested and mirrored cards. No canvas lookup, system-prefix parsing,
extra header field or old-ID compatibility branch is needed. The header still carries one canonical ID.

Why this rule is safe:
- The system namespace leads every card ID, so duplicated models with the same object IDs remain distinct.
- The `_in_` delimiter bounds the object's canonical ID: `job` cannot match `job-2`. As before, production IDs
  use hex and dashes; the shipped name-as-ID examples do not contain `_in_` in object IDs.
- Root IDs stay unchanged. Nested IDs change once at their shared construction point; derived button, collapse,
  icon, leader-line and HTMX IDs generally follow `web_id` automatically. Audit explicit format assumptions rather
  than assuming every selector needs a rewrite.
- `route_id` and library identities do not change. Preserve mirror enumeration and equality/hash behavior:
  appearances in different parents remain distinct, and equal object IDs in different systems remain distinct.

Alternatives considered:
- **Owner-canvas lookup and prefix stripping in JS (earlier proposal, superseded).** Smaller immediate patch,
  but retains two ID shapes and teaches the client to parse the system namespace. The consistent Python rule is
  preferred for overall simplicity; the additional selector/test audit is accepted.
- **Server sends every mirror's exact DOM ID.** Reintroduces the nginx header overflow fixed by `0b2f361b`.
- **Server sends an extra unprefixed stem.** Adds cross-layer payload plumbing without needing it once ID
  construction is consistent.
- **Unscoped `button-Class-id_in_` or substring matching.** Loses system isolation or matches parent identities.

## Files to touch

- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` — private unprefixed
  containment-path helper, prefix-at-front `web_id`, updated comments. Keep routing and mirror logic unchanged.
- `tests/unit_tests/domain/entities/web_abstract_modeling_classes/test_modeling_object_web.py` — update nested
  list/dict ID expectations and extend the existing ID tests for multiple levels, one leading namespace,
  unchanged root IDs and distinct systems.
- `tests/e2e/pages/model_builder_page.py` — adapt `card_id_selector` to identify the card's own class under the
  uniform prefix without matching a class appearing only in the parent path. Audit other literal selectors,
  derived-ID construction, leader lines and HTMX targeting; update actual format assumptions found.
- `js_tests/model_builder_main.test.js` — remove the reproduction's `test.failing` marker and task comment.
  Regenerate `card_highlight_two_canvases` through `js_tests/build_fixtures.py` using `npm run jest`.
- `specs/architecture/workspace.html` — replace root-only prefix inheritance with one leading system namespace
  on the completed containment path.
- `specs/architecture/rendering.html` — one canonical ID in headers, expanded by exact-or-`_in_` matching;
  every card starts with its system namespace.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

## Tests

- Update/extend the existing Python ID tests for root, list, dict and multiple nesting levels. Check exactly one
  leading system prefix and isolation across systems. Run the wrapper test module.
- Keep the Python-rendered Jest reproduction: nested job, mirrored step, prefix-sharing `job-2`, root journey,
  unknown system and parked-model cases. Turn it into a plain `test` after implementation and run `npm run jest`
  to rebuild the real fixture. Do not copy old nested ID strings into expectations or modify the client matcher.
- Run non-E2E checks and affected existing E2E job, journey-step, edge-object and model-comparison flows after
  updating selectors. Check card targeting, leader-line endpoints, HTMX swaps and Task 3's deletion behavior.
- Verify off-screen nested create/edit scrolling in the browser. The Jest reproduction cannot assert actual
  scrolling because jsdom supplies no real geometry.
- Earlier scratch discrimination above validated the superseded JS patch only. The new Python design still needs
  implementation-time validation; no passing prototype result is claimed for it.

## Acceptance criteria

- Every nested ID starts with its canonical ID plus `_in_`, with exactly one system namespace at the beginning.
- Creating or editing an editable nested object pulses its cards and scrolls the first into view when off-screen.
  Opening a mirrored object's edit panel marks its mirrors as opened. Task 6's inspection-only panels keep their behavior.
- Root IDs and behavior remain unchanged. Other models' cards and prefix-sharing sibling objects are untouched.
- Single-ID highlight headers and the existing document-wide exact-or-`_in_` matcher remain unchanged.
- Card selectors, leader lines, HTMX targets, model switching and server-side removal still work with the new IDs.
- Workspace/rendering documentation describes the new invariant; no compatibility shim is introduced.

## Risks and side effects

- Nested DOM IDs change. Most derived IDs inherit the change, but explicit selectors and ID expectations must be
  audited, especially `card_id_selector`, which currently treats nested cards differently from roots.
- Scroll-into-view resumes for nested creates and edits that silently skipped it since 2026-06-16.
- The Python-rendered Jest fixture connects the Python ID rule to the unchanged client prefix matcher and checks
  isolation when two models share object IDs. Root/list/dict/deep Python tests pin the construction invariant.
- No serialization, migration, library dependency or transport schema change is needed; these are DOM identities.

## Flags

- Run B remains after Run A and before Tasks 13/14. Task 12 now shares `modeling_object_web.py` with Tasks 6, 13
  and 14. It keeps Task 6's read-only panel behavior and Task 3's server-side deletion mechanism.
- Validation includes Python ID tests, `npm run jest`, non-E2E checks and affected E2E flows. This is broader than
  the earlier client-only patch because the shared nested ID rule changes.
- Constitution §1.4: the server still decides what to highlight through one canonical ID; the browser maps it
  to root and mirrored cards with its existing selector.

## Decisions

- 2026-11-03, user review: build the unprefixed containment path first and add `sys-{system}-` at the beginning
  of every completed card ID. Preserve the existing JS matcher and constant-size header. This supersedes the
  2026-10-21 owner-canvas/prefix-stripping proposal; accept the selector audit and Python/E2E test updates in return
  for one consistent ID rule.
