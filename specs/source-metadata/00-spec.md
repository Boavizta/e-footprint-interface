# Source metadata — feature spec

Let users attach two pieces of metadata to any `ExplainableObject` in the e-footprint
model:

- **Confidence level** — `low`, `medium`, `high`, or unset (default).
- **Comment** — free-form text.

Both are per-value annotations, authored by the user in the interface, and travel
with the value through serialization, export, and display.

Related work: this spec also introduces **source editing** in the interface —
previously the source line was read-only. See §4.

---

## 1. Scope

### In scope

- Confidence and comment on **user-editable inputs** (numerical, string, timezone,
  form-input timeseries).
- Comment on **calculated (derived) values**, authored manually. No confidence on
  calculated values.
- Source editing from the interface (name + link), bundled into the same editor as
  the comment.
- Persistence round-trip (session, download, upload).
- Display in edit forms, source table, and xlsx export.

### Out of scope

- Auto-derived confidence on calculated values (e.g. worst-of-ancestors). Not ruled
  out for the future.
- Confidence / comment on canonical `Sources` singletons themselves. Those remain
  origin identifiers only.
- Bulk-editing metadata across many values at once.
- Surfacing metadata in the sankey diagram or emission charts.

---

## 2. Data model

Metadata lives on `ExplainableObject`, **not** on `Source`. Rationale: confidence
and comment are statements about *this value's* use of a source, not about the
source itself. Two values citing the same `Sources.ADEME_STUDY` can legitimately
carry different confidence levels and different comments.

New attributes on `ExplainableObject`:

| Attribute | Type | Default | Notes |
|---|---|---|---|
| `confidence` | `Literal["low", "medium", "high"] \| None` | `None` | Only meaningful on inputs. For calculated values, always `None`. |
| `comment` | `str \| None` | `None` | Free-form text. No length limit enforced in the data model. |

`Source` itself is unchanged.

### Edit behavior on value change

When a user edits the numeric value of an input that previously carried metadata:

- **Comment persists.** Free-form notes usually stay relevant across small value
  tweaks.
- **Confidence resets to `None`.** It's a judgement about a specific value; a new
  value needs a new judgement.

---

## 3. Form UI — inputs

Each editable input field gains two new affordances:

### 3a. Confidence badge (right of the field)

- Rendered inline to the right of the input — right of the unit field when a unit
  is present, right of the input itself otherwise.
- Default state: `None` — rendered as a neutral "Set confidence" affordance
  (faint, one-click to open).
- Set state: a colored badge (`low` / `medium` / `high`) that opens a select
  dropdown on click.
- One-click-to-edit, select-style interaction. No confirmation step beyond
  selecting a value.

### 3b. Source + comment line (below the field)

The existing source line becomes clickable and opens a source+comment editor.
Source and comment are saved together in one submit; the user does not need to
know that they land on different objects internally (`Source` vs
`ExplainableObject.comment`).

**Editor shape:**
- A source picker: dropdown of canonical Sources (`ADEME_STUDY`, `BASE_ADEME_V19`,
  etc.), plus a "custom" option. Selecting "custom" reveals name + optional link
  fields.
- A comment textarea below.
- Save + cancel actions.

**Display when a comment is set:** below the source line, always visible, on one
expandable line using the existing truncating-text-tooltip pattern
(`components/truncating_text.html`). Click to expand to full text.

Picking a canonical source does **not** pull in author-side metadata; confidence
and comment remain per-value on the `ExplainableObject`.

---

## 4. Source editing (new capability)

Today the source line in the interface is read-only — it just displays
`Source: user data` or the canonical name derived from whether the user overrode
the default. With this spec, the source line becomes user-editable via the editor
described in §3b.

A freshly picked canonical source pins the value's `.source` to that canonical
`Source` instance. Free-entry creates a new `Source` on the value.

---

## 5. Form UI — calculated values

Calculated (derived) values are not edited as form inputs. Users annotate them via:

- **Source table row** — each row gains a comment-edit affordance. Same editor as
  inputs, but the confidence control is not shown for calculated rows.
- **Calculated attribute explanation panel** — the side panel that explains a
  calculated attribute gains a comment-edit affordance.

Confidence is not settable on calculated values.

---

## 6. Source table

`source_table.html` gains two new columns, inserted after the existing "Source"
column:

