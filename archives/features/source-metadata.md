---
shipped: 1.4.0
date: 2026-05-06
repos: e-footprint (21.0.0), e-footprint-interface
---

# Source metadata

User-editable inputs gained two annotations — **confidence** (`low` / `medium` / `high` / unset) and **comment** (free-form text) — plus the ability to edit the **source** of a value from the interface (previously read-only). Both annotations live on `ExplainableObject`, travel through serialization, download/upload, and xlsx export, and surface in the edit form and source table.

## Why

Models in e-footprint mix high-confidence measurements, rough estimates, and outright placeholders, but the interface gave users no way to mark *which is which* or to leave a note explaining a value. Reviewers had to ask the author. Sources, the closest existing concept, identify *origin* — they don't capture per-value judgement, and two values citing the same source can legitimately disagree on confidence.

## Key decisions

- **Annotations live on `ExplainableObject`, not on `Source`.** Confidence and comment are statements about *this value's* use of a source, not about the source itself.
- **Calculated values don't carry metadata.** Carrying a comment across recomputation would need a hook in `ModelingUpdate` to transfer state across `ExplainableObject` swaps; the payoff didn't justify it. Re-open if user demand surfaces.
- **`Source` got an `id` and was lifted to a top-level `"Sources": {id: {...}}` block in the system JSON.** Replaced the inline `{"name", "link"}` shape, so identity now travels with the data. Each `ExplainableObject.to_json` emits `"source": "<source_id>"`. This fixed a long-standing dedup problem the picker would otherwise have made visible. Schema bump to library v21 with an `upgrade_version_20_to_21` handler.
- **Sentinels (`Sources.USER_DATA`, `Sources.HYPOTHESIS`) have hardcoded ids** (`"user_data"`, `"hypothesis"`) so they re-identify with the live Python singletons across processes. Other `Sources.*` constants get uuid-based ids and re-identify only within a single load.
- **Source resolution centralised in the loader.** Subclass `from_json_dict` overrides no longer touch sources — `_apply_json_source` runs after construction in `json_to_system`. Adding a new `ExplainableObject` subclass no longer means remembering source plumbing.
- **Comment persists across value edits; confidence resets.** Enforced server-side in the form-data parser, so client tampering can't bypass it.
- **In the source table, confidence and source/comment use intentionally different persistence shapes.** Confidence autosaves on each menu pick (single enum-bounded field, no Apply needed); source + comment bundle behind a single Apply (free-form, users want to compose before committing). In the side panel both ride the form's existing Save button — no per-widget autosave — because the user is already in an explicit edit session.
- **Custom sources are reusable across sibling fields in the same submission.** The client mints a stable id at Apply time and injects the new source into every other `<select>` in the form; the server dedupes via a `pending_sources` dict keyed by that id.
- **Source picker is scoped to the current modeling**, not the global `Sources` registry, plus the two sentinels appended unconditionally.

## Surprises

- The library's lazy `explain_nested_tuples` rehydration path also carries source refs, so `initialize_calculus_graph_data_from_json` had to thread `sources_dict` through alongside `flat_obj_dict`. Easy to miss; covered by a dedicated test.
- The interface's "source line" partial was originally derived client-side from "is this value different from default?" — replacing it with a server-rendered, live-backed widget meant rewriting `source.html` end to end, not extending it.

## Out of scope, may revisit

- Confidence / comment on calculated (derived) values.
- Auto-derived confidence on calculated values (e.g. worst-of-ancestors).
- Confidence / comment on canonical `Sources.*` singletons themselves.
- Bulk-editing metadata across many values at once.
- Surfacing metadata in the sankey diagram or emission charts.
- Comment length cap in the UI (no cap in the data model).

