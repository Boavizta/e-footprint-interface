# Source metadata — feature spec

Let users attach two pieces of metadata to user-editable inputs in the
e-footprint model:

- **Confidence level** — `low`, `medium`, `high`, or unset (default).
- **Comment** — free-form text.

Both are per-value annotations, authored by the user in the interface, and travel
with the value through serialization, export, and display. Calculated (derived)
values are intentionally excluded — see §1.

Related work: this spec also introduces **source editing** in the interface —
previously the source line was read-only. See §4.

---

## 1. Scope

### In scope

- Confidence and comment on **user-editable inputs** (numerical, string, timezone,
  form-input timeseries).
- Source editing from the interface (name + link), bundled into the same editor as
  the comment.
- Persistence round-trip (session, download, upload).
- Display in edit forms, source table, and xlsx export.

### Out of scope

- Metadata (confidence or comment) on **calculated (derived) values**. They're
  audit artifacts; the user's judgement belongs on the inputs that feed them.
  Carrying comments across recomputation would require a non-trivial hook in
  `ModelingUpdate` to transfer state across `ExplainableObject` swaps, and the
  payoff doesn't justify it. Not ruled out for the future.
- Auto-derived confidence on calculated values (e.g. worst-of-ancestors).
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
| `confidence` | `Literal["low", "medium", "high"] \| None` | `None` | Set only on inputs. |
| `comment` | `str \| None` | `None` | Set only on inputs. No length limit enforced in the data model. |

Both attributes live on the `ExplainableObject` base class (default `None`) but
are only user-settable on inputs; they stay `None` on calculated values.

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
- A source picker: dropdown of `Source` instances **already referenced by at
  least one `ExplainableObject` in the current modeling**, plus
  `Sources.USER_DATA` and `Sources.HYPOTHESIS` appended if not naturally present
  (so the two sentinel origins are always available). Plus a "custom" option
  that reveals name + optional link fields.
- A comment textarea below.
- Save + cancel actions.

The dropdown is **not** a canonical list shared across modelings — it's derived
from the current system's own sources. This keeps the picker scoped to sources
the user has already chosen to cite, and avoids dumping the full `Sources`
registry on them.

**Same-form cross-field source sharing.** `available_sources` is server-rendered
at form load, so a custom source created in one field's editor is not in the
other fields' server-rendered dropdowns by default. To let users reuse a
freshly-minted source across siblings within the same submission:

- The client generates a stable id (e.g. 6-char random hex) at "Apply" time and
  writes it into the field's hidden `__source_id` input. It also injects the new
  source into the in-memory option list of every other source `<select>` in the
  same form, so siblings can pick it before Save.
- The server receives the same client-generated id from each field that picked
  the new source, and `_apply_metadata` deduplicates within the submission via a
  `pending_sources` dict keyed by that id, ensuring all fields end up referencing
  the *same* `Source` instance.

**Display when a comment is set:** below the source line, always visible, on one
expandable line using the existing truncating-text-tooltip pattern
(`components/truncating_text.html`). Click to expand to full text.

Picking a source from the dropdown does **not** pull in author-side metadata;
confidence and comment remain per-value on the `ExplainableObject`.

---

## 4. Source editing (new capability)

Today the source line in the interface is read-only — it just displays
`Source: user data` or the canonical name derived from whether the user overrode
the default. With this spec, the source line becomes user-editable via the editor
described in §3b.

Picking from the dropdown pins the value's `.source` to the selected `Source`
instance (the same Python object already used elsewhere in the modeling, or one
of the two sentinels). Free-entry creates a new `Source` on the value.

