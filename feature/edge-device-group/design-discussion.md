# Edge Device Groups in the Interface — Design

## What EdgeDeviceGroup is (backend recap)

An `EdgeDeviceGroup` is a purely organizational modeling object:
- Two dict attributes: `sub_group_counts` (keys: EdgeDeviceGroup, values: counts)
  and `edge_device_counts` (keys: EdgeDevice, values: counts)
- Groups can nest arbitrarily deep; practical use is 2-3 levels, up to 5
- A device or sub-group can appear in multiple parent groups (additive contribution)
- Groups carry no footprint — they multiply device counts
- Groups are optional — ungrouped devices keep `total_nb_of_units = 1`

Counting hierarchy:
`EdgeUsageJourney (ensembles) x Group (devices/ensemble) x Component (units/device)`

## Finalized design

### Display: Groups as accordion containers in Infrastructure column

Groups appear as top-level cards in a dedicated `#edge-device-groups-list`
container. Ungrouped devices remain in `#edge-devices-list` below.
A new "Add group" button in the top button row.

```
Infrastructure
├── [Add server] [Add ext API] [Add edge device] [Add group]
├── External APIs: [...]
├── Servers: [...]
├── [Group: "Rack A"] ▸
│     [Shelf 1] ×3 ▸
│       [Camera] ×4 ▸ Components: [CPU, Storage]
│     [Sensor] ×10 ▸ Components: [CPU, RAM]
│     [Gateway] ×2 ▸ Components: [CPU]
│     [Add or link existing]
├── [Group: "Rack B"] ▸ ...
├── [Standalone Device] ▸ Components: [...]
```

### Group card is read-only; mutations go through the edit panel

The group card is a read-only accordion view of its contents. No inline
"Add", "Link existing", or "Unlink" buttons inside the card. Instead, a
single **"Add or link existing"** button at the bottom of the group card
opens the group's **edit side panel**, which provides full control over
sub-groups, devices, and counts.

This keeps the card lightweight and avoids duplicating mutation UI that
the edit panel already handles.

### Group card internal layout

No explicit "Sub-groups" / "Devices" section labels inside the card.
Sub-groups always appear on top (visually distinguishable by their
accordion style, slightly different from device entries), followed by
devices below. The visual distinction + ordering makes labels unnecessary.

### Counts: inline editing

Each device/sub-group entry inside a group shows a count badge (e.g.
"×10"). Clicking it turns into an inline `<input type="number" min="1">`,
pre-filled with the current value. Saves on blur/Enter via HTMX.
Reverts on Escape.

### Unlink button

Each device/sub-group entry inside a group has an [✕] unlink button.
Clicking it removes the entry from the group's dict. If a device is no
longer in any group, it reappears in the ungrouped flat list.

### Component accordion preserved inside groups

Devices inside groups keep their component accordion, exactly like
standalone devices. This means nesting can reach: group > sub-group >
device > components (3-4 levels). This is acceptable for the typical
2-3 group depth.

### Grouped devices leave the flat list

When a device gets linked to any group, it disappears from the ungrouped
flat list. When removed from ALL groups, it reappears.

### Group membership in device edit panel

When editing an edge device via the side panel, a "Group membership"
section appears showing:
- Each group the device belongs to, with its current count
- Inline count edit per group
- A "Remove from group" button per entry

These are independent HTMX actions (not part of the main form).

---

## Detailed mockups

### 1. Group card (expanded)

```
┌─────────────────────────────────────────────────┐
│ ▸  Rack A                               [edit]  │
│                                                  │
│  ┌───────────────────────────────────────────┐   │
│  │ ▸  Shelf 1              ×[3]       [✕]    │   │
│  │   ┌───────────────────────────────────┐   │   │
│  │   │ ▸ Camera    ×[4]          [✕]    │   │   │
│  │   │   Components: [CPU] [Storage]    │   │   │
│  │   └───────────────────────────────────┘   │   │
│  └───────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────┐   │
│  │ ▸ Sensor        ×[10]             [✕]    │   │
│  │   Components: [CPU] [RAM]                │   │
│  │ ▸ Gateway        ×[2]             [✕]    │   │
│  │   Components: [CPU]                      │   │
│  └───────────────────────────────────────────┘   │
│                                                  │
│  [Add or link existing]                          │
└─────────────────────────────────────────────────┘
```

