# Sankey Impact Repartition — Implementation Specification

## Overview

Add an "Impact repartition" section below the existing bar/line charts in the result panel. This section displays interactive Sankey diagrams powered by e-footprint's `ImpactRepartitionSankey` class, allowing users to explore how their system's CO2 footprint flows from the whole down to individual components. Users can tune every parameter of the Sankey analysis and add as many diagrams as they want to compare different perspectives.

**Reference mockup:** `sankey-interface-feature/sankey_mockup.html`

---

## 1. Architecture & Data Flow

### Server-side (Django)

**New view: `sankey_diagram(request)`**

- URL: `/model_builder/sankey-diagram/` (POST)
- Receives Sankey parameters as form data (see Section 4 for the full list)
- Reconstructs the system via `ModelWeb(SessionSystemRepository(request.session))`
- Instantiates `ImpactRepartitionSankey` with the received parameters, mapping UI class labels back to e-footprint class names
- Calls `build()`, then extracts:
  - **Plotly figure JSON** via `fig.to_json()` (with `display_column_information=False` since column headers are rendered as HTML)
  - **Column metadata** via `get_column_information()`, with class names mapped to UI labels using `ClassUIConfigProvider.get_label()`
  - **Title parts**: system name, total CO2 amount, lifecycle filter info, excluded types info
- Returns an HTML partial containing:
  - The HTML column headers (positioned using `x_center` from column metadata)
  - A `<div>` with the Plotly JSON embedded in a `data-plotly` attribute (or inline `<script>`)
  - The interaction hints overlay
  - A small JS snippet that calls `Plotly.newPlot()` on the container

**New view: `sankey_form(request)`**

- URL: `/model_builder/sankey-form/` (GET)
- Returns the settings panel HTML for a new Sankey card
- Pre-populates:
  - **Excluded object types chips**: only impact source classes (`is_impact_source is True`) present in the current system, with UI labels from `ClassUIConfigProvider`
  - **Skipped object types chips**: only classes present in the current system, with UI labels; defaults pre-selected (see Section 5)
- The available classes are determined from the keys of `model_web.response_objs` (a dict keyed by class name), filtered against the known excludable/skippable lists
- This keeps the form generation server-side (Django template) so the chip lists are always in sync with the actual modeling

### Client-side (JS)

- **Plotly.js** must be loaded. It is included in `base.html` via CDN `<script>` tag (loaded with the main page)
- **Card IDs**: Each Sankey card has a unique `card_id` (server-generated integer, starting at 1 for the first auto-generated card, incremented for each new card). This ID is used to build unique element IDs throughout the card: `sankey-card-{card_id}`, `settings-{card_id}`, `advanced-{card_id}`, `sankey-diagram-area-{card_id}`, `sankey-plot-{card_id}`, etc. The `card_id` is:
  - Generated server-side by `sankey_form()` (passed as template context, tracked via a session counter or a simple global counter)
  - Included as a hidden `<input name="card_id">` in each card's settings form
  - Echoed back by `sankey_diagram()` in the response so element IDs remain consistent after swap
- **Live update**: every settings control triggers a debounced (300ms) HTMX POST to `/model_builder/sankey-diagram/` with `hx-target="#sankey-diagram-area-{card_id}"` targeting that specific card's diagram area. Since there can be multiple cards on the page, the unique ID ensures the correct diagram is swapped.
- **Add card**: the "+ Add another analysis view" button sends an HTMX GET to `/model_builder/sankey-form/` to get a fresh card (with a new `card_id`) including settings panel + empty diagram area. The card is appended to `#sankey-cards-container` (use `hx-swap="beforeend"` with `hx-target="#sankey-cards-container"`). The first render is triggered immediately via the live update mechanism.
- **Remove card**: pure client-side JS (fade + remove from DOM)
- **Toggle settings**: pure client-side JS (show/hide), using the card-specific element IDs
- **Plotly rendering**: after HTMX swap, a small inline script or `htmx:afterSettle` listener calls `Plotly.newPlot()` on `#sankey-plot-{card_id}` with the embedded JSON data. Use `{ responsive: true, displayModeBar: false }` config.

