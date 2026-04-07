# Implementation Plan: Edge Device Groups in the Interface

## Context

EdgeDeviceGroup is fully implemented in the e-footprint backend but has zero web interface support. This plan adds full CRUD support for groups in the interface: displaying them in the infrastructure column, creating/editing/deleting them via side panels, and managing dict-based relationships (device-to-count and sub-group-to-count mappings).

The design document is at `design-discussion.md` (same folder).

---

## Phase 1: Backend wiring (registration, web wrapper, ModelWeb)

### 1a. Create EdgeDeviceGroupWeb class

**New file:** `model_builder/domain/entities/web_core/hardware/edge/edge_device_group_web.py`

Follow the pattern from `edge_device_base_web.py` and `edge_device_web.py`:

```python
class EdgeDeviceGroupWeb(ModelingObjectWeb):
    add_template = "add_edge_device_group.html"
    attributes_to_skip_in_forms = ["sub_group_counts", "edge_device_counts"]
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def template_name(self):
        return "edge_device_group"

    @classmethod
    def prepare_creation_input(cls, form_data):
        form_data = dict(form_data)
        form_data["sub_group_counts"] = {}
        form_data["edge_device_counts"] = {}
        return form_data

    @classmethod
    def pre_delete(cls, web_obj, model_web):
        # Remove from all parent groups' sub_group_counts dicts
        # (backend self_delete raises PermissionError if still referenced)
        efp_obj = web_obj.modeling_obj
        for parent_dict in list(efp_obj.explainable_object_dicts_containers):
            if efp_obj in parent_dict:
                del parent_dict[efp_obj]
```

Why `attributes_to_skip_in_forms`: the two dict attributes (`sub_group_counts`, `edge_device_counts`) are managed through the dedicated dict-count widget, not the standard form field generator. The only standard form field is `name`.

### 1b. Register in mapping

**File:** `model_builder/domain/efootprint_to_web_mapping.py`

Add import and entry to `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`:
```python
"EdgeDeviceGroup": EdgeDeviceGroupWeb,
```

### 1c. Add UI config label

**File:** `model_builder/adapters/ui_config/class_ui_config.json`

```json
"EdgeDeviceGroup": {
    "label": "Edge device group"
},
```

### 1d. Add ModelWeb accessors

**File:** `model_builder/domain/entities/web_core/model_web.py` (after `edge_devices` property, ~line 187)

```python
@property
def edge_device_groups(self):
    return self.get_web_objects_from_efootprint_type("EdgeDeviceGroup")

@property
def root_edge_device_groups(self):
    """Root-level groups (not sub-groups of any other group)."""
    return [g for g in self.edge_device_groups
            if not g.modeling_obj._find_parent_groups()]

@property
def ungrouped_edge_devices(self):
    """Edge devices not in any group."""
    return [d for d in self.edge_devices
            if not d.modeling_obj._find_parent_groups()]
```

### 1e. Add pre_delete hooks for objects referenced in group dicts

Both `EdgeDevice.self_delete()` and `EdgeDeviceGroup.self_delete()` raise `PermissionError` if the object is still referenced in parent group dicts. The interface must remove these references before deletion.

**File:** `model_builder/domain/entities/web_core/hardware/edge/edge_device_base_web.py`

Add `pre_delete` (on base class since EdgeComputer/EdgeAppliance can also be group members):
```python
@classmethod
def pre_delete(cls, web_obj, model_web):
    efp_obj = web_obj.modeling_obj
    for parent_dict in list(efp_obj.explainable_object_dicts_containers):
        if efp_obj in parent_dict:
            del parent_dict[efp_obj]
```

The same pattern is used in `EdgeDeviceGroupWeb.pre_delete` (step 1a).

---

## Phase 2: Infrastructure column display

### 2a. Group card template

**New file:** `model_builder/templates/model_builder/object_cards/edge_device_group_card.html`

Accordion card following the pattern from `edge_device_with_accordion_card.html`:
- Outer card div with `id="{{ object.web_id }}"`, standard card classes
- Accordion header: chevron + group name button (click opens edit panel via `hx-get="/model_builder/open-edit-object-panel/{{ object.efootprint_id }}/"`)
- Accordion body containing group content partial (see 2b)
- "Add or link existing" button at bottom → opens group edit panel

### 2b. Group content partial (recursive)

**New file:** `model_builder/templates/model_builder/object_cards/partials/group_content.html`

