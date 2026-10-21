# bug-fixes-2026-10 — tasks

**Status:** diagnosed and planned 2026-10-21; nothing implemented. Each task links its diagnostic;
[`plan.html`](plan.html) digests them and orders the runs. Run them in order, each in a fresh
`feature-implement` session.

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
Tasks 13–15 are user-approved smell-sweep refactors.

## Task 1 — The #sidePanel unsaved-changes guard blocks instead of replaying

**Goal:** With unsaved side-panel edits, clicking an element whose own `hx-target` is `#sidePanel`
shows the unsaved-changes modal; "Discard changes" discards the edits and closes the panel, and
nothing is issued. The user repeats the click, which then runs exactly as authored. This removes
the hand-parsed replay (and its `eval`) and fixes a visible defect: the boosted "Data & privacy"
links have no `hx-get`, so the replay loaded the builder page into `#sidePanel` (shown in jsdom
with the bundled htmx 2.0.6; confirm in a browser via the new E2E). Applies the mission's
guards-block rule (`specs/mission.md:26-28`). Settled 2026-10-21: scope is this guard only; the
navigation guard and `runAfterSidePanelDiscardConfirmation` stay for
`server-rendered-state-follow-up`. The shared `#unsavedModal` copy names only the discard, so it
stays true for the guards that still continue: "The open side panel has unsaved changes. Discard
them?" with "Keep editing" / "Discard changes".