### Rendering split: what's HTML vs. what's Plotly

| Element | Rendered by | Rationale |
|---------|-------------|-----------|
| Diagram title | HTML (card header) | Full styling control, uses UI labels |
| Column headers | HTML (positioned above plot) | Full styling control, uses UI labels from `ClassUIConfigProvider` |
| Sankey diagram | Plotly.js (client-side) | Interactive (drag nodes, hover tooltips) |
| Settings panel | Django template (server-side) | Chip lists depend on system's actual objects |

**Column header positioning:** The `get_column_metadata()` method returns `x_center` (0-1 normalized) for each column. Use these values as `left: <x_center * 100>%` with `transform: translateX(-50%)` on absolutely-positioned header tags within a `position: relative` container that matches the Plotly plot width. The Plotly layout margins (`l`, `r`) must be accounted for in the offset.

---

## 2. Template Structure

```
result_panel.html
├── (existing) result_graph.html (bar + line charts)
├── sankey_section.html                          ← NEW include
│   ├── onboarding banner (dismissible)
│   ├── #sankey-cards-container
│   │   └── sankey_card.html (repeated, each with unique card_id) ← NEW partial
│   │       ├── #sankey-card-{card_id}
│   │       ├── .sankey-card-header (title + subtitle + gear/delete buttons)
│   │       ├── #settings-{card_id} .sankey-settings (open by default)
│   │       │   ├── settings intro text
│   │       │   ├── hidden input: card_id
│   │       │   ├── main settings row (lifecycle, threshold, detail level)
│   │       │   ├── advanced toggle
│   │       │   └── #advanced-{card_id} advanced settings (excluded/skipped types, column headers, label length)
│   │       └── #sankey-diagram-area-{card_id}   ← HTMX swap target (unique per card)
│   │           ├── .sankey-column-headers (HTML, absolutely positioned)
│   │           └── #sankey-plot-{card_id} .sankey-plot-container (Plotly renders here)
│   │               └── .interaction-hint (bottom-right overlay)
│   └── "+ Add another analysis view" button
```

**The first card is auto-generated** when the result panel loads: the `sankey_section.html` template includes one `sankey_card.html` with default settings, and the initial diagram is rendered server-side in the same request (or triggered immediately via HTMX after settle).

---

## 3. ImpactRepartitionSankey Parameters — UI Mapping

The `figure()` method is called with `display_column_information=False` (column headers are rendered as HTML). The title is also not used from Plotly — it's rendered as HTML in the card header.

| `ImpactRepartitionSankey` param | UI control | UI label | Default | Help text |
|---|----|----|----|---|
| `lifecycle_phase_filter` | `<select>` dropdown | **Lifecycle phase** | `None` (All phases) | Focus on manufacturing (hardware production) or usage (energy consumption) impacts, or view both. |
| `aggregation_threshold_percent` | `<input type="range">` slider (0–10, step 0.5) | **Aggregation threshold** | `1.0` | Components below this share of total emissions are grouped into "Other" to reduce clutter. |
| `skip_phase_footprint_split` | Toggle (checkbox switch) | **Phase split** (under "Detail level") | `False` (checked = split enabled) | _Part of detail level description_ |
| `skip_object_category_footprint_split` | Toggle | **Category split** | `False` (checked) | _Part of detail level description_ |
| `skip_object_footprint_split` | Toggle | **Object split** | `False` (checked) | _Part of detail level description_ |
| `excluded_object_types` | Chip multi-select (red when active) | **Excluded object types** | `[]` (none excluded) | Completely remove these hardware types from the analysis. Their impact will not appear in the diagram at all. |
| `skipped_impact_repartition_classes` | Chip multi-select (blue when active) | **Skipped object types** | See Section 5 | These object types won't appear as their own nodes. Instead, their children are connected directly to their parent. Useful to simplify the diagram by removing intermediate levels. |
| `display_column_information` | Toggle | **Column headers** | Always `False` for Plotly figure (HTML rendering handles this) | _The toggle controls whether the HTML column headers are shown_ |
| `node_label_max_length` | `<input type="number">` (5–50) | **Label max length** | `15` | Truncate long node names to keep the diagram readable. |