Renders one level of group contents. Receives `group` (the web-wrapped EdgeDeviceGroup) as context:

1. **Sub-groups** (rendered first, visually distinct):
   For each `(sub_group, count)` in `group.modeling_obj.sub_group_counts.items()`:
   - Entry row with slightly different styling (background: `var(--gray-50)`, font-weight: 400)
   - Chevron + sub-group name + count badge (`×N`) + unlink button (`×`)
   - Nested accordion body: recursively `{% include "partials/group_content.html" with group=sub_group_web %}`

2. **Devices** (below sub-groups):
   For each `(device, count)` in `group.modeling_obj.edge_device_counts.items()`:
   - Entry row: chevron + device name (clickable → device edit panel) + count badge + unlink button
   - Component accordion inside (reuse existing `edge_component_card.html` pattern)

Count badges use `hx-post` to `update-dict-count` endpoint (Phase 4).
Unlink buttons use `hx-post` to `unlink-dict-entry` endpoint (Phase 4).

### 2c. Update infrastructure column

**File:** `model_builder/templates/model_builder/model_builder_main.html`

1. Add "Add group" button to the button grid (after the edge device button, ~line 42):
```html
{% include 'model_builder/components/add_object_button.html' with btn_id="btn-add-edge-device-group" hx_url="/model_builder/open-create-object-panel/EdgeDeviceGroup/" label="Add group" btn_extra_classes="" %}
```

2. Add `#edge-device-groups-list` container ABOVE `#edge-devices-list` (~line 54):
```html
<div id="edge-device-groups-list" class="list-group d-flex flew-column w-75 ms-25">
    {% for group in model_web.root_edge_device_groups %}
        {% include 'model_builder/object_cards/edge_device_group_card.html' with object=group %}
    {% endfor %}
</div>
```

3. Change `#edge-devices-list` to iterate `model_web.ungrouped_edge_devices` instead of `model_web.edge_devices`.

### 2d. Add Sortable for groups

**File:** `theme/static/scripts/model_builder_main.js` (~line 27)

```javascript
new Sortable(document.getElementById("edge-device-groups-list"), options);
```

---

## Phase 3: Dict mutation endpoints

These endpoints power the inline count edits, unlink buttons, and link actions throughout the UI.

### 3a. New view functions

**New file:** `model_builder/adapters/views/views_dict_mutation.py`

```python
def update_dict_count(request, parent_id, key_id):
    """POST: Update count of an entry in a group's dict."""
    # 1. Load model, find parent group and key object
    # 2. Determine which dict (sub_group_counts or edge_device_counts) based on key type
    # 3. Update: parent_dict[key_obj] = SourceValue(new_count * u.dimensionless)
    # 4. Persist and return OOB response re-rendering all root groups + ungrouped devices list

def unlink_dict_entry(request, parent_id, key_id):
    """POST: Remove an entry from a group's dict."""
    # 1-2. Same as above
    # 3. del parent_dict[key_obj]
    # 4. Persist and return OOB response

def link_dict_entry(request, parent_id, key_id):
    """POST: Add an entry to a group's dict with count=1."""
    # 1-2. Same as above
    # 3. parent_dict[key_obj] = SourceValue(1 * u.dimensionless)
    # 4. Persist and return OOB response
```

### 3b. URL routing

**File:** `model_builder/urls.py`

```python
path("update-dict-count/<str:parent_id>/<str:key_id>/", views_dict_mutation.update_dict_count),
path("unlink-dict-entry/<str:parent_id>/<str:key_id>/", views_dict_mutation.unlink_dict_entry),
path("link-dict-entry/<str:parent_id>/<str:key_id>/", views_dict_mutation.link_dict_entry),
```

### 3c. HTMX response for dict mutations

OOB-swap strategy (consistent with design doc):
1. Re-render all root group cards: `hx-swap-oob="outerHTML:#<group_web_id>"` for each
2. Re-render ungrouped devices list: `hx-swap-oob="innerHTML:#edge-devices-list"` (if a device moved in/out)
3. Use `restoreAccordionStateInFragment` to preserve open/close state

Follow the presenter pattern from `_generate_mirrored_cards_html()` in `htmx_presenter.py`.

### 3d. Inline count edit in card template

```html
<input type="number" min="1" value="{{ count }}"
       hx-post="/model_builder/update-dict-count/{{ group.efootprint_id }}/{{ entry.efootprint_id }}/"
       hx-trigger="change" hx-swap="none" name="count"
       class="count-inline-edit">
```