- No "Sub-groups" / "Devices" section labels
- Sub-groups on top, visually distinct (accordion style), devices below
- ×[count] clickable → inline number input (min 1), saves on blur/Enter
- [✕] removes entry from this group's dict
- [edit] and [Add or link existing] both open the group edit panel
- Device name clickable → opens device edit panel

### 2. Device entry inside a group (with component accordion)

```
┌──────────────────────────────────────────┐
│ ▸  Sensor       ×[10]             [✕]   │
│   Components                             │
│   ┌──────────────────────────────────┐   │
│   │ Edge CPU                         │   │
│   │ Edge RAM                         │   │
│   └──────────────────────────────────┘   │
│   [Add component]                        │
└──────────────────────────────────────────┘
```

- Device name clickable → opens device edit panel
- ×[count] clickable → inline number input (min 1)
- [✕] removes device from this group
- Component accordion works identically to standalone devices

### 3. Edge device edit panel with group membership

```
┌─ Side Panel: Edit "Sensor" ────────────────┐
│                                             │
│  [Regular form fields: name, type, ...]     │
│                                             │
│  ── Group membership ─────────────────────  │
│                                             │
│  Rack A                ×[10]    [Remove]    │
│  Shelf 2               ×[5]    [Remove]    │
│                                             │
│  [Calculated attributes accordion]          │
│                                             │
│  [Save]                                     │
└─────────────────────────────────────────────┘
```

Group membership entries are independent HTMX actions (not part of the
main form). Each count update or remove triggers its own request.

---

## Group creation form

The "Add group" side panel includes:
- Name field
- Sub-groups section: select_multiple-style picker (existing groups) with a
  count field per selected sub-group (default 1)
- Edge devices section: select_multiple-style picker (existing devices) with
  a count field per selected device (default 1)

On save, creates the group AND populates both dicts with the specified counts.
An empty group (no sub-groups, no devices) is allowed.

## Group edit panel

The "Edit group" side panel is very similar to the creation form:
- Name field (editable)
- Sub-groups section: same select_multiple pattern, allowing adding/removing
  sub-groups and editing counts inline
- Edge devices section: same pattern for devices
- Calculated attributes accordion at the bottom, same as other edit panels

## Group deletion

When a group is deleted:
- Its sub-groups become orphaned root groups (they can be manually relinked
  to another group later)
- Its devices become ungrouped if not in any other group
- A confirmation dialog explains this, akin to existing deletion dialogs

## Device and sub-group deletion

When an edge device is deleted:
- `DeleteObjectUseCase` removes it from all parent groups'
  `edge_device_counts` dicts before calling `self_delete()`
- If the device was the only entry in a group, the group becomes empty
  (which is allowed)

When a sub-group (EdgeDeviceGroup) is deleted:
- `DeleteObjectUseCase` removes it from all parent groups'
  `sub_group_counts` dicts before calling `self_delete()`
- Its own sub-groups become orphaned root groups (relinked manually later)
- Its own devices become ungrouped if not in any other group

This follows the same pattern as list-based relationships: the use case
handles unlinking before the domain object is deleted.

## Dict mutation endpoints

Three dedicated endpoints handle dict-based mutations, distinct from the
existing `edit-object` flow:

| Endpoint | Verb | Action |
|---|---|---|
| `/model_builder/update-dict-count/<parent_id>/<key_id>/` | POST | Update count: `parent.dict[key] = new_count` |
| `/model_builder/unlink-dict-entry/<parent_id>/<key_id>/` | POST | Remove entry: `del parent.dict[key]` |
| `/model_builder/link-dict-entry/<parent_id>/<key_id>/` | POST | Add entry: `parent.dict[key] = 1` (default count) |

