# Card Order Persistence

## Goal

Persist the drag-and-drop ordering of object cards in the main modeling view so it survives:
- Page reload
- JSON export/import (download then re-upload)

Currently the order is maintained only in the DOM during a session and is lost on reload.

## Design decisions

- **Storage location**: `interface_config["card_order"]` alongside `sankey_diagrams` — same JSON file, same persistence path.
- **Save trigger**: On SortableJS `onEnd` only. DOM naturally tracks order during a session; the backend only needs to know the order when it re-renders the page from scratch (reload, import). Fire-and-forget POST on drag end.
- **All lists at once**: Each drag POST sends the full order of all 5 lists in one request. Avoids any partial-state problem and keeps the endpoint trivial.
- **Unknown/new IDs**: Objects not in the saved order (newly added) are appended at the end. Objects in the saved order that no longer exist are silently ignored. No cleanup needed.
- **Where ordering is applied**: In the `model_builder_main` view (adapter layer), not in `ModelWeb`. The view reads `interface_config["card_order"]`, sorts the object lists, and passes sorted lists explicitly as template context variables. `ModelWeb` stays domain-pure.
- **`external-api-list` fix**: This list exists in the template but is missing from `initSortableObjectCards()`. It gets added here.
- **SortableJS `dataIdAttr`**: Set to `"id"` so `sortable.toArray()` reads the existing `id="{{ object.web_id }}"` attribute without any template changes.

## JSON structure

```json
{
  "interface_config": {
    "sankey_diagrams": [...],
    "card_order": {
      "up-list":           ["UsagePattern_abc", "EdgeUsagePattern_xyz"],
      "uj-list":           ["UsageJourney_1", "UsageJourney_2"],
      "external-api-list": ["ExternalAPI_1"],
      "server-list":       ["Server_1", "Server_2"],
      "edge-devices-list": ["EdgeDeviceBase_1"]
    }
  }
}
```

IDs stored are `web_id` values (the `id` attribute of each card DOM element, matching `object.web_id` in templates).

## Implementation steps

### Step 1 — New endpoint `save_card_order`

**File**: `model_builder/adapters/views/views.py`

```python
import json as json_module

def save_card_order(request):
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    card_order = json_module.loads(request.body)
    repository.interface_config["card_order"] = card_order
    model_web.persist_to_cache()
    return HttpResponse(status=204)
```

**File**: `model_builder/urls.py`

```python
path("save-card-order/", views.save_card_order, name="save-card-order"),
```

### Step 2 — Update `initSortableObjectCards()` in JS

**File**: `theme/static/scripts/model_builder_main.js`

Add `dataIdAttr: "id"` to the shared options so `sortable.toArray()` reads card `id` attributes. Add `external-api-list` (currently missing). In `onEnd`, collect orders from all sortable instances and POST to the new endpoint.

Store the SortableJS instances so their `.toArray()` can be called after any drag:

```javascript
const sortableLists = {};

function initSortableObjectCards() {
    const listIds = ["up-list", "uj-list", "external-api-list", "server-list", "edge-devices-list"];
    const options = {
        dataIdAttr: "id",
        animation: 150,
        onStart: () => {
            document.querySelectorAll('.grabbing').forEach(el => el.classList.remove('grabbing'));
        },
        onEnd: () => {
            document.querySelectorAll('.grabbing').forEach(el => el.classList.remove('grabbing'));
            updateLines();
            saveCardOrder();
        }
    };

    listIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) sortableLists[id] = new Sortable(el, options);
    });
}

function saveCardOrder() {
    const order = {};
    Object.entries(sortableLists).forEach(([id, sortable]) => {
        order[id] = sortable.toArray();
    });
    fetch('/model_builder/save-card-order/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
                           ?? getCookie('csrftoken'),
        },
        body: JSON.stringify(order),
    });
}
```

Note: CSRF token must be available. Check how other `fetch` calls in the codebase access it (e.g., Sankey delete) and follow the same pattern. If the page does not include a CSRF token input, use the cookie-based helper `getCookie('csrftoken')` (already available or trivially added).

### Step 3 — Sorting helper in the view layer

**File**: `model_builder/adapters/views/views.py`

Add a module-level helper:

```python
def _sort_by_saved_order(objects, saved_ids: list) -> list:
    """Sort objects by saved web_id order; unknown IDs appended at end."""
    id_to_pos = {web_id: i for i, web_id in enumerate(saved_ids)}
    known = [o for o in objects if o.web_id in id_to_pos]
    unknown = [o for o in objects if o.web_id not in id_to_pos]
    return sorted(known, key=lambda o: id_to_pos[o.web_id]) + unknown
```

### Step 4 — Apply saved order in `model_builder_main` view

**File**: `model_builder/adapters/views/views.py`

In `model_builder_main`, after building `model_web`, read saved order and produce sorted lists:

```python
card_order = repository.interface_config.get("card_order", {})

context = {
    "model_web": model_web,
    "up_list_objects": _sort_by_saved_order(
        list(model_web.usage_patterns) + list(model_web.edge_usage_patterns),
        card_order.get("up-list", [])
    ),
    "uj_list_objects": _sort_by_saved_order(
        list(model_web.usage_journeys) + list(model_web.edge_usage_journeys),
        card_order.get("uj-list", [])
    ),
    "external_api_list_objects": _sort_by_saved_order(
        list(model_web.external_apis),
        card_order.get("external-api-list", [])
    ),
    "server_list_objects": _sort_by_saved_order(
        list(model_web.servers),
        card_order.get("server-list", [])
    ),
    "edge_devices_list_objects": _sort_by_saved_order(
        list(model_web.edge_devices),
        card_order.get("edge-devices-list", [])
    ),
}

http_response = htmx_render(request, "model_builder/model_builder_main.html", context=context)
```

### Step 5 — Update `model_builder_main.html` template

**File**: `model_builder/templates/model_builder/model_builder_main.html`

Replace the inline `{% for ... in model_web.xxx %}` loops with the pre-sorted context variables:

```html
<!-- up-list -->
<div id="up-list" class="list-group w-75 ps-0 pb-0">
    {% for object in up_list_objects %}
        {% include 'model_builder/object_cards/basic_card.html' %}
    {% endfor %}
</div>

<!-- uj-list -->
<div id="uj-list" class="list-group w-100 ps-0">
    {% for object in uj_list_objects %}
        {% include 'model_builder/object_cards/journey_card.html' %}
    {% endfor %}
</div>

<!-- external-api-list -->
<div id="external-api-list" class="list-group d-flex flew-column w-75 ms-25">
    {% for object in external_api_list_objects %}
        {% include 'model_builder/object_cards/basic_card.html' %}
    {% endfor %}
</div>

<!-- server-list -->
<div id="server-list" class="list-group d-flex flew-column w-75 ms-25">
    {% for object in server_list_objects %}
        {% include 'model_builder/object_cards/server_card.html' %}
    {% endfor %}
</div>

<!-- edge-devices-list -->
<div id="edge-devices-list" class="list-group d-flex flew-column w-75 ms-25">
    {% for object in edge_devices_list_objects %}
        {% include 'model_builder/object_cards/edge_device_card.html' %}
    {% endfor %}
</div>
```

Note: the template currently passes `with object=usage_pattern` etc. to the includes. Since `object` is the loop variable name, these `with` clauses are redundant once the loop variable is already named `object`. Verify the includes work without the `with` keyword — they should, since `object` is already in scope as the loop variable.

### Step 6 — Verify CSRF token availability for `fetch`

Check how the Sankey delete `fetch` call accesses the CSRF token in `sankey.js` and replicate the same pattern in `saveCardOrder`. If it uses `getCookie('csrftoken')`, that function must be available in `model_builder_main.js` scope. If needed, extract it to a shared utility or inline it.

## Edge cases

| Case | Behavior |
|---|---|
| No saved order (new model or first load) | `card_order` is `{}`, all `_sort_by_saved_order` calls get empty `saved_ids` → all objects go to `unknown` → natural model order preserved |
| New object added | HTMX appends its card to the list. On next reload, its `web_id` is absent from saved order → appended at end ✓ |
| Object deleted | Its `web_id` remains in `interface_config["card_order"]` until next drag, but is silently skipped by `_sort_by_saved_order` on reload ✓ |
| Import with no `card_order` | `interface_config` from imported file may lack `"card_order"` → `get("card_order", {})` returns `{}` → natural order ✓ |
| Import with saved `card_order` | Restored on render ✓ |
| Reboot to default model | `model_builder_main` redirects after reboot; on the subsequent GET, `interface_config` is from the default system data (likely no `card_order`) → natural order ✓ |

## Testing strategy

### Manual
1. Drag cards to a custom order; reload the page → verify order is preserved.
2. Export JSON; import it → verify order is restored.
3. Add a new object → reload → verify it appears at the end, other objects keep their order.
4. Delete an object → reload → verify remaining objects keep their order.
5. Drag in all 5 lists; reload → verify each list independently preserves order.

### Unit tests

1. **`_sort_by_saved_order`**: empty saved list returns original order; full saved list returns correct order; partial saved list puts unknowns at end; deleted IDs silently ignored.

2. **`save_card_order` view**: POST with valid JSON updates `repository.interface_config["card_order"]` and returns 204.

3. **`model_builder_main` view** context: with no saved order, context lists match natural model order; with saved order, context lists match saved order.

## Files changed

| File | Change |
|---|---|
| `model_builder/adapters/views/views.py` | Add `_sort_by_saved_order` helper, update `model_builder_main` context, add `save_card_order` view |
| `model_builder/urls.py` | Add `save-card-order/` URL |
| `model_builder/templates/model_builder/model_builder_main.html` | Use sorted context variables instead of `model_web.xxx` in the 5 list loops |
| `theme/static/scripts/model_builder_main.js` | Add `dataIdAttr: "id"`, add `external-api-list`, add `saveCardOrder()`, store Sortable instances in `sortableLists` |