### 3e. Unlink button in card template

```html
<button hx-post="/model_builder/unlink-dict-entry/{{ group.efootprint_id }}/{{ entry.efootprint_id }}/"
        hx-swap="none" class="unlink-btn" title="Remove from {{ group.name }}">
    &times;
</button>
```

---

## Phase 4: Group creation side panel

### 4a. Custom add template

**New file:** `model_builder/templates/model_builder/side_panels/add/add_edge_device_group.html`

Follow pattern from `add_edge_device.html`:
- Form with `hx-target="#edge-device-groups-list"` and `hx-swap="beforeend"`
- Standard name field (via `add_form_content.html`)
- Dict-count widget for sub-groups (select from existing groups, each with count)
- Dict-count widget for edge devices (select from existing devices, each with count)

### 4b. Dict-count form widget

**New file:** `model_builder/templates/model_builder/side_panels/dynamic_form_fields/dict_count.html`

Inspired by `select_multiple.html` but with per-entry count fields:

```
┌─ Sub-groups ─────────────────────────────┐
│ [Dropdown: available groups ▼] [+ Add]   │
│                                          │
│ Shelf 1           ×[3]         [Remove]  │
│ Shelf 2           ×[1]         [Remove]  │
└──────────────────────────────────────────┘
```

- Dropdown shows only objects NOT already selected
- "Add" inserts with count = 1
- Each entry: name, `<input type="number" min="1">`, remove button
- Hidden input stores JSON: `{"<obj_id>": count, ...}`

### 4c. Dict-count JS helpers

**New file:** `theme/static/scripts/dict_count.js`

- `addDictCountEntry(fieldId)` — move selected from dropdown to entries list, count=1
- `removeDictCountEntry(fieldId, objId)` — remove entry, return to dropdown
- `refreshDictCountField(fieldId)` — update hidden JSON input

### 4d. Form context for creation

**File:** `model_builder/adapters/forms/form_context_builder.py`

`build_creation_context` provides available groups and devices for the dict-count widgets:
- `available_edge_device_groups`: all existing groups (for sub-group picker)
- `available_edge_devices`: all existing devices (for device picker)

### 4e. post_create hook to populate dicts

The creation form includes dict-count data as JSON in the form submission. A `post_create` hook on `EdgeDeviceGroupWeb` populates the dicts after the empty group is created:

```python
@classmethod
def post_create(cls, added_obj, form_data, model_web):
    efp_obj = added_obj.modeling_obj
    for group_id, count in json.loads(form_data.get("sub_group_counts_json", "{}")).items():
        group = model_web.flat_efootprint_objs_dict[group_id]
        efp_obj.sub_group_counts[group] = SourceValue(int(count) * u.dimensionless)
    for device_id, count in json.loads(form_data.get("edge_device_counts_json", "{}")).items():
        device = model_web.flat_efootprint_objs_dict[device_id]
        efp_obj.edge_device_counts[device] = SourceValue(int(count) * u.dimensionless)
```

---

## Phase 5: Group edit side panel

### 5a. Custom edit template for groups

**New file:** `model_builder/templates/model_builder/side_panels/edit/edit_edge_device_group.html`

Extends `edit_panel__generic.html`. Adds dict-count sections below the standard name form:
- Sub-groups dict-count widget (independent HTMX actions via Phase 3 endpoints)
- Devices dict-count widget (same)
- Calculated attributes accordion at bottom

Set `edit_template = "edit_edge_device_group.html"` on `EdgeDeviceGroupWeb`.

The dict-count widgets here work differently from the creation form: each add/remove action is an individual HTMX request (via `link-dict-entry` / `unlink-dict-entry`), not part of a batched form submit.

### 5b. Cycle prevention in sub-group picker

The available groups dropdown for sub-groups must exclude:
- The group itself
- All ancestors (via `_find_all_ancestor_groups()`)
- Groups already in the dict

Computed in the view and passed as template context.

### 5c. Group membership in device edit panel

**File:** `model_builder/templates/model_builder/side_panels/edit/edit_panel__generic.html`

