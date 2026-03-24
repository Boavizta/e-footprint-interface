# Sankey Diagram Persistence

## Goal

Persist Sankey diagram configurations so they survive:
- Result panel close/reopen during a session
- JSON export/import (download then re-upload)

Currently all Sankey card settings are ephemeral — lost on panel close or page refresh.

## Design decisions

- **Clean Architecture**: The repository layer owns `interface_config`. `ModelWeb` stays pure efootprint domain — it never sees or touches `interface_config`.
- **Storage location**: `interface_config` lives as a top-level key inside the cached system data JSON (Redis + Postgres), alongside efootprint class keys.
- **No Django session storage**: `sankey_card_counter` is removed. Card IDs use short UUIDs (8-char hex).
- **In-RAM preservation**: `SessionSystemRepository` holds `_interface_config` in memory from init. `save_system_data` (renamed to `save_data`) merges it back into both `data` and `data_without_calculated_attributes` before writing. No extra cache round-trips, no separate `save_interface_config` method.
- **Single save path**: Both model edits and Sankey config changes go through the same `model_web.persist_to_cache()` method (renamed from `update_system_data_with_up_to_date_calculated_attributes`). This calls `to_json()` (fast) then `repository.save_data()`, which merges `_interface_config` before writing.
- **Versioning**: `efootprint_interface_version` top-level key enables future migrations of `interface_config` structure. Uses the interface package's `__version__` (synced with `pyproject.toml` via a test), mirroring e-footprint's pattern. Version bumped to `1.0.0` as part of this feature.
- **e-footprint core**: No changes needed. `json_to_system` iterates over known class names only, ignoring unknown top-level keys.

## JSON structure

```json
{
  "efootprint_version": "17.0.1",
  "efootprint_interface_version": "1.0.0",
  "interface_config": {
    "sankey_diagrams": [
      {
        "id": "a1b2c3d4",
        "lifecycle_phase_filter": "",
        "aggregation_threshold_percent": 1,
        "active_columns": ["phase", "1", "3", "4", "category", "7", "8"],
        "excluded_types": [],
        "display_column_headers": true,
        "node_label_max_length": 20
      }
    ]
  },
  "System": { "...": "..." },
  "Server": { "...": "..." }
}
```

## Implementation steps

### Step 1: Bump interface version to 1.0.0 and add `__version__`

**File**: `pyproject.toml`

Change `version = "0.14.5"` to `version = "1.0.0"`.

**File**: `e_footprint_interface/version.py` (new)

```python
__version__ = "1.0.0"
```

**File**: `e_footprint_interface/__init__.py`

```python
from .version import __version__
```

**File**: `tests/test_version_is_up_to_date.py` (new)

Mirror e-footprint's pattern:

```python
import unittest
import tomllib
from pathlib import Path

from e_footprint_interface import __version__


def get_version_from_pyproject():
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)
        return pyproject["tool"]["poetry"]["version"]


class TestVersion(unittest.TestCase):
    def test_version_is_up_to_date(self):
        self.assertEqual(get_version_from_pyproject(), __version__)
```

### Step 2: Hold `interface_config` in RAM in `ISystemRepository`

**File**: `model_builder/domain/interfaces/system_repository.py`

Add an `interface_config` property that reads from system data in memory. The interface doesn't add new abstract methods — the existing `get_system_data` / `save_system_data` contract is sufficient.

Add a concrete `get_interface_config` method:

```python
def get_interface_config(self) -> dict:
    """Retrieve interface_config from stored system data."""
    data = self.get_system_data()
    return data.get("interface_config", {}) if data else {}
```

Rename `save_system_data` to `save_data`:

```python
@abstractmethod
def save_data(
    self,
    data: Dict[str, Any],
    data_without_calculated_attributes: Optional[Dict[str, Any]] = None
) -> None:
    """Persist the system data and interface config.

    Implementations must merge self._interface_config into data before writing.
    """
    pass
```

### Step 3: `SessionSystemRepository` — RAM storage + merge on save

**File**: `model_builder/adapters/repositories/session_system_repository.py`

**On init/first read**: Capture `interface_config` from cached data into `self._interface_config`.

