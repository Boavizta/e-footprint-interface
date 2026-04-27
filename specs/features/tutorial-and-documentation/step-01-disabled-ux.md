# Step 1 — Disabled-instead-of-error UX: implementation plan

## Goal

Replace after-the-fact error modals with preemptively disabled buttons and hover
tooltips on every "Add" action whose prerequisites are not yet met. Gate the two
"results" buttons (`#btn-open-panel-result` and toolbar "Show results") behind
model completeness. When any constraint flips, re-render the affected regions and
show a toast notification. No SSOT plumbing; this step is entirely within the
interface repo.

---

## Scope

### Classes with prerequisites

| Web class | File | Requires |
|---|---|---|
| `JobWeb` | `domain/entities/web_core/usage/job_web.py` | At least one server or external API |
| `UsagePatternWebBaseClass` | `domain/entities/web_core/usage/usage_pattern_web_base_class.py` | At least one usage journey (edge variant: edge usage journey) |
| `RecurrentServerNeedWeb` | `domain/entities/web_core/usage/edge/recurrent_server_web.py` | At least one edge device |
| `RecurrentEdgeDeviceNeedBaseWeb` | `domain/entities/web_core/usage/edge/recurrent_edge_device_need_base_web.py` | At least one edge device |

### Buttons to gate

**Top-level "Add" buttons** (`model_builder_main.html` via `add_object_button.html`):

| Button | Object type | Disable when |
|---|---|---|
| "Add usage pattern" | `UsagePattern` | `model_web.usage_journeys` empty |
| "Add edge usage pattern" | `EdgeUsagePattern` | `model_web.edge_usage_journeys` empty |

**Child "Add" buttons** (`add_child_button.html`):

| Context | Object type | Disable when |
|---|---|---|
| Journey / edge journey cards | `Job` | No servers or external APIs |
| Edge device cards | `RecurrentServerNeed` | No edge devices |
| Edge device cards | `RecurrentEdgeDeviceNeed` variants | No edge devices |

Journey step buttons have no prerequisites and are not affected.

**Results buttons:**

| Button | Location | Disable when |
|---|---|---|
| `#btn-open-panel-result` ("Results" bar) | `model_builder_main.html` (inside `#model-canva`) | `SystemValidationService.validate_for_computation` returns invalid |
| Toolbar "Show results" | `upload_download_reboot_model_tooltips.html` (outside `#model-canva`) | Same |

---

## Design

### `can_create` predicate

Add `can_create(cls, model_web) -> tuple[bool, str]` to each of the four classes.
This is the single source of truth for the prerequisite check. Return convention:
`(True, "")` when allowed; `(False, non_empty_reason)` when blocked.

`get_creation_prerequisites` is updated to call `can_create` and raise if it
returns `False`, preserving the creation endpoint as a last line of defence.

```python
@classmethod
def can_create(cls, model_web: "ModelWeb") -> tuple[bool, str]:
    if not model_web.servers + model_web.external_apis:
        return False, "Add a server or external API in the Infrastructure section first."
    return True, ""
```

### Tooltip copy guidelines

Plain English. Reference the object to create, not UI mechanics. No `click`,
`button`, `drag`, `instantiate`, `import`, or backticks.

- "Add a server or external API in the Infrastructure section first."
- "Add a usage journey in the Usage journeys section first."
- "Add an edge device in the Infrastructure section first."

### Constraint snapshot and re-render on change

**Snapshot.** `ModelWeb._build_creation_constraints()` iterates the unique web
classes from `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`, calls `can_create` on
each that has it, and returns a dict keyed by class name string:

```python
{"JobWeb": {"enabled": False, "reason": "..."}, "UsagePatternWebBaseClass": {"enabled": True, "reason": ""}, ...}
```

String keys make Django template lookups trivial
(`creation_constraints.JobWeb.enabled`). A test enforces that every key
corresponds to a class with `can_create` (or is `"__results__"`), and vice versa.

A special `"__results__"` key is added by running
`SystemValidationService.validate_for_computation`. When invalid, `reason` is the
combined validation error messages; when valid, `reason` is `""`.

`ModelWeb` computes and stores `self.creation_constraints` at init time (right
after loading the system).

**Diff on mutation.** The base `ModelingObjectWeb.create_side_effects` recomputes
constraints and compares against the snapshot. If any constraint flipped, it emits
OOB regions and stashes the diff on `model_web` for the presenter:

```python
# In ModelingObjectWeb (base class)
@classmethod
def create_side_effects(cls, added_obj, model_web):
    side_effects = CreateSideEffects()
    new_constraints = model_web._build_creation_constraints()
    if new_constraints != model_web.creation_constraints:
        side_effects.oob_regions.append(OobRegion("model_canvas"))
        side_effects.oob_regions.append(OobRegion("results_toolbar_button"))
        model_web.constraint_changes = _diff_constraints(
            model_web.creation_constraints, new_constraints)
        model_web.creation_constraints = new_constraints
    return side_effects
```

