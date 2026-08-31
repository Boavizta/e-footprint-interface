# Persistent object-card ordering — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

## Task 1 — Persist and restore the six-list order

**Status:** Pending.

**Goal:** Establish the complete server-side contract for saving card order and rendering every resident model canvas
from its own saved order, without changing `ModelWeb` or relying on client-side reordering.

**Files touched:**

- `model_builder/adapters/views/views.py`
- `model_builder/urls.py`
- `model_builder/templates/model_builder/components/model_canvas_content.html`
- `model_builder/templates/model_builder/object_cards/partials/root_edge_device_groups_list.html`
- `model_builder/templates/model_builder/object_cards/partials/ungrouped_edge_devices_list.html`
- `tests/unit_tests/adapters/views/test_card_order_views.py`
- `tests/unit_tests/adapters/views/test_views_upload_json.py` if focused import coverage fits the existing suite better
- `CHANGELOG.md` if this task is implemented standalone (the feature loop defers a consolidated entry)

**Tests added/changed:**

- Unit-test the stable rank merge with exact saved order, missing configuration, stale saved IDs, duplicate saved IDs,
  and newly added objects appended in their original relative order.
- Exercise combined web/edge usage-pattern and usage-journey lists as single rendered lists.
- POST a complete payload containing `up-list`, `uj-list`, `external-api-list`, `server-list`,
  `edge-device-groups-list`, and `edge-devices-list`, then assert that the identical six-list mapping is stored under
  `interface_config["card_order"]`.
- Assert the POST preserves existing sibling configuration such as `sankey_diagrams`, persists through the repository,
  and changes only the active workspace slot.
- Assert malformed, missing-key, extra-key, or non-string-array payloads return 400 without changing saved config.
- Render a two-model workspace whose slots have different orders and assert each resident canvas receives its own
  adapter-sorted lists.
- Cover JSON import with `card_order` where needed to make the existing generic `interface_config` round trip explicit.

**Acceptance:**

- The POST endpoint accepts one complete, valid six-list order and persists it through the active repository's existing
  cache/session path; it never overwrites other `interface_config` keys.
- Fresh renders use explicit adapter-provided lists for all six top-level card containers, including root edge-device
  groups and ungrouped edge devices.
- Saved IDs absent from the model are ignored; current objects absent from the saved order are appended stably.
- Rank merging is `O(n + m)` per list rather than repeatedly scanning the saved array.
- Each resident workspace canvas uses its own model-scoped `card_order`.
- `ModelWeb` and the e-footprint library remain unchanged.
- The affected Python tests pass and the repository remains fully functional before the browser save trigger is wired.

**Depends on:** none.

---

## Task 2 — Save every SortableJS list and prove the round trip

**Status:** Pending.

**Goal:** Connect drag completion to the server contract, guard against any sortable list being omitted from persistence,
and verify the user-visible reload and JSON export/import outcomes.

**Files touched:**

- `theme/static/scripts/model_builder_main.js`
- `js_tests/model_builder_main.test.js`
- `js_tests/build_fixtures.py` if a rendered canvas fixture is needed
- `tests/e2e/pages/model_builder_page.py`
- `tests/e2e/test_card_order_persistence.py`
- `specs/architecture.md`
- `CHANGELOG.md` if this task is implemented standalone, or for the consolidated entry when the feature loop is used

**Tests added/changed:**

- Stub SortableJS and assert the six canonical containers are initialized, including `external-api-list`, with
  `dataIdAttr: "id"`.
- Derive the initialized Sortable instances in the regression test, trigger `onEnd` for every one, and assert every
  emitted POST contains every initialized list ID mapped to that instance's current `toArray()` value. The test must fail
  if any initialized sortable list is missing from persistence.
- Assert one drag end produces one complete request only, while still removing the grab state and updating leader lines.
- Assert a rejected background request does not revert the DOM or produce an unhandled promise rejection.
- Add a Playwright workflow that reorders cards, reloads, and observes the saved order.
- In the same focused workflow or a second non-redundant case, download the reordered model, replace/reset its state,
  upload the downloaded JSON, and observe the restored order.

**Acceptance:**

- SortableJS initializes all six lists from one shared list-ID definition and reads existing card IDs without template
  attribute changes.
- Every `onEnd` sends exactly one fire-and-forget POST containing the full current order of all six sortable lists.
- Automated coverage proves that every initialized sortable list is persisted; adding or removing an initialized list
  without updating persistence cannot pass the Jest suite.
- Dragged order survives a real page reload and a real download/upload round trip.
- The active model is saved after a workspace switch, while parked-canvas ID suffixing and reinitialization continue to
  work with the existing resident-canvas design.
- `specs/architecture.md` documents `interface_config["card_order"]`, six-list drag-end persistence, and adapter-side
  restoration; no `AGENTS.md` update is needed unless implementation reveals a broader contributor rule.
- Applicable Jest, Python, and Playwright suites pass; the full repository quality gates are run before shipping.

**Depends on:** Task 1.

---

## Ordering rationale

Task 1 groups the endpoint, repository write, stable ordering helper, template context, and Python tests because there is
no useful review boundary inside that server-rendered contract. It leaves a green, independently reviewable backend that
can save and restore injected order data while remaining unused by the browser.

Task 2 then supplies the first user-visible behavior and its browser-level evidence. The SortableJS wiring, exhaustive
all-sortables regression test, reload/export/import workflow, architecture note, and changelog belong together because
they collectively prove and document the completed interaction rather than separate technical layers.