The current `__init__` doesn't read data — that happens lazily via `get_system_data()`. We have two options:
- Read eagerly at init (extra cache call on every request, even those that don't need system data)
- Capture on first `get_system_data` call

Better: capture lazily. Override `get_system_data_with_source` to store `_interface_config` as a side effect:

```python
def __init__(self, session: SessionBase):
    self._session = session
    self._cache_backend = CacheBackend()
    self._interface_config = None  # populated on first read

@property
def interface_config(self) -> dict:
    """In-RAM interface config. Populated after first get_system_data call."""
    if self._interface_config is None:
        return {}
    return self._interface_config

@interface_config.setter
def interface_config(self, value: dict):
    self._interface_config = value

def get_system_data_with_source(self):
    # ... existing logic ...
    # After successfully reading data from any source:
    if data is not None and self._interface_config is None:
        self._interface_config = data.get("interface_config", {})
    return data, source
```

**On save**: Merge `_interface_config` and `efootprint_interface_version` into both data dicts before writing:

```python
def save_data(self, data, data_without_calculated_attributes=None):
    # Merge interface config from RAM
    if self._interface_config is not None:
        from e_footprint_interface import __version__ as interface_version
        for d in (data, data_without_calculated_attributes):
            if d is not None:
                d["interface_config"] = self._interface_config
                d["efootprint_interface_version"] = interface_version

    # ... existing size check + cache write logic unchanged ...
```

No `key not in data` guard needed: `_interface_config` in RAM is always the authoritative source. If a view updated it (Sankey settings change), the new value is merged. If no view changed it, the original value is preserved.

### Step 4: `InMemorySystemRepository` — same pattern

**File**: `model_builder/adapters/repositories/in_memory_system_repository.py`

```python
def __init__(self, initial_data=None, max_payload_size_mb=None):
    self._data = deepcopy(initial_data) if initial_data else None
    self._max_payload_size_mb = max_payload_size_mb
    self._interface_config = self._data.get("interface_config", {}) if self._data else {}

@property
def interface_config(self) -> dict:
    return self._interface_config

@interface_config.setter
def interface_config(self, value: dict):
    self._interface_config = value

def save_data(self, data, data_without_calculated_attributes=None):
    if self._interface_config:
        from e_footprint_interface import __version__ as interface_version
        data["interface_config"] = self._interface_config
        data["efootprint_interface_version"] = interface_version

    # ... existing size check logic ...
    self._data = data
```

### Step 5: Rename `update_system_data_with_up_to_date_calculated_attributes` → `persist_to_cache`

**File**: `model_builder/domain/entities/web_core/model_web.py`

```python
def persist_to_cache(self):
    """Serialize current system state and persist to cache."""
    start = perf_counter()
    data_with_calculated_attributes = self.to_json(save_calculated_attributes=True)
    data_without_calculated_attributes = self.to_json(save_calculated_attributes=False)
    elapsed_ms = (perf_counter() - start) * 1000
    logger.info(f"Serialized system data in {round(elapsed_ms, 1)} ms.")
    self.repository.save_data(
        data_with_calculated_attributes,
        data_without_calculated_attributes=data_without_calculated_attributes
    )
```

**Update all callers** across the codebase. Search for `update_system_data_with_up_to_date_calculated_attributes` and replace with `persist_to_cache`. Also rename `save_system_data` → `save_data` in all callers.

### Step 6: Update `download_json` to include `interface_config`

**File**: `model_builder/adapters/views/views.py`

```python
from e_footprint_interface import __version__ as interface_version

def download_json(request):
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    system = model_web.system
    data = model_web.to_json(save_calculated_attributes=False)

    # Include interface config in export
    if repository.interface_config:
        data["interface_config"] = repository.interface_config
        data["efootprint_interface_version"] = interface_version

    json_data = json.dumps(data, indent=4)
    # ... rest unchanged ...
```

### Step 7: Update `upload_json` to preserve `interface_config`

**File**: `model_builder/adapters/views/views.py`

```python
def upload_json(request):
    repository = SessionSystemRepository(request.session)
    # ... file parsing ...

    if data and not import_error_message:
        try:
            # Extract interface_config before processing
            interface_config = data.get("interface_config", {})

            system_data = SessionSystemRepository.upgrade_system_data(data)
            import_service = ProgressiveImportService(...)
            system_data_with_calculated_attributes = import_service.import_system(system_data)
            model_web = ModelWeb(repository, system_data_with_calculated_attributes)

            # Set interface_config in RAM before persisting
            repository.interface_config = interface_config
            model_web.persist_to_cache()

            return redirect("model-builder")
        except Exception as e:
            # ... error handling unchanged ...
```

The key insight: `repository.interface_config = interface_config` sets the in-RAM value. The subsequent `persist_to_cache()` → `save_data()` merges it into the data before writing to cache. No separate save needed.

### Step 8: Add `interface_config` version upgrade infrastructure

**File**: `model_builder/version_upgrade_handlers.py`

```python
def upgrade_interface_config(config: dict, from_major_version: int) -> dict:
    """Apply interface_config migrations from from_major_version to current."""
    from e_footprint_interface import __version__ as interface_version
    current_major = int(interface_version.split(".")[0])
    for version in range(from_major_version, current_major):
        handler = INTERFACE_CONFIG_UPGRADE_HANDLERS.get(version)
        if handler:
            config = handler(config)
    return config

INTERFACE_CONFIG_UPGRADE_HANDLERS = {
    # Future: 1: upgrade_interface_config_v1_to_v2,
}
```

**In `ISystemRepository.upgrade_system_data`**, add `interface_config` upgrade after existing upgrades:

```python
@staticmethod
def upgrade_system_data(data):
    # ... existing efootprint version upgrades ...

    # Upgrade interface_config if present
    if "interface_config" in data:
        from e_footprint_interface import __version__ as interface_version
        from model_builder.version_upgrade_handlers import upgrade_interface_config
        current_major = int(interface_version.split(".")[0])
        json_interface_version = data.get("efootprint_interface_version", "0.14.5")
        json_major = int(json_interface_version.split(".")[0])
        if json_major < current_major:
            data["interface_config"] = upgrade_interface_config(
                data["interface_config"], json_major)
            data["efootprint_interface_version"] = interface_version

    return data
```

### Step 9: Simplify `sankey_form` to only create new cards

**File**: `model_builder/adapters/views/sankey_views.py`

`sankey_form` now only creates new cards with default settings and a fresh UUID. Restoring saved cards is handled entirely by `sankey_cards` (Step 10).

```python
import uuid

def sankey_form(request):
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    present_classes = _get_present_classes(model_web)

    card_id = uuid.uuid4().hex[:8]
    exclude_chips = _build_exclude_chip_list(EXCLUDABLE_CLASSES, present_classes)
    analyse_by_chips = _build_analyse_by_chips(present_classes)

    return render(request, "model_builder/result/sankey_card.html", {
        "card_id": card_id,
        "exclude_chips": exclude_chips,
        "analyse_by_chips": analyse_by_chips,
    })
```

Remove `sankey_card_counter` session usage entirely.

### Step 10: New endpoint to load all saved cards on panel open

**File**: `model_builder/adapters/views/sankey_views.py`

```python
from django.template.loader import render_to_string
from django.http import HttpResponse

def sankey_cards(request):
    """Return all saved Sankey cards, or a single default card if none saved."""
    repository = SessionSystemRepository(request.session)
    saved_diagrams = repository.interface_config.get("sankey_diagrams", [])

    if not saved_diagrams:
        # No saved config — fall back to single default card
        return sankey_form(request)

    # Render all saved cards in one response
    model_web = ModelWeb(repository)
    present_classes = _get_present_classes(model_web)
    cards_html = []

    for i, saved in enumerate(saved_diagrams):
        card_id = saved["id"]
        exclude_chips = _build_exclude_chip_list(EXCLUDABLE_CLASSES, present_classes)
        analyse_by_chips = _build_analyse_by_chips(present_classes)

        saved_active = set(saved.get("active_columns", []))
        for chip in analyse_by_chips:
            chip["active"] = chip["chip_id"] in saved_active
        saved_excluded = set(saved.get("excluded_types", []))
        for chip in exclude_chips:
            chip["active"] = chip["class_name"] in saved_excluded

        context = {
            "card_id": card_id,
            "exclude_chips": exclude_chips,
            "analyse_by_chips": analyse_by_chips,
            "initial_settings": saved,
        }
        cards_html.append(render_to_string(
            "model_builder/result/sankey_card.html", context, request=request))

    return HttpResponse("".join(cards_html))
```

Register the URL:

**File**: `model_builder/urls.py` (or wherever sankey URLs are defined)

```python
path("sankey-cards/", sankey_views.sankey_cards, name="sankey-cards"),
```

### Step 11: Update `sankey_section.html` to load saved cards

**File**: `model_builder/templates/model_builder/result/sankey_section.html`

Change the initial load from `sankey-form/` (single default card) to `sankey-cards/` (all saved cards):

```html
<div id="sankey-cards-container"
     hx-get="/model_builder/sankey-cards/"
     hx-trigger="load"
     hx-swap="innerHTML">
</div>
```

Note: `hx-swap` changes from `beforeend` to `innerHTML` because `sankey-cards` returns all cards at once.

The "Add another analysis view" button still points to `sankey-form/` (creates a new default card with a fresh UUID).

### Step 12: Update `sankey_card.html` to use saved values

**File**: `model_builder/templates/model_builder/result/sankey_card.html`

Pre-populate form fields from `initial_settings` context variable when present:

```html
<!-- Lifecycle phase dropdown -->
<select name="lifecycle_phase_filter">
    <option value="" {% if not initial_settings or initial_settings.lifecycle_phase_filter == "" %}selected{% endif %}>All phases</option>
    <option value="Manufacturing" {% if initial_settings and initial_settings.lifecycle_phase_filter == "Manufacturing" %}selected{% endif %}>Manufacturing only</option>
    <option value="Usage" {% if initial_settings and initial_settings.lifecycle_phase_filter == "Usage" %}selected{% endif %}>Usage only</option>
</select>

<!-- Aggregation threshold -->
{% with threshold=initial_settings.aggregation_threshold_percent|default:"1" %}
<input type="range" name="aggregation_threshold_percent" min="0" max="10" step="0.5"
       value="{{ threshold }}"
       oninput="this.nextElementSibling.textContent = this.value + '%'">
<span style="font-size: 13px; color: #555; min-width: 28px;">{{ threshold }}%</span>
{% endwith %}

<!-- Column headers checkbox -->
<input class="form-check-input" type="checkbox" name="display_column_headers"
       {% if not initial_settings or initial_settings.display_column_headers %}checked{% endif %}
       id="toggle-columns-{{ card_id }}">

<!-- Label length -->
<input type="number" name="node_label_max_length"
       value="{% if initial_settings %}{{ initial_settings.node_label_max_length }}{% else %}20{% endif %}"
       min="5" max="50" style="width: 70px;">
```

The chip toggles (analyse_by and excluded_types) are already handled in Step 9 via the `active` flag on each chip dict — no template changes needed for those.

### Step 13: Persist settings on every diagram render

**File**: `model_builder/adapters/views/sankey_views.py`

In `sankey_diagram`, after building the diagram, update `repository.interface_config` and call `model_web.persist_to_cache()`:

```python
def sankey_diagram(request):
    card_id = request.POST.get("card_id", "")
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    # ... existing diagram building logic ...

    # Persist this card's settings
    card_settings = {
        "id": card_id,
        "lifecycle_phase_filter": lifecycle_phase_str,
        "aggregation_threshold_percent": aggregation_threshold_percent,
        "active_columns": sorted(active_columns),
        "excluded_types": excluded_object_types,
        "display_column_headers": display_column_headers,
        "node_label_max_length": node_label_max_length,
    }
    config = repository.interface_config
    diagrams = config.setdefault("sankey_diagrams", [])

    # Find existing card by id and update, or append if new
    card_idx = next((i for i, d in enumerate(diagrams) if d["id"] == card_id), None)
    if card_idx is not None:
        diagrams[card_idx] = card_settings
    else:
        diagrams.append(card_settings)

    model_web.persist_to_cache()

    # ... existing render logic unchanged ...
```

### Step 14: Handle card deletion

**File**: `model_builder/adapters/views/sankey_views.py`

Add a new endpoint for deleting a card's persisted config:

```python
def sankey_delete_card(request):
    card_id = request.POST.get("card_id", "")
    repository = SessionSystemRepository(request.session)
    model_web = ModelWeb(repository)
    config = repository.interface_config
    diagrams = config.get("sankey_diagrams", [])
    config["sankey_diagrams"] = [d for d in diagrams if d["id"] != card_id]
    model_web.persist_to_cache()
    return HttpResponse("")
```

Register the URL and update the JS `sankeyRemoveCard` function to call this endpoint (via HTMX or fetch) before removing the card DOM element.

**File**: `theme/static/scripts/sankey.js`

```javascript
function sankeyRemoveCard(cardId) {
    // Persist deletion
    fetch('/model_builder/sankey-delete-card/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'card_id=' + cardId,
    });
    // Remove from DOM (existing logic)
    var card = document.getElementById('sankey-card-' + cardId);
    if (card) card.remove();
}
```

### Step 15: Handle "Add another analysis view" with persistence

When the user clicks "Add another analysis view", `sankey_form` is called without `card_index`, creating a new card with a fresh UUID and default settings. The settings are persisted on first diagram render (Step 13) when the form auto-submits via `hx-trigger="load, change delay:300ms"`.

No additional changes needed — the existing auto-submit flow handles this.

## Testing strategy

### Unit tests

1. **Version sync** (`tests/test_version_is_up_to_date.py`):
   - `__version__` matches `pyproject.toml` version

2. **Repository preservation** (`tests/unit_tests/adapters/repositories/`):
   - `save_data` merges `_interface_config` from RAM into data before writing
   - `interface_config` property returns empty dict when no data loaded
   - `interface_config` property returns stored config after data load
   - Setting `interface_config` property updates RAM state
   - Same tests for both `SessionSystemRepository` and `InMemorySystemRepository`

3. **Sankey views** (`tests/unit_tests/adapters/views/test_sankey_views.py`):
   - `sankey_form` with no saved config returns default card with UUID id
   - `sankey_form` with saved config pre-populates settings
   - `sankey_cards` with no saved config falls back to single default
   - `sankey_cards` with saved configs returns all cards
   - `sankey_diagram` persists card settings via `persist_to_cache`
   - `sankey_delete_card` removes card and persists

4. **Download/upload** (`tests/unit_tests/adapters/views/`):
   - `download_json` includes `interface_config` and `efootprint_interface_version` in output
   - `upload_json` sets `repository.interface_config` from uploaded file and persists
   - Upload of JSON without `interface_config` works (backward compatibility)

5. **Version upgrade**:
   - `upgrade_system_data` with no `interface_config` is a no-op
   - `upgrade_system_data` applies interface_config migrations when version is old

### E2E tests

Update `tests/e2e/test_sankey.py`:
- Create Sankey cards with custom settings, close result panel, reopen, verify settings restored
- Export JSON, import it, verify Sankey configs are restored

## Rename summary

| Old name | New name | Reason |
|---|---|---|
| `save_system_data` | `save_data` | Now saves both system data and interface config |
| `update_system_data_with_up_to_date_calculated_attributes` | `persist_to_cache` | Shorter, clearer intent |

## Files changed (summary)

| File | Change |
|---|---|
| `pyproject.toml` | Bump version to `1.0.0` |
| `e_footprint_interface/version.py` | New: `__version__ = "1.0.0"` |
| `e_footprint_interface/__init__.py` | Import `__version__` |
| `tests/test_version_is_up_to_date.py` | New: version sync test |
| `model_builder/domain/interfaces/system_repository.py` | Add `get_interface_config`, rename `save_system_data` → `save_data` |
| `model_builder/adapters/repositories/session_system_repository.py` | `_interface_config` in RAM, populate on read, merge on save, rename method |
| `model_builder/adapters/repositories/in_memory_system_repository.py` | Same pattern |
| `model_builder/domain/entities/web_core/model_web.py` | Rename `update_system_data_with_up_to_date_calculated_attributes` → `persist_to_cache` |
| `model_builder/version_upgrade_handlers.py` | Add `upgrade_interface_config`, `INTERFACE_CONFIG_UPGRADE_HANDLERS` |
| `model_builder/adapters/views/views.py` | `download_json` merges config, `upload_json` sets config on repository, rename calls |
| `model_builder/adapters/views/sankey_views.py` | Restore saved cards, persist settings, delete card endpoint, remove `sankey_card_counter` |
| `model_builder/urls.py` | Add `sankey-cards/` and `sankey-delete-card/` URLs |
| `model_builder/templates/model_builder/result/sankey_section.html` | Load from `sankey-cards/` instead of `sankey-form/` |
| `model_builder/templates/model_builder/result/sankey_card.html` | Accept `initial_settings` for pre-population |
| `theme/static/scripts/sankey.js` | `sankeyRemoveCard` calls delete endpoint |
| All files calling `save_system_data` | Rename to `save_data` |
| All files calling `update_system_data_with_up_to_date_calculated_attributes` | Rename to `persist_to_cache` |