Same logic in the base `delete_side_effects` and `edit_side_effects`. The four
`can_create` constraints are count-based and can't flip during an edit, but the
`__results__` constraint can (e.g. editing a usage pattern to point to a journey
with no steps).

Subclasses that override `create_side_effects` (`EdgeDeviceGroupWeb`,
`EdgeDeviceBaseWeb`, `EdgeComponentBaseWeb`) are updated to call `super()` and
merge their own regions into the result, instead of constructing a fresh
`CreateSideEffects`. Same for `EdgeDeviceGroupWeb.delete_side_effects`.

**One toast per prerequisite group.** The constraint dict is keyed by the four base
web classes that define `can_create` (not by every concrete subclass) plus
`"__results__"`, so the diff produces at most five entries. One toast per flipped
entry.

**Two OOB regions.**

| OOB region key | What it re-renders | Why separate |
|---|---|---|
| `model_canvas` | `model_builder_main.html` content via `hx-swap-oob="innerHTML:#model-canva"` | Covers all "Add" buttons + `#btn-open-panel-result`. Accordion state preserved by `restoreAccordionStateInFragment`. |
| `results_toolbar_button` | The toolbar "Show results" `<div>` via `hx-swap-oob="outerHTML:#show-results-toolbar-btn"` | Lives in `upload_download_reboot_model_tooltips.html`, outside `#model-canva`. |

Both regions are emitted together whenever any constraint flips — they're cheap
and constraint flips are rare.

### JS reinitialization after canvas OOB swap

When the `model_canvas` OOB region replaces the full canvas content, JS
initialization must re-run: Bootstrap tooltips, accordion listeners, and
leaderlines. The presenter must include `initModelBuilderMain` and
`resetLeaderLines` in `HX-Trigger-After-Settle` whenever the `model_canvas` OOB
region is emitted.

### Toast messages

Toast copy is presentation, not domain logic. It lives in
`adapters/ui_config/constraint_toast_messages.py`, keyed by the same class name
strings used in the constraint dict:

```python
CONSTRAINT_TOAST_MESSAGES = {
    "JobWeb": {
        "unlocked": "You can now add jobs",
        "locked": "Job creation is no longer available",
    },
    "UsagePatternWebBaseClass": {
        "unlocked": "You can now add usage patterns",
        "locked": "Usage pattern creation is no longer available",
    },
    "RecurrentServerNeedWeb": {
        "unlocked": "You can now add recurrent server needs",
        "locked": "Recurrent server need creation is no longer available",
    },
    "RecurrentEdgeDeviceNeedBaseWeb": {
        "unlocked": "You can now add recurrent edge device needs",
        "locked": "Recurrent edge device need creation is no longer available",
    },
    "__results__": {
        "unlocked": "Your model is complete — results are now available",
        "locked": "Results are no longer available",
    },
}
```