**Note on `display_column_information`:** The Plotly figure is always generated with `display_column_information=False` to avoid Plotly annotations. The "Column headers" toggle in the UI controls whether the HTML column headers (rendered from `get_column_information()`) are shown or hidden. The column metadata is always fetched server-side regardless of this toggle, since it's cheap. This toggle simply adds/removes the HTML column header bar.

**Note on toggle semantics:** The UI toggles are phrased positively ("Phase split" = enabled when checked). The `ImpactRepartitionSankey` params are phrased as `skip_*` (negative). So: `skip_phase_footprint_split = NOT checkbox.checked`.

### Detail level help text

Displayed below the three toggles as a single `setting-desc`:
> Control how many breakdown levels appear. "Phase" splits manufacturing vs. usage. "Category" groups by object type (servers, devices...). "Object" shows individual components.

---

## 4. Settings Panel Layout

### Main settings (always visible when panel is open)

Displayed as a horizontal flex row wrapping on smaller screens:

1. **Lifecycle phase** — dropdown (`All phases` / `Manufacturing only` / `Usage only`)
2. **Aggregation threshold** — range slider with live percentage label
3. **Detail level** — three toggle switches in a row

A **settings intro** line appears above:
> Adjust these settings to explore different perspectives of your system's environmental impact. Changes are applied instantly.

### Advanced settings (collapsed by default, toggle via "Advanced options" link)

1. **Excluded object types** — chip multi-select, red highlight when active
2. **Skipped object types** — chip multi-select, blue highlight when active
3. **Column headers** — toggle (show/hide)
4. **Label max length** — number input

Each setting has a `setting-desc` line below it explaining what it does (see Section 3 table for the texts).

---

## 5. Default Skipped Classes