**Diagnostic:** [`diagnostics/side-panel-replay-hand-parsing.md`](diagnostics/side-panel-replay-hand-parsing.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `theme/static/scripts/side_panel_utils.js` — remove `pendingRequest`, the `htmx:beforeRequest`
  guard (around lines 127–139, with its `hideLoadingBar` timeout) and `proceedWithPendingRequest()`
  (around 199–220); add an own-`hx-target="#sidePanel"` branch to the `htmx:confirm` listener (around
  162–171) wired to `closeWarningModalAndCloseSidePanel()`, never calling `issueRequest`; rewrite the
  guard comment. Match on the element's own attribute, not `detail.target`, so `htmx.ajax` openers
  with their own confirmation don't stack two dialogs.
- `model_builder/templates/model_builder/modals/warn_before_side_panel_closing_modal.html` — Cancel
  calls `closeWarningModal()` (no `hideLoadingBar`); button labels.
- `model_builder/templates/model_builder/model_builder_main.html` (around line 84) — modal message.
- `specs/design/journeys/build-a-model.html` (around 358) and `specs/design/journeys/compare-models.html`
  (around 638) — quoted strings; build-a-model says discard closes the panel and the user repeats
  the click.
- `specs/architecture/workspace.html` (around 41–43) — the same `htmx:confirm` listener blocks
  `#sidePanel` elements; drop the "older beforeRequest guard" sentence.
- `specs/features/server-rendered-state-follow-up/kickoff.md` (line 40) — narrow the row to the
  navigation guard and `runAfterSidePanelDiscardConfirmation`.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `js_tests/side_panel_switch_guard.test.js` — `#sidePanel` branch: modified, unmodified, other
  element, Discard issues nothing, an event matching both branches shows the modal once.
- `tests/e2e/test_forms.py::test_pending_request_preserves_hx_vals` — rewrite: Discard closes the
  panel, the next click sends the request with its `hx-vals` and button lock.
- E2E — dirty panel plus Help → Data & privacy: modal, Discard, repeat click opens Data & privacy
  correctly; assert the new message and labels once.

**Acceptance:**
- No path re-issues an interrupted `#sidePanel` request; the `#sidePanel` guard path contains no `eval`,
  `pendingRequest` or `htmx:beforeRequest` listener. The Save-path `eval` in
  `setRecomputationToTrueIfResultPaneIsOpen` stays (out of scope; plan decision 1, 2026-10-21).
- Dirty panel + Data & privacy never loads the builder page into the side panel.
- The navigation guard and Simplified-inputs entry keep their current behavior under the new copy.

**Depends on:** none.

**Implementation:** easy — deletions plus one listener branch; behavior and copy are settled.

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
- `js_tests/fixtures/inline_count_autosave.html` — regenerate via `js_tests/build_fixtures.py`.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- Unit (dict mutation views): region absent without the flag, present with it.
- E2E: console-error assertion (collector pattern from `test_model_comparison.py:201-203`) on canvas
  inline count and group-entry count/✕; new case — child panel open, canvas count edit → panel count
  synced, no console error.
- Jest for the helper if `side_panel_utils.js` has Jest coverage.

**Acceptance:**
- No `htmx:oobErrorNoTarget` on any listed path, with or without a panel open, in one- and
  two-model workspaces.
- With the child's edit panel open, a canvas count edit still updates the panel's count.

**Depends on:** none.

**Implementation:** easy — known cause, one helper, one server condition; tests are specified.

## Task 3 — The server owns card removal on delete; drop the delete-modal hyperscript

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
- `tests/unit_tests/adapters/presenters/test_htmx_presenter.py` — replace the `HX-Reswap == "none"`
  assertion; OOB delete present (and first) for results-only and `edge_device_lists` outputs, absent
  with `model_canvas` and for list deletions.
- `tests/unit_tests/adapters/views/test_views_deletion.py` — modal has no `script=`/`remove #`
  (mirrored and not); iot example: `UsagePattern` delete emits the OOB delete, `Job` delete does not.
  Shares the iot loader with Task 4.
- `tests/integration/test_deletion.py` — `output.web_id` equals the pre-deletion card id.
- E2E `tests/e2e/objects/test_usage_journeys.py::test_delete_usage_journey` and the job deletion in
  `tests/e2e/objects/test_jobs.py` — no console errors (collector from
  `test_model_comparison.py:201-203`), card still disappears. Existing comparison and full-journey
  deletion E2E tests must keep passing.

**Acceptance:**
- Deleting any card (top-level, nested, mirrored, constraint-flipping, root edge group) logs no
  console error.
- Top-level no-flip deletions remove the card from the active canvas only; a parked comparison
  canvas is untouched.

**Depends on:** Task 4 (soft: no shared product file, but shipping Task 4 first lets the new
no-console-error checks cover recurrent-need deletion). Shares `test_views_deletion.py` and
`CHANGELOG.md` with Task 4.

**Implementation:** standard — small diff, but an HTMX/OOB transition (full review surface).

## Task 4 — Deleting a recurrent need: ignore detached contextual containers when rendering cards

**Goal:** Deleting a `RecurrentServerNeed` or any recurrent edge need (e.g. `RecurrentEdgeProcess`)
re-renders the parent edge usage journey card without the deleted need, with no error modal.
`ModelingObjectWeb.efootprint_contextual_modeling_obj_containers` skips the library's detached
contextual wrappers (`modeling_obj_container is None`), as every library reader already does. Fixes
GitHub #151, and the latent same-crash after an `edge_device` relink.

**Diagnostic:** [`diagnostics/recurrent-need-delete-render-error.md`](diagnostics/recurrent-need-delete-render-error.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` — filter
  detached entries in `efootprint_contextual_modeling_obj_containers` (around lines 378–380).
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_deletion.py::test_recurrent_need_deletion_rerenders_its_edge_usage_journey_card`
  — reproduction; remove its expected-failure marker. No other tests.

**Acceptance:**
- The reproduction passes with its marker removed.
- Deleting a recurrent server or edge need on the Industrial IoT example shows no error modal; the
  canvas immediately matches what a reload shows.
- Deletion of jobs, steps, usage patterns and edge components is unchanged.

**Depends on:** none. Once shipped, nested-child deletions surface Task 3's hyperscript "is null"
console error (previously masked by the crash).

**Implementation:** easy — one-line filter with a verified cause; regression test shape is given.

## Task 5 — Round daily chart emissions to significant figures so totals match the library

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

## Task 6 — Edit panels for objects held by library-built relationships open instead of erroring

**Goal:** Opening the edit panel of an `EdgeStorage`, a recurrent edge process/workload component
need, or an EcoLogits external API server (reachable from calculated-attribute chart headers and
ancestor lists) renders the panel with no error modal, and its Delete shows the "referenced by
<owner>" blocking modal. Two interface-side `KeyError`s cause it: (1)
`list_containers_and_attr_name_in_list_container` indexes the container's constructor signature
with relationship attributes the library builds in `after_init` (`ExternalAPI.server`,
`EdgeComputer.components`, `recurrent_edge_component_needs`); use `.get(attr_name)` and skip
missing ones, the library's own idiom; (2) `get_corresponding_web_class` lacks an
`ExternalAPIServer` entry. Settled 2026-10-21: both parts ship in this task. Found while
diagnosing #151.

**Diagnostic:** [`diagnostics/check-can-delete-keyerror.md`](diagnostics/check-can-delete-keyerror.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` —
  `.get(attr_name)` and skip `None` in `list_containers_and_attr_name_in_list_container` (around lines
  389–390), on top of Task 4's filter at 378–380.
- `model_builder/domain/efootprint_to_web_mapping.py` — `"ExternalAPIServer": ModelingObjectWeb`
  (around lines 52–54).
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_edition.py::TestViewsEdition::test_library_built_child_panel_opens_and_delete_is_blocked_by_its_owner`
  — reproduction; remove its expected-failure marker. No other tests.
- `tests/unit_tests/domain/test_web_efootprint_wrappers.py::test_make_sure_that_all_canonical_classes_are_mapped` — drop the
  stale `"ExternalAPIServer"` exclusion.

**Acceptance:**
- The reproduction passes with its marker removed.
- Those panels open from their calculated-attribute links on the shipped examples; Delete shows the
  blocking modal naming the owner and leaves the model unchanged.
- Jobs, needs, edge devices, CPU/RAM components and usage patterns behave as before.

**Depends on:** Task 4 (adjacent lines of the same property). Task 8 must follow in the same run:
with Task 6 alone, an `EdgeStorage` edit from its newly openable panel saves but swaps a card id
not on the canvas, so the edge computer card is not refreshed (Task 8's reproduction covers it).

**Implementation:** easy — two one-line changes with verified causes.

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
  move the unit box styling (lines 19-24) to a wrapper that holds the existing readonly input (borderless,
  `name`/`id`/`value` unchanged) and a `span` "each hour". Widen it from `w-25` if needed. New helper text
  (lines 28-30).
- `CHANGELOG.md`: `## [Unreleased]` fix entry referencing #150.

**Tests added/changed:**
- `tests/e2e/objects/test_edge_objects.py` (near line 411): "each hour" is visible beside the unit; the
  input value is still `cpu_core`; after switching to a storage component the value updates and "each
  hour" stays.
- A form-rendering unit or integration test of the constant template: new helper text, and no
  `…__constant_unit` field value contains "each hour".

**Acceptance:**
- Server-need, edge-process and component-need constant editors show `<unit> each hour` in one visual
  box, plus the new helper text.
- Posted units, saved models and results are unchanged.

**Depends on:** none.

**Implementation:** easy — one template and copy change; decisions settled.

## Task 8 — Library-built edge components are blocked from deletion instead of a silent no-op

**Goal:** Deleting an edge computer's CPU or RAM component, or an edge appliance's component, shows
the "referenced by <device>" blocking modal and leaves the model unchanged. Today it offers "Yes,
delete" and returns 200, but nothing is deleted: their web overrides declare the library-built
`components` list a removal target, and the edit silently drops that non-constructor attribute. The
library treats these components as internal (built in `after_init`, deleted only with their
device). Component edits keep re-rendering the owning device card through one `mirrored_cards`
override on `EdgeComponentWeb`; the three internal web classes subclass it and lose their
list-container overrides. This also places `EdgeStorage` edits (newly reachable after Task 6) under
the edge computer card. Settled 2026-10-21: the blocking modal, with its existing copy as for
Task 6, not hiding Delete.

**Diagnostic:** [`diagnostics/edge-component-delete-silent-noop.md`](diagnostics/edge-component-delete-silent-noop.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/domain/entities/web_core/hardware/edge/edge_component_base_web.py` —
  `mirrored_cards` override placing the component under `edge_device.mirrored_cards`, with a
  one-line docstring.
- `model_builder/domain/entities/web_builders/hardware/edge/edge_computer_cpu_component.py`,
  `edge_computer_ram_component.py`, `edge_appliance_component.py` — subclass `EdgeComponentWeb`;
  delete the `list_containers_and_attr_name_in_list_container` overrides; drop the unused `typing`
  import in the appliance file.
- `specs/architecture/forms-and-relationships.html` (or wherever `mirrored_cards`/list containers
  are described) — one line: library-built relationships are never removal targets; edge
  components are placed under their device's cards via `EdgeComponentWeb.mirrored_cards`.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_views_deletion.py::test_library_built_edge_component_deletion_is_blocked_and_edits_rerender_its_device`
  — reproduction; remove its expected-failure marker. No other tests.
- Delete `test_list_containers_and_attr_name_in_list_container` from
  `tests/unit_tests/domain/entities/web_builders/hardware/edge/test_edge_computer_cpu_component_web.py`,
  `test_edge_computer_ram_component_web.py` and `test_edge_appliance_component_web.py` (they test the deleted overrides);
  keep their calculated-attribute filter tests.
- Existing `tests/integration/test_deletion.py` device-cascade tests and the custom-edge-device component E2E
  (`tests/e2e/objects/test_edge_objects.py`, around line 334) must keep passing.

**Acceptance:**
- The reproduction passes with its marker removed.
- Delete on a CPU, RAM or appliance component shows the blocking modal naming its device; the model
  is unchanged.
- Renaming a CPU, RAM or appliance component, or an edge storage, re-renders the owning device card
  with no error modal.
- Deleting an edge computer or appliance still deletes its components; custom edge device
  components stay deletable and render as before.

**Depends on:** Task 6 (hard: without its `.get` skip, removing the overrides raises
`KeyError 'components'` on panel open). Ship in the same run, right after Task 6.

**Implementation:** easy — one override plus three base-class swaps, probe-verified.

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
- New `tests/unit_tests/adapters/views/test_views_calculated_attributes.py`:
  - iot `Factory-sensor` panel: no hourly chart URL for `Sensor-local-storage` empty entries, their
    explanation URL present, CPU/RAM hourly chart URLs still present;
  - every hourly chart URL rendered in that panel returns 200;
  - decorator: a forced exception returns 500, `HX-Reswap: none`, modal markup and
    `openModalDialog` trigger (conventions of `test_exception_handling.py`).
- Optional (S5): a URLconf test requiring every HTMX fragment view to be decorated or listed as an
  explicit exemption.

**Acceptance:**
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
- `tests/unit_tests/adapters/views/test_views_calculated_attributes.py` (created by Task 9) —
  programmatic EdgeComputer + EdgeStorage system with two edge usage patterns: no duplicate `id=`
  in the edge computer panel; the CPU button's `hx-target`/`data-bs-target` point at its own row id,
  which exists.
- E2E selector updates to `^=` prefixes: `tests/e2e/test_calculus_graph.py:59`,
  `tests/e2e/objects/test_external_api_objects.py:70,74`,
  `tests/e2e/objects/test_video_external_api_objects.py:147,149`; run those three files.

**Acceptance:**
- No duplicate ids in any shipped example's panels (rerun the diagnostic's sweep after Task 6, which
  unblocks the component and storage panels).
- In the Factory-sensor panel, each CPU/RAM/storage formula button opens only its own explanation,
  and each stays reachable.

**Depends on:** Task 9 (shared new test file; also gives Task 9's empty dict entries distinct ids).

**Implementation:** easy — template id changes plus E2E selector updates.

## Task 11 — A referenced object is blocked from deletion; a confirmed delete never only unlinks

**Goal:** A confirmed delete either removes the object from the saved model or shows the error
modal with the session unchanged; it never returns 200 while the object survives. Today `_delete`'s
list/dict branch only unlinks the object and relies on `EditService`'s accordion-children diff to
delete it, and `check_can_delete` skips the direct-reference block whenever a list/dict container
exists. A usage journey (or edge usage journey) in a pattern that holds two journeys offers "Yes,
delete", is only unlinked from its patterns and reappears on reload. A pattern that still holds it
but has other journeys is left out of the blocking modal. Settled 2026-10-21: (1) a journey is
blocked while any pattern holds it, and the modal names every holding pattern; the user detaches it
first with the membership ×. (2) A custom edge-device component referenced by a recurrent component
need is blocked, naming the need. (3) Copy fixes ("reorient these edge devices" noun, journey
confirmation wording) are deferred to the copy backlog with smell-sweep S12. Only containers that
nest their child (`renders_relationship_children_as_nested_cards`) count as removal targets. The
sole-member block becomes dead and goes. Leftover references block. `_delete` gets one tail:
if the object is still present after unlinking, `pre_delete` then `self_delete()` (the library
raises on leftover references). Folds in smell-sweep S7 (the redundant `mirrored_cards` override).
Task 3's OOB-delete rule is unchanged.

**Diagnostic:** [`diagnostics/list-deletion-only-unlinks.md`](diagnostics/list-deletion-only-unlinks.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `model_builder/application/use_cases/delete_object.py` — nesting-only removal targets (around
  lines 61–73); delete the sole-member block (around 92–103); block on references left after removal
  (around 105–118); single deletion tail with one `delete_side_effects` call (around 177–235).
- `model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py` — remove the
  redundant `mirrored_cards` override (around 42–45); reword comments (around 47–60).
- `specs/architecture/forms-and-relationships.html` (around 168–181) — journeys are blocked while any
  pattern holds them, naming every pattern; a container that does not nest its child is a reference,
  not a removal target; `required_non_empty_relationships` now only guards last-member removal in
  widgets and membership sections.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `tests/unit_tests/application/use_cases/test_delete_object.py::TestDeleteObjectUseCase::test_referenced_object_is_blocked_naming_every_holder_and_never_only_unlinked`
  — reproduction; remove its expected-failure marker. No other tests.
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

**Depends on:** Task 8 (hard: otherwise an edge appliance's built-in component gets an error modal
instead of the blocking modal); Tasks 3, 4, 6 (soft; shared `delete_object.py`,
`test_views_deletion.py`, `test_delete_object.py`, `CHANGELOG.md`).

**Implementation:** standard — use-case deletion semantics on a full review surface; settled rule,
prototype-verified.

## Task 12 — Card highlight expands the canonical id within its owning canvas

**Goal:** Creating or editing a nested object (job, step, edge function, recurrent need or process,
edge component) pulses every one of its cards on the active canvas and scrolls the first into view;
opening a mirrored object's edit panel marks every mirror as opened. Root cards behave as before,
and nothing on a parked canvas is touched, even for a duplicated model with identical object ids.
Since `cc9611c3` prefixed root web ids with `sys-{system}-`, the client's `button-<id>_in_…`
expansion never matches nested ids (`Class-id_in_<parent>`). `cardButtonsForWebId` picks the
resident canvas whose `sys-${data-system-id}-` prefixes the id (longest wins), strips it to
`Class-id`, and queries `[id="button-${id}"], [id^="button-${local}_in_"]` inside that canvas only.
The header stays one canonical id (the nginx limit fixed by `0b2f361b`). Reproduced in a browser.

**Diagnostic:** [`diagnostics/card-highlight-id-mismatch.md`](diagnostics/card-highlight-id-mismatch.md)

**Repository:** `e-footprint-interface`

**Files touched:**
- `theme/static/scripts/model_builder_main.js` — `cardButtonsForWebId` (around lines 200–208):
  owner-canvas lookup via `[data-model-canvas][data-system-id]`, prefix stripping, scoped query,
  corrected comment.
- `model_builder/adapters/views/views_edition.py` (around 38–40) — comment only.
- `specs/architecture/rendering.html` — one line beside "Toast notifications and tooltips": one
  canonical `web_id` per highlight, expanded client-side to the owning canvas's root and `_in_`
  mirrors.
- `CHANGELOG.md` — `## [Unreleased]` fix entry.

**Tests added/changed:**
- `js_tests/build_fixtures.py` — programmatic system with a step and job shared by two journeys, a
  sibling job whose id shares a prefix, rendered on an active and a parked canvas (same object ids,
  fresh system id); expected button ids embedded as JSON from Python.
- `js_tests/model_builder_main.test.js` — pulse and opened sets match exactly on the active canvas;
  nothing on the parked canvas or the prefix-sharing sibling; root card; unknown system highlights
  nothing and does not throw.
- Optional: `tests/e2e/objects/test_edge_objects.py::test_edge_function_name_mirroring` asserts both
  mirrors get `.model-builder-card-opened`.

**Acceptance:**
- As in the goal; the highlight headers stay constant-size.

**Depends on:** none (shares only `CHANGELOG.md` and `js_tests/build_fixtures.py` with other tasks).

**Implementation:** easy — one client function, with a Python-generated fixture pinning the id rule.

## Task 13 — One web-class resolver and a `has_edit_panel` property (refactor)

**Goal:** One rule maps a library class to its web class: exact name, else the nearest mapped MRO
ancestor, else `ModelingObjectWeb`. `wrap_efootprint_object`, form generation and the use cases
use it (use cases read `type(web_obj)` instead of re-looking up `MAPPING`). Today three lookups
disagree on 10 concrete classes: after Task 6, `RecurrentEdgeProcess{CPU,RAM,Storage}Need` and
`RecurrentEdgeWorkloadNeed` get `ModelingObjectWeb` for panel, canvas and deletion but
`RecurrentEdgeComponentNeedWeb` for forms. A `has_edit_panel` wrapper property derived from the
resolver replaces the hard-coded class-name lists in the calculated-attribute templates (S11).
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
- View checks that the four recurrent process/workload need panels open and edit correctly.

**Acceptance:**
- No two paths resolve a library class to different web classes; no rendered link points at a
  class without an edit panel.
- Full non-E2E suite and edge E2E files pass unchanged.

**Depends on:** Task 8 (and therefore Tasks 4 and 6).

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

## Execution plan

Runs, ordering, deduplication verdicts and deferred items: [`plan.html#execution-plan`](plan.html#execution-plan).