The presenter reads `model_web.constraint_changes` (a list of
`(key, "unlocked" | "locked")` tuples), looks up each in
`CONSTRAINT_TOAST_MESSAGES`, and concatenates them into the existing action toast.
The current toast system uses a single element (`#toast-push-notification`), so
multiple messages are joined into one toast string (e.g. "Server has been saved!
— You can now add jobs"). No JS changes needed.

### Surfacing constraints in templates

The `model_builder_main` view passes `model_web.creation_constraints` as
`creation_constraints` in the template context (and `{}` in the `upload_json`
fallback path). No other view needs to change.

Since the dict is keyed by class name strings, Django template lookups work
natively (e.g. `creation_constraints.JobWeb.enabled`).

### Template changes

**`add_object_button.html`** — accept `disabled` (bool) and `disabled_reason`
(str). When `disabled`: add `disabled` attribute and Bootstrap tooltip attrs;
omit HTMX attrs and Hyperscript.

```html
<button ...
    {% if not disabled %}
    hx-get="{{ hx_url }}" hx-target="#sidePanel" hx-trigger="click"
    hx-swap="innerHTML" hx-disabled-elt="button"
    _="on click removeAllOpenedObjectsHighlights()"
    {% else %}
    disabled data-bs-toggle="tooltip" data-bs-placement="top" title="{{ disabled_reason }}"
    {% endif %}
>...</button>
```

**`add_child_button.html`** — same treatment for the "Add new" button; "Link
existing" is unaffected.

**`model_builder_main.html`** — for each gated "Add" include, use `{% if %}` to
pass `disabled=True` and `disabled_reason` from `creation_constraints`. Gate
`#btn-open-panel-result` the same way using the `__results__` entry.

**`upload_download_reboot_model_tooltips.html`** — wrap the toolbar "Show results"
`<div>` in a stable `<div id="show-results-toolbar-btn">`. Gate it using the
`__results__` constraint: when disabled, add `disabled` styling and tooltip, omit
HTMX attrs.

Card templates follow the same pattern for child buttons.

### Bootstrap tooltip initialization

Confirm the existing `initModelBuilderMain` JS handler already initializes
`data-bs-toggle="tooltip"` elements. If not, add it to the post-settle HTMX
handler.

---

## Files to change

### Domain

1. `domain/entities/web_core/model_web.py` — add `_build_creation_constraints()`
   (includes `__results__` via `SystemValidationService`); store
   `self.creation_constraints` at init time.
2. `domain/entities/web_core/usage/job_web.py` — add `can_create`; delegate from
   `get_creation_prerequisites`.
3. `domain/entities/web_core/usage/usage_pattern_web_base_class.py` — same.
4. `domain/entities/web_core/usage/edge/recurrent_server_web.py` — same.
5. `domain/entities/web_core/usage/edge/recurrent_edge_device_need_base_web.py` —
   same.
6. `domain/entities/web_abstract_modeling_classes/modeling_object_web.py` — add
   constraint-diff logic to base `create_side_effects`, `delete_side_effects`, and
   `edit_side_effects`; emit both `model_canvas` and `results_toolbar_button` OOB
   regions on flip.
7. `domain/entities/web_core/hardware/edge/edge_device_base_web.py` — update
   `create_side_effects` to call `super()` and merge.
8. `domain/entities/web_core/hardware/edge/edge_component_base_web.py` — same.
9. `domain/entities/web_core/hardware/edge/edge_device_group_web.py` — same for
   both `create_side_effects` and `delete_side_effects`.

### Adapter / presenter

10. `adapters/ui_config/constraint_toast_messages.py` — new file; toast copy keyed
    by web class + `"__results__"`.
11. `adapters/presenters/oob_regions.py` — add two renderers:
    - `model_canvas`: re-renders `model_builder_main.html` as
      `hx-swap-oob="innerHTML:#model-canva"`.
    - `results_toolbar_button`: re-renders the toolbar "Show results" wrapper as
      `hx-swap-oob="outerHTML:#show-results-toolbar-btn"`.
12. `adapters/presenters/htmx_presenter.py` — read `model_web.constraint_changes`,
    look up toast copy from `constraint_toast_messages`, concatenate into the
    action toast, and add `initModelBuilderMain` + `resetLeaderLines` to
    `HX-Trigger-After-Settle` when `model_canvas` OOB is emitted.
13. `adapters/views/views.py` — pass `model_web.creation_constraints` as template
    context in `model_builder_main` and `upload_json`.

### Templates

14. `templates/model_builder/components/add_object_button.html` — disabled state +
    tooltip.
15. `templates/model_builder/components/add_child_button.html` — same for "Add new"
    button.
16. `templates/model_builder/model_builder_main.html` — gate `UsagePattern` and
    `EdgeUsagePattern` buttons; gate `#btn-open-panel-result` with `__results__`.
17. `templates/model_builder/upload_download_reboot_model_tooltips.html` — wrap
    "Show results" in `<div id="show-results-toolbar-btn">`; gate with
    `__results__`.
18. Card templates that include `add_child_button.html` for `Job`,
    `RecurrentServerNeed`, and `RecurrentEdgeDeviceNeed` — gate accordingly. Locate
    exact sites by searching for `add_child_button.html` in templates.

---

## Tests

### Existing tests — keep as-is

The existing `test_get_creation_prerequisites_requires_*` tests already cover the
prerequisite logic. Since `get_creation_prerequisites` now delegates to
`can_create`, these tests implicitly cover the predicate too. No new
`test_can_create.py` needed.

### New integration test — `tests/integration/test_constraint_change_rerendering.py`

Domain-only integration tests (no browser, uses `InMemorySystemRepository` +
`ModelWeb`) covering the constraint-change → OOB region mechanism:

- Base `create_side_effects` emits `model_canvas` and `results_toolbar_button` OOB
  regions when constraints change (e.g. first server created) and does not emit
  them when they don't.
- Base `delete_side_effects` emits both OOB regions when constraints change (e.g.
  last server deleted) and does not emit them when they don't.
- Subclass overrides (`EdgeDeviceBaseWeb`, `EdgeComponentBaseWeb`,
  `EdgeDeviceGroupWeb`) preserve the constraint-diff OOB regions from `super()`
  alongside their own regions.
- `model_web.constraint_changes` is populated correctly on a 0→1 and 1→0
  transition and is absent/empty when no constraint flipped.

### New unit test — `tests/unit_tests/adapters/ui_config/test_ui_config_consistency.py`

Constraint and UI config consistency checks:

- Every key in `_build_creation_constraints()` output has a matching entry in
  `CONSTRAINT_TOAST_MESSAGES`, and vice versa.
- Every key (except `"__results__"`) is the `__name__` of a web class that defines
  `can_create`.
- Every entry in `CONSTRAINT_TOAST_MESSAGES` has both `"unlocked"` and `"locked"`
  non-empty strings.
- Every key in `class_ui_config.json` is the name of a class in
  `MODELING_OBJECT_CLASSES_DICT` (catches stale entries from deleted classes).

### E2E — extend `test_complete_model_building_workflow`

Add button activation state assertions at natural points in the existing workflow:
check buttons are disabled before their prerequisite is created, enabled after.
No new test file needed.

---

## Out of scope

- `can_create` on classes without existing prerequisites.
- Library CI workflow — excluded per user instruction.