| Column | Content |
|---|---|
| Confidence | Badge (`low`/`medium`/`high`) or empty. |
| Comment | Truncating-text-tooltip. Click expands inline. |

Each row is clickable (or has an explicit edit affordance) to open the
source+comment editor inline.

---

## 7. Export

The "Export to xlsx" download gains two new columns — `confidence` and
`comment` — populated from the underlying `ExplainableObject`.

Interface-level JSON export/import (download → upload round-trip) preserves the
new fields via the existing `ModelWeb.to_json` persistence path.

---

## 8. Persistence

### Library-side (`ExplainableObject.to_json` / `from_json_dict`)

Two new optional fields in the JSON payload for every explainable object:

```json
{
  "value": "...",
  "label": "...",
  "source": {"name": "...", "link": "..."},
  "confidence": "medium",
  "comment": "Cross-checked against internal audit 2025-Q4."
}
```

Both fields are omitted when `None`. Loading an old JSON without the fields
populates them as `None` — no migration strictly required for the data shape, but
the system version should bump so the upgrade handler is a clean no-op checkpoint
(see `e-footprint/efootprint/api_utils/version_upgrade_handlers.py`).

### Interface-side

No change to `interface_config` — the new fields live inside the system data,
carried by the efootprint serialization layer.

---

## 9. Open questions (to resolve at implementation time)

- **Confidence badge visual design** — color palette per level, icon vs text-only.
  Minor; decide when the first widget is rendered.
- **Source editor form shape** — inline popover under the source line vs
  side-panel modal. The truncating comment line wants something non-modal.
- **Carry-over of comments on calculated value recomputation** — when a calculated
  attribute is recomputed, a new `ExplainableObject` replaces the old one. The
  user's comment must survive that swap. Needs a hook in `ModelingUpdate` (or on
  the calculated-attribute update path) to transfer `comment` from the previous
  `ExplainableObject` to the new one. Confidence does not apply here.
- **Comment length cap in the UI** — no cap in the data model, but the textarea
  may want a soft cap (e.g. 2 000 chars) for layout sanity.
- **Free-entry canonical collision** — if a user types a free-form name that
  matches a canonical source's `name`, should we auto-snap to the canonical
  instance or keep it as a distinct `Source`? Recommend: distinct, with a quiet
  notice.

---

## 10. Touchpoints (non-exhaustive)

### e-footprint (library)

- `efootprint/abstract_modeling_classes/explainable_object_base_class.py` —
  `ExplainableObject.__init__`, `to_json`, `from_json_dict`. Also fix the
  hand-rolled source dict at the existing `to_json` site — call
  `self.source.to_json()` instead of inlining `{"name": ..., "link": ...}`.
- `efootprint/api_utils/version_upgrade_handlers.py` — version bump + no-op
  handler.
- Tests covering serialization round-trip, copy semantics, and edit-behavior (see
  §2).

### e-footprint-interface

- `model_builder/adapters/forms/form_field_generator.py` — emit the confidence
  badge payload on input fields; emit source-editor context.
- `model_builder/adapters/forms/form_data_parser.py` — parse `confidence` +
  `comment` submissions; apply the "carry comment, reset confidence on value
  change" rule.
- `model_builder/domain/object_factory.py` — propagate annotations into the
  `ModelingUpdate` path.
- Templates
  - `side_panels/dynamic_form_fields/source.html` — render the interactive
    source+comment line.
  - `side_panels/dynamic_form_fields/dynamic_form_field.html` — wire in the
    confidence badge slot.
  - A new partial for the confidence badge + its select dropdown.
  - A new partial for the source+comment editor.
  - `result/source_table.html` — two new columns, row edit affordance.
  - Calculated-attribute explanation panels — comment edit affordance.
- xlsx export view — add the two columns.
- Playwright E2E coverage for: set confidence, set comment, edit source, edit
  value with metadata present (confidence resets, comment persists), round-trip
  via download+upload.

---

## 11. Resuming from cold context

1. Read this file end to end.
2. Read `01-implementation-plan.md` (to be written) for ordered steps and test
   gates.
3. Re-read the two `CLAUDE.md` files (`e-footprint/CLAUDE.md` and
   `e-footprint-interface/CLAUDE.md`) for code-style and architecture constraints
   — in particular the Clean Architecture layering in the interface and the
   ExplainableObject serialization conventions in the library.