The `parent_id` identifies the group. The `key_id` identifies the device
or sub-group. The view determines which dict (`edge_device_counts` or
`sub_group_counts`) based on the key object's type.

For `update-dict-count`, the new count is sent in the POST body.

All three endpoints trigger a `ModelingUpdate` through the
`ExplainableObjectDict` and return an HTMX response that re-renders
all root groups (OOB swap), consistent with the general HTMX update
strategy described below.

## Dict-count form widget

The group creation and edit panels use a new form widget inspired by
`select_multiple.html` but with per-entry count fields. Behavior:

- A dropdown shows only objects **not already** in the dict (same
  filtering as `select_multiple`)
- Clicking "Add" inserts the selected object with a default count of 1
- Each entry in the selected list shows: object name, an inline
  `<input type="number" min="1">` for the count, and a remove button
- The entire form (name + sub-groups with counts + devices with counts)
  is submitted as a single POST on save
- On edit, the widget is pre-populated with current dict entries and
  their counts

## Cycle prevention

Three layers of protection:

1. **Recursion guard in e-footprint (backend safety net):**
   `_find_root_groups()` and `_find_all_ancestor_groups()` must accept a
   `visited` set parameter to break cycles instead of infinitely recursing.
   Without this, a cycle would hang the process before any validation runs.

2. **`no_cycle_validation` calculated attribute in e-footprint:**
   Raises a clear error if a cycle is detected. Protects direct library
   users — not expected to trigger through the interface.

3. **View-layer filtering (interface guardrail):**
   The "Link existing sub-group" picker excludes:
   - The group itself
   - All ancestors of the group (direct and transitive)

## Drag-to-reorder

Group cards support drag-to-reorder via Sortable, same as edge devices
and servers. Order persistence to JSON is out of scope for this feature.

## Infrastructure column layout

Groups live in a dedicated `#edge-device-groups-list` container, separate
from `#edge-devices-list` (which holds ungrouped devices). Neither
container has a visible section label, consistent with how other
infrastructure sections (servers, external APIs) work today.
`#edge-device-groups-list` appears above `#edge-devices-list`.

## Top-level "Add edge device" button

Behavior unchanged when groups exist — always creates an ungrouped device.

## HTMX update strategy after dict mutations

After adding/removing a device or sub-group to/from a group:
- All root groups are re-rendered (OOB swap)
- If an edge device changed state from unlinked to linked (or vice versa),
  the corresponding ungrouped card is deleted (or re-rendered)
- `restoreAccordionStateInFragment` handles preserving accordion open/close
  state before swapping

This avoids fine-grained per-group targeting and keeps the logic simple.

## Count = 0

The backend allows count = 0 (non-negative validation). The interface
should enforce a minimum of 1 in the inline count input to avoid confusion.
To "mute" a device, the user should unlink it from the group instead.

---

## Backend differences from existing patterns

### Dict-based relationships (not list-based)

Existing child management uses `List[ChildType]`. Groups use
`ExplainableObjectDict` where each entry is `{object: count}`.

| Operation | How it works |
|---|---|
| Add device to group | `group.edge_device_counts[device] = SourceValue(count * u.dimensionless)` |
| Change count | Update `group.edge_device_counts[device]` |
| Remove device from group | `del group.edge_device_counts[device]` |
| Add sub-group | `group.sub_group_counts[sub_group] = SourceValue(count * u.dimensionless)` |

This requires new view endpoints distinct from the existing `edit_object`
flow, because:
- Dict entries need both a key (object reference) and a value (count)
- Dict mutations trigger modeling updates via `ExplainableObjectDict`
  `__setitem__` / `__delitem__`
- The existing form parsing (semicolon-separated IDs for lists) doesn't
  apply to dict relationships