**Free-entry that collides with a canonical `Sources.*` name** — kept as a
distinct `Source` instance, with a quiet notice in the editor ("A canonical
source with this name already exists — if you want to use it, pick it from the
dropdown instead."). No auto-snap; the user stays in control.

---

## 5. Source table

`source_table.html` gains two new columns, inserted after the existing "Source"
column:

| Column | Content |
|---|---|
| Confidence | Badge (`low`/`medium`/`high`) or empty. |
| Comment | Truncating-text-tooltip. Click expands inline. |

Each row for an **input** is clickable (or has an explicit edit affordance) to
open the source+comment editor inline. Rows for calculated values render both
new columns as empty and are not editable.

---

## 6. Export

The "Export to xlsx" download gains two new columns — `confidence` and
`comment` — populated from the underlying `ExplainableObject`.

Interface-level JSON export/import (download → upload round-trip) preserves the
new fields via the existing `ModelWeb.to_json` persistence path.

---

## 7. Persistence

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
populates them as `None` — the data shape change is purely additive and fully
backward-compatible, so no migration and no version bump are required.

### Interface-side

No change to `interface_config` — the new fields live inside the system data,
carried by the efootprint serialization layer.

### Source deduplication on load — **must be resolved at implementation plan time**

In Python, many `ExplainableObject`s can (and normally do) share the same
`Source` instance by reference. At JSON serialization time each object writes
its source inline as `{"name": ..., "link": ...}`, so the download/upload
round-trip currently **loses object identity**: reloading a system produces N
distinct `Source` instances that merely happen to be equal by `name`/`link`.

This is not a new problem, but the source picker in §3b makes it visible — a
naive "list all sources used in the modeling" would return duplicates, and the
source table and xlsx export already walk sources with the same silent
duplication.

**Direction to pursue (to be confirmed during implementation planning):** fix
this at the deserializer rather than per-consumer. Thread a
`(name, link) → Source` registry through the JSON load path (e.g.
`json_to_system` / `ExplainableObject.from_json_dict`), seeded with the
`Sources.*` canonical singletons so reloaded data also re-identifies with the
Python constants. Each `from_json_dict` consults the registry before minting a
new `Source`. This restores the runtime invariant in one place and every
consumer — picker, source table, export — gets dedup for free.

The alternative (dedupe only when building the picker) is a symptom-level fix
and leaves the same duplication in every other consumer. Not recommended.

The implementation plan must explicitly commit to an approach and specify:

- where in the load path the registry is held and how it's scoped (per-load
  call, not a module global);
- whether canonical `Sources.*` singletons seed the registry (recommended: yes);
- the dedup key — `(name, link)` — and its handling of `None` links;
- test coverage that proves identity is restored across a full
  `to_json` → `from_json_dict` round-trip for sources shared across multiple
  `ExplainableObject`s.

---

## 8. Open questions (to resolve at implementation time)

- **Confidence badge visual design** — color palette per level, icon vs text-only.
  Minor; decide when the first widget is rendered.
- **Source editor form shape** — inline popover under the source line vs
  side-panel modal. The truncating comment line wants something non-modal.
- **Comment length cap in the UI** — no cap in the data model, but the textarea
  may want a soft cap (e.g. 2 000 chars) for layout sanity.

---

## 9. Touchpoints (non-exhaustive)

### e-footprint (library)

- `efootprint/abstract_modeling_classes/explainable_object_base_class.py` —
  `ExplainableObject.__init__`, `to_json`, `from_json_dict`. Also fix the
  hand-rolled source dict at the existing `to_json` site — call
  `self.source.to_json()` instead of inlining `{"name": ..., "link": ...}`.
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
  - `result/source_table.html` — two new columns, row edit affordance on input
    rows only.
- xlsx export view — add the two columns.
- Playwright E2E coverage for: set confidence, set comment, edit source, edit
  value with metadata present (confidence resets, comment persists), round-trip
  via download+upload.

---

## 10. Resuming from cold context

1. Read this file end to end.
2. Read `01-implementation-plan.md` (to be written) for ordered steps and test
   gates.
3. Re-read the two `CLAUDE.md` files (`e-footprint/CLAUDE.md` and
   `e-footprint-interface/CLAUDE.md`) for code-style and architecture constraints
   — in particular the Clean Architecture layering in the interface and the
   ExplainableObject serialization conventions in the library.