Add conditional block between form and calculated attributes:
```html
{% if group_memberships %}
<div class="my-3">
    <h6>Group membership</h6>
    {% for membership in group_memberships %}
    <div class="d-flex align-items-center gap-2 mb-2">
        <span>{{ membership.group_name }}</span>
        <input type="number" min="1" value="{{ membership.count }}"
               hx-post="/model_builder/update-dict-count/{{ membership.group_id }}/{{ object_to_edit.efootprint_id }}/"
               hx-trigger="change" hx-swap="none">
        <button hx-post="/model_builder/unlink-dict-entry/{{ membership.group_id }}/{{ object_to_edit.efootprint_id }}/"
                hx-swap="none" class="btn btn-sm btn-outline-danger">Remove</button>
    </div>
    {% endfor %}
</div>
{% endif %}
```

**File:** `model_builder/adapters/views/views_edition.py`

When opening edit panel for an edge device, compute `group_memberships` by iterating `device.explainable_object_dicts_containers` and pass to template context.

---

## Phase 6: CSS and styling

**File:** `theme/static/scss/` or inline in templates

Styles from the mockup (`feature/edge-device-group/mockup.html`):
- `.count-badge` — small inline badge (×N), primary color, clickable
- `.count-inline-edit` — inline number input replacing badge on click
- `.unlink-btn` — small × button, gray default, red on hover
- `.subgroup-entry` — distinct from device entries (gray-50 bg, font-weight 400)

---

## Implementation order

| Step | Phase | What | Testable outcome |
|------|-------|------|------------------|
| 1 | 1 | Backend wiring | Groups exist in ModelWeb, visible in debug |
| 2 | 2 | Infrastructure display | Group cards render (read-only, no inline actions yet) |
| 3 | 3 | Dict mutation endpoints | Count edit and unlink work in cards |
| 4 | 4 | Creation panel | "Add group" creates groups with optional members |
| 5 | 5 | Edit panel + membership | Full edit flow, device membership display |
| 6 | 6 | Styling polish | Visual match with mockup |

---

## Files summary

### New files (8)

| File | Purpose |
|------|---------|
| `model_builder/domain/entities/web_core/hardware/edge/edge_device_group_web.py` | Web wrapper |
| `model_builder/templates/model_builder/object_cards/edge_device_group_card.html` | Group card |
| `model_builder/templates/model_builder/object_cards/partials/group_content.html` | Recursive group content partial |
| `model_builder/templates/model_builder/side_panels/add/add_edge_device_group.html` | Creation panel |
| `model_builder/templates/model_builder/side_panels/edit/edit_edge_device_group.html` | Edit panel |
| `model_builder/templates/model_builder/side_panels/dynamic_form_fields/dict_count.html` | Dict-count widget |
| `model_builder/adapters/views/views_dict_mutation.py` | Dict mutation endpoints |
| `theme/static/scripts/dict_count.js` | Dict-count widget JS |

### Modified files (10)

| File | Change |
|------|--------|
| `model_builder/domain/efootprint_to_web_mapping.py` | Add `EdgeDeviceGroupWeb` mapping |
| `model_builder/adapters/ui_config/class_ui_config.json` | Add label |
| `model_builder/domain/entities/web_core/model_web.py` | Add `edge_device_groups`, `root_edge_device_groups`, `ungrouped_edge_devices` |
| `model_builder/domain/entities/web_core/hardware/edge/edge_device_base_web.py` | Add `pre_delete` hook |
| `model_builder/templates/model_builder/model_builder_main.html` | Add button + `#edge-device-groups-list` container |
| `theme/static/scripts/model_builder_main.js` | Add Sortable for groups |
| `model_builder/urls.py` | Add 3 dict mutation URL patterns |
| `model_builder/templates/model_builder/side_panels/edit/edit_panel__generic.html` | Add group membership block |
| `model_builder/adapters/views/views_edition.py` | Pass `group_memberships` context |
| `model_builder/adapters/forms/form_context_builder.py` | Provide available groups/devices for dict-count |

---

## Verification

1. **Start server:** `python manage.py runserver`
2. **Create group:** "Add group" → enter name → save → card appears in `#edge-device-groups-list`
3. **Add device to group:** Open group edit panel → dict-count widget → add device → device moves from ungrouped list to group card
4. **Inline count edit:** Click count badge in card → change value → blur → count persists
5. **Unlink:** Click × on device in card → device returns to ungrouped list
6. **Nested groups:** Create two groups, add one as sub-group → nested accordion renders
7. **Delete group:** Sub-groups become root, devices become ungrouped
8. **Delete grouped device:** Removed from group dicts first, then deleted cleanly
9. **Device edit panel:** "Group membership" section shows per-group count and remove button
10. **Run tests:** `poetry run pytest`
