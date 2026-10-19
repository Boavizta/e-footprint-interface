# Server-rendered state follow-up — kickoff note

Status: kickoff note, not yet specified · 2026-10-19 · Interface-owned

Run `spec-specify server-rendered-state-follow-up` in a fresh session to turn this note into
`spec.html`. This note records the survey that motivates the feature so that session does not have
to rediscover it. It is deliberately a note, not a spec: scope, success criteria and tradeoffs are
still to be shaped.

## Why

[request-lifecycle-simplification](../request-lifecycle-simplification/spec.html) establishes the
convention that feature JavaScript observes request completion through one signal and treats the
server-rendered fragment as the state after a request. It applies that rule to Simplified inputs
and the Results panel, and explicitly leaves older modules out of scope so its diff stays
reviewable. A survey of the remaining modules found two groups that break the same rule and are
worth a second, separate pass. Everything else surveyed is client-owned by nature (drafts, widget
state, ephemeral UI state, per-browser preferences) and should stay as it is.

Apply the convention from `specs/conventions.md` (JavaScript section) once that feature ships;
if this feature starts before it, read the convention text in the request-lifecycle plan,
section 1.1.

## Group 1 — the client reconstructs state the server already owns

All in `theme/static/scripts/source_metadata.js` except the last item.

| Item | Where | What happens today | Candidate direction |
|---|---|---|---|
| Source table row update | `updateSourceTableRowDisplay()` line 333, called from the `htmx:afterRequest` handler at line 579 | After the row form's POST succeeds, the client rewrites the row display from the values it submitted. The code comment states the server has persisted the metadata and the client "already knows" the text. | The row endpoint returns the rendered row as an out-of-band fragment; the handler goes. |
| Custom source broadcast | `_broadcastNewSource()` line 451, `_broadcastSourceToEditors()` line 457 | When a custom source is applied in one editor, the client inserts or renames an option in every sibling source select so they can pick it. The available-source list is repository state. | Either refresh the selects from a server fragment, or do not broadcast and let the next server render include the new source. Check how often a user applies a custom source and then picks it in a sibling field of the same form before saving. |
| Confidence autosave | `autosaveConfidence()` line 137 | The badge is updated locally, then a POST is sent with `swap: "none"` and no outcome handling. A failed save leaves the badge showing a value the server did not accept. | The response renders the badge; failure shows the exception modal as elsewhere. |
| Provisional bookmark dependency locks | `theme/static/scripts/simplified_inputs/bookmarks.js`, `refreshCreationBookmarks()` line 28 and `isActiveCreationBookmark()` line 23 | During object creation, the client re-derives which inputs are required by which, from the dynamic-form JSON (`dynamic_lists`, `simplified_required_by`) and a chain-following loop. This duplicates the catalog dependency rule the server applies for saved objects. It exists because the object does not exist yet. | Lock nothing client-side while creating; the server applies dependencies when the object is saved and the first render shows the result. Accepted constraint to weigh: during creation a user can tick an input whose companion the server will add on save. |

## Group 2 — request sequencing done by hand

| Item | Where | What happens today | Candidate direction |
|---|---|---|---|
| Timeseries preview | `theme/static/scripts/timeseries_preview.js` (about 300 lines): `scheduleRequest()` line 140, `sendRequest()` line 92, `cancelRequest()` line 75, `abortRequest()` line 67, `beginRequestRevision()` line 43, `updateDeleteReadiness()` line 49, `consumeResponses()` line 239 | Per-region debounce timers, an active-request map, a request sequence number echoed by the server (`request_sequence`, required by `views_timeseries_preview.py` line 166 and rendered back as `data-request-sequence` in `side_panels/timeseries_preview.html`), stale requests aborted by dispatching `htmx:abort` on a detached `span` created as the request source, responses parked in a sink and selected by sequence, and the Delete button disabled while previews are pending. | HTMX natively covers debounce (`hx-trigger="... changed delay:..."`), stale-request replacement (`hx-sync="closest form:replace"`) and the disabled button (`hx-disabled-elt`). With request replacement the server-side sequence echo and the response sink are unnecessary. Consumers: `timeseries_preview.html`, `timeseries_preview_panel.html`, `edit_panel__generic.html`, `edit_recurrent_edge_component_need.html`, `dynamic_form_fields/hourly_quantities_from_growth.html`. |
| Deferred side-panel request replay | `theme/static/scripts/side_panel_utils.js`: `htmx:beforeRequest` guard line 127 and `proceedWithPendingRequest()` line 199 | One unsaved-changes guard cancels a `#sidePanel`-targeted request, then re-issues it by reading the element's `hx-get`, `hx-vals` (including `eval` of `js:` values) and `hx-target`. The other guard in the same file (`htmx:confirm` line 162, `proceedWithPendingNavigation()` line 173) defers through `event.detail.issueRequest(true)`, which re-fires the exact request. | Unify both guards on the `htmx:confirm` mechanism. Removes the attribute re-reading and the `eval`. The architecture page `specs/architecture/workspace.html` describes both guards today and would be reconciled. |

## Surveyed and deliberately left alone

- `workspace.js` remembered base view per model (client map, lost on reload): defensible; moving it
  server-side costs a request on the Modeling switch that needs none today. Low priority; note it in
  the spec's out-of-scope list if not taken.
- `model_builder_main.js` accordion state preserved across out-of-band fragments: ephemeral UI state.
- `side_panel_utils.js` recomputation flag read from Results panel visibility: only the browser knows.
- Edge-modeling and first-run flags in local storage: per-browser preferences.
- Form dirty flags, weekly pattern builder, dict-count and multi-select widgets: drafts before submit.
- Card order and Sankey card deletion `fetch` calls: JSON endpoints, server-owned, no swap involved.

## Shaping hints for the specify session

- Separate correctness items from maintainability items. The confidence autosave showing an
  unaccepted value is a correctness gap; the rest is maintenance.
- Each candidate trades a small client convenience for less coordination; name the accepted
  constraint per item as the request-lifecycle spec did.
- Jest coverage: `js_tests/source_metadata.test.js`, `js_tests/timeseries_preview.test.js`,
  `js_tests/side_panel_switch_guard.test.js` encode current behaviour and will need outcome-based
  rewrites rather than adaptation.