When a new Sankey card is created, the following classes are **pre-selected as skipped** (if they are present in the current system's modeling):

- `UsagePattern`
- `EdgeUsagePattern`
- `JobBase`
- `RecurrentEdgeDeviceNeed`
- `RecurrentServerNeed`
- `RecurrentEdgeComponentNeed`

These defaults produce a clean diagram that flows from system → lifecycle phases → object categories → individual hardware, which is the most intuitive starting view.

**The skipped and excluded chip lists only show classes actually present in the current modeling.** This is determined server-side by inspecting `model_web.system` and collecting the `class_as_simple_str` of all objects in the dependency tree. The Django template iterates over this filtered list.

---

## 6. Excluded Object Types — Available Classes

Only classes where `is_impact_source` is `True` can be excluded. The full set of excludable classes is:

- `Device`
- `EdgeDevice`
- `Network`
- `ServerBase` (covers Server, GPUServer, etc. via `isinstance`)
- `ExternalAPI` (covers subclasses via `isinstance`)
- `Storage`
- `EdgeStorage`

As with skipped types, **only those present in the current modeling are shown** as chips. The chip label uses `ClassUIConfigProvider.get_label()` for user-friendly names.

---

## 7. Card Title

The card title is rendered as HTML in `.sankey-card-header` with two lines:

- **Title**: `"{system.name} — {lifecycle_info}impact repartition{excluded_info}: {total_co2} CO2eq"`
  - `lifecycle_info`: `"manufacturing "` or `"usage "` if filtered, empty otherwise
  - `excluded_info`: `" excluding {comma-joined UI labels}"` if types are excluded, empty otherwise
  - `total_co2`: formatted amount from the built Sankey (using `display_co2_amount`)
- **Subtitle**: `"All phases"` / `"Manufacturing only"` / `"Usage only"`

The title is generated server-side and included in the diagram area response so it updates on every setting change.

---

## 8. Column Headers

Rendered as HTML elements **above** the Plotly diagram, positioned to align with the Sankey columns:

- Server returns `get_column_information()` with each entry containing:
  - `column_type`: `"manual_split"` (e.g., "Life cycle phase", "Object category") or `"impact_repartition"` (class names)
  - `x_center`: normalized 0–1 position from `get_column_metadata()`
  - `class_names`: list of class names (for impact_repartition columns)
- For `manual_split` columns: display the `description` field
- For `impact_repartition` columns: display UI labels from `ClassUIConfigProvider.get_label()`, one per line
- Styled as small bordered tags (see mockup `.column-header-tag` class)

**Alignment strategy:**
- The column header container is `position: relative` with the same horizontal padding as the Plotly plot margins
- Each header tag is `position: absolute; left: {x_center * 100}%; transform: translateX(-50%)`
- The Plotly layout uses fixed `margin.l` and `margin.r`; the header container uses matching `padding-left` and `padding-right`

---

## 9. User Guidance

Three layers, from most to least prominent:

### 9a. Onboarding banner (top of section, dismissible)

Shown once at the top of the Sankey section. Dismissible via X button. Consider persisting dismissal in `localStorage` so it doesn't reappear on every result panel open.

Content:
> **Sankey diagrams** show how your system's total CO2 footprint flows from the whole down to individual components. The width of each flow is proportional to its share of emissions. Use the settings to change the analysis angle — filter by lifecycle phase, adjust detail level, or exclude specific object types.
>
> _You can also drag nodes to rearrange the diagram, and hover over flows to see details._

### 9b. Settings intro + per-setting descriptions

- **Settings intro** (blue left border bar): "Adjust these settings to explore different perspectives of your system's environmental impact. Changes are applied instantly."
- **Per-setting `setting-desc`** text below each control (see Section 3 for all texts)

### 9c. Interaction hints (bottom-right of diagram)

Subtle, non-interactive hints:
- "Drag nodes to rearrange" (with hand icon)
- "Hover flows for details" (with question mark icon)

Consider fading these out after the user's first interaction with the diagram.

---

## 10. Live Update

**No Apply button.** Every settings change triggers a live update:

- All controls (`select`, `input[type=range]`, `input[type=checkbox]`, `input[type=number]`, chip clicks) call a debounced update function (300ms delay)
- The update sends an HTMX POST to `/model_builder/sankey-diagram/` with the card's current settings
- The response replaces `.sankey-diagram-area` (column headers + Plotly container + interaction hints)
- The card title is also updated in the response
- A loading state (spinner or subtle opacity reduction) should be shown during the request

**HTMX implementation detail:** Each card's settings form should have `hx-post="/model_builder/sankey-diagram/"` with `hx-target="#sankey-diagram-area-{card_id}"` (unique per card, see Section 1 for card ID strategy), `hx-trigger="change delay:300ms, input delay:300ms from:find input[type=range]"`. Chip clicks need a small JS helper to toggle the chip class and then trigger the HTMX request (e.g., via `htmx.trigger(form, 'change')`). A hidden `<input name="card_id" value="{card_id}">` is included in the form so the server can echo it back in the response, keeping element IDs consistent across swaps.

---

## 11. Adding & Removing Cards

### Adding

- The "+ Add another analysis view" button sends an HTMX GET to `/model_builder/sankey-form/`
- The server returns a complete new card (settings + empty diagram area) with default settings
- The card is appended to `#sankey-cards-container` (use `hx-swap="beforeend"` on the container, or `hx-target="#sankey-cards-container"`)
- Settings panel is open by default
- Immediately after insertion, the live update mechanism fires to generate the initial diagram with default settings
- Smooth scroll to the new card

### Removing

- The X button on each card removes it from the DOM (client-side only, no server request)
- Fade-out animation (opacity 0, slight translateY, then remove after 200ms)
- There's no minimum card count — the user can remove all cards

---

## 12. Mobile & Responsive Considerations

### Landscape encouragement

Sankey diagrams need horizontal space. On mobile in portrait mode, display a subtle banner suggesting landscape orientation:

```html
<div class="sankey-landscape-hint">
    <svg><!-- rotate phone icon --></svg>
    Rotate your device for a better view of the diagram
</div>
```

- Show only when `window.innerWidth < 768` **and** `orientation === 'portrait'` (use `matchMedia('(orientation: portrait)')`)
- Hide automatically when the user rotates to landscape
- Dismissible (the user may prefer portrait)
- This pattern doesn't exist in the interface yet, so it would be a new component. Keep it simple and self-contained.

### Responsive layout

- **Settings row**: already uses `flex-wrap: wrap`, so controls stack vertically on small screens. No special handling needed.
- **Chip selects**: naturally wrap. On very small screens, consider a smaller chip size.
- **Plotly diagram**: uses `responsive: true` so it adapts to container width. Set a reasonable `min-height` (300px mobile, 400px desktop).
- **Column headers**: on narrow screens, they may overlap. Consider hiding them automatically below a certain width threshold, or reducing font size.
- **Interaction hints**: hide on touch devices (no hover) — replace "Hover flows" with "Tap flows for details".

### Sankey plot sizing

- The Plotly layout should use `width: undefined` (let responsive mode handle it) with `height` proportional to the container width (e.g., `Math.max(350, containerWidth * 0.4)`)
- Set `margin: { t: 10, b: 30, l: 20, r: 20 }` (minimal top margin since title/column headers are external HTML)

---

## 13. e-footprint Changes

### Minor: Ensure `figure()` / `build()` work cleanly with `display_column_information=False`

This should already work. Verify that `get_column_information()` and `get_column_metadata()` still return data even when `display_column_information=False` (they should — the flag only controls Plotly annotation generation in `figure()`).

### Consider: Add a `to_plotly_json()` convenience method

To avoid the overhead of generating the full Plotly figure (with layout/title/annotations we don't need) and then extracting just the data, consider adding a method that returns just the Sankey `data` dict (nodes + links) without calling `figure()`. This would be more efficient for the web use case. However, this is an optimization — the initial implementation can use `figure(display_column_information=False).to_json()` and strip the unwanted parts.

### Consider: expose `_total_system_kg` or a summary method

The title needs the total CO2 amount. Currently `_total_system_kg` is private. Either:
- Make it a public property (`total_system_kg`)
- Or add a `summary()` method returning title parts

This would avoid having to parse it out of the title string. A simple `@property` exposing `_total_system_kg` after `build()` would suffice.

---

## 14. Dependencies

- **Plotly.js**: Required for rendering. Load with the main page via CDN in `base.html` (`https://cdn.plot.ly/plotly-2.27.0.min.js` or latest stable). No lazy-loading — Plotly is central to the tool.
- **No new Python dependencies**: `ImpactRepartitionSankey` is already in e-footprint. Plotly is already an e-footprint dependency (used by `figure()`).

---

## 15. File Inventory (new/modified)

### New files (interface)

| File | Purpose |
|------|---------|
| `templates/model_builder/result/sankey_section.html` | Section wrapper: onboarding banner + cards container + add button |
| `templates/model_builder/result/sankey_card.html` | Single card: header + settings + diagram area |
| `templates/model_builder/result/sankey_diagram.html` | Diagram area partial (column headers + Plotly container): the HTMX swap target |
| `adapters/views/sankey_views.py` | `sankey_diagram()` and `sankey_form()` views |
| `theme/static/scripts/sankey.js` (or TS) | Client-side: card management, chip toggles, live update wiring, Plotly rendering |
| `theme/static/scss/_sankey.scss` | Sankey-specific styles (card, settings, chips, column headers, hints) |

### Modified files (interface)

| File | Change |
|------|--------|
| `templates/model_builder/result/result_panel.html` | Add `{% include 'model_builder/result/sankey_section.html' %}` inside `#graph-block`, after `result_graph.html` |
| `templates/model_builder/result/result_graph.html` | Possibly: wrap existing charts in their own container to keep them visually separated from the sankey section |
| `adapters/views/views.py` or `urls.py` | Register new URL routes for `sankey-diagram` and `sankey-form` |
| `theme/templates/base.html` | Add Plotly.js CDN `<script>` tag |

### Possibly modified files (e-footprint)

| File | Change |
|------|--------|
| `efootprint/utils/impact_repartition/sankey.py` | Expose `total_system_kg` as a public property. Potentially add a `to_plotly_json()` convenience method. |

---

## 16. Known Gotchas & Edge Cases

### Chip state serialization

Chips use CSS classes (`active` / `active-exclude`) to track state, but HTMX only submits native form elements (`<input>`, `<select>`, `<textarea>`). **Chip state will be silently lost unless explicitly serialized.** Each chip has a corresponding hidden `<input type="hidden" name="skipped_classes" value="UsagePattern">` (or `name="excluded_types"`) that is added/removed when the chip is toggled. This way HTMX naturally submits them as a multi-value field. The JS chip toggle function must both toggle the CSS class and add/remove the hidden input.

### HTMX request races

Rapid setting changes can queue concurrent requests. A slow response could overwrite a newer result. **Use `hx-sync="replace"` on each card's form** so HTMX automatically aborts in-flight requests when a new one fires for the same form.

### Plotly memory cleanup

When HTMX swaps the diagram area, the old Plotly instance's WebGL context and event listeners are not cleaned up. Over time (with many re-renders), this leaks memory. **Add an `htmx:beforeSwap` listener** that calls `Plotly.purge(plotElementId)` on the outgoing element before replacement.

### Column header alignment

Plotly can auto-adjust margins even with explicit settings (e.g., if long labels overflow). If margins shift, HTML column headers will be misaligned. **Set Plotly layout `automargin: false`** on axes, and use fixed `margin: { t: 10, b: 30, l: 20, r: 20 }`. The HTML header container must use matching padding.

### Plotly.js loading

Load Plotly.js with the main page (in `base.html`) since it is central to using the tool. No lazy-loading needed. Use CDN: `https://cdn.plot.ly/plotly-2.27.0.min.js` (or latest stable).

### String class names for ImpactRepartitionSankey params

`skipped_impact_repartition_classes` and `excluded_object_types` accept both `type[ModelingObject]` and `str`. **Use string class names** (e.g., `"UsagePattern"`, `"ServerBase"`) in form data — `ImpactRepartitionSankey` already resolves strings to classes internally. This avoids needing to import and map class types in the view.

### Detecting classes present in the modeling

To populate chip lists, the server needs to know which classes exist in the current system. **Use the keys of `model_web.response_objs`** — this is a dict keyed by class name (e.g., `"Server"`, `"UsagePattern"`, `"Device"`, etc.) containing the objects of each type. Filter these keys against the known excludable/skippable class lists to determine which chips to render.

### System reconstruction cost

Each live update reconstructs the system via `ModelWeb(SessionSystemRepository(request.session))`. This is the same pattern used by `result_chart()` and is acceptable.

---

## 17. Implementation Order

Suggested order for a coding agent to minimize blocked work:

1. **e-footprint changes** (small, unblocks everything):
   - Expose `total_system_kg` as a public property
   - Verify `get_column_metadata()` / `get_column_information()` work after `build()` with `display_column_information=False`

2. **Django views** (`sankey_views.py`):
   - `sankey_diagram()`: takes params, builds Sankey, returns diagram partial
   - `sankey_form()`: returns a new card with settings pre-populated from system
   - Register URL routes

3. **Templates**:
   - `sankey_diagram.html` (the HTMX swap target — column headers + Plotly container)
   - `sankey_card.html` (full card with settings form + diagram area)
   - `sankey_section.html` (section wrapper with onboarding banner + add button)
   - Integrate into `result_panel.html`

4. **CSS** (`_sankey.scss`):
   - Card, settings, chip, column header, and hint styles
   - Mobile/responsive rules and landscape hint

5. **JavaScript** (`sankey.js`):
   - Chip toggle + hidden input sync
   - Plotly rendering after HTMX swap (`htmx:afterSettle`)
   - Plotly cleanup before swap (`htmx:beforeSwap`)
   - Card add/remove/toggle interactions
   - Onboarding banner dismissal (with `localStorage` persistence)

6. **Plotly.js integration**:
   - Add CDN `<script>` tag in `base.html`
