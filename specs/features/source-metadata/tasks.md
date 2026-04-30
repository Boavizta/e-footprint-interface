# Source metadata — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.md`](spec.md). **Plan:** [`plan.md`](plan.md).

Two repos involved. Tasks 1–2 land in `e-footprint` (library, PyPI). Tasks 3–8 land in `e-footprint-interface`. Library tasks must publish before the interface pins to the new version, but interface work can proceed against the local editable path during development.

---

## Task 1 — Library: Source id + top-level "Sources" block + upgrade handler (v21.0.0)

**Status:** Done.

**Goal:** Restructure the library JSON so `Source` is a top-level entity with a deterministic id, and every `ExplainableObject.source` serializes as a string id-ref. Centralize source resolution in the loader. Migrate existing v20 JSONs forward via an upgrade handler. Schema bump to v21.0.0. No `confidence`/`comment` yet.

**Files touched (e-footprint):**
- `efootprint/abstract_modeling_classes/explainable_object_base_class.py` — `Source` gains `_use_name_as_id: bool = False` class flag; `__init__` sets `self.id = css_escape(name) if Source._use_name_as_id else str(uuid.uuid4())[:6]`, with optional explicit `id=` kwarg for sentinels; empty-string `link` normalised to `None`. `Source.to_json` emits `{"id", "name", "link"}`; `Source.from_json_dict` reads the id. New module-level helper `_apply_json_source(obj, json_dict, sources_dict)` resolves source by id-ref against `sources_dict`. Base `to_json` emits `"source": "<source_id>"` instead of inline dict. `initialize_calculus_graph_data_from_json` accepts and persists `sources_dict` for lazy `explain_nested_tuples` rehydration.
- `efootprint/abstract_modeling_classes/explainable_quantity.py`, `explainable_hourly_quantities.py`, `explainable_recurrent_quantities.py`, `explainable_timezone.py` — drop the `Source.from_json_dict(d.get("source"))` line and stop passing `source` to `cls(...)` in their `from_json_dict`; source is applied centrally.
- `efootprint/builders/timeseries/explainable_hourly_quantities_from_form_inputs.py`, `explainable_recurrent_quantities_from_constant.py` — same.
- `efootprint/constants/sources.py` — `Sources.USER_DATA` and `Sources.HYPOTHESIS` constructed with explicit `id="user_data"` / `id="hypothesis"`.
- `efootprint/api_utils/system_to_json.py` — walk all `ExplainableObject`s, collect distinct `Source` instances by id, emit a top-level `"Sources": {id: source.to_json()}` block before the modeling-class blocks. Emit only sources actually referenced.
- `efootprint/api_utils/json_to_system.py` — pre-pass: read `system_dict["Sources"]`, build `sources_dict = {id: Source.from_json_dict(d)}`; substitute live Python singletons for the two sentinel ids. After every `ExplainableObject` constructed (main loop and `ExplainableObjectDict` post-pass), call `_apply_json_source(obj, json_dict, sources_dict)`. Pass `sources_dict` into `initialize_calculus_graph_data_from_json`.
- `efootprint/api_utils/version_upgrade_handlers.py` — new `upgrade_version_20_to_21(system_dict, ...)`: walk every `ExplainableObject` payload (including `explain_nested_tuples` carriers), collect distinct inline source dicts, hoist to a top-level `"Sources"` block keyed by computed id, rewrite each `"source"` field to the id ref. Register in `VERSION_UPGRADE_HANDLERS`.
- `pyproject.toml` (library) — bump `version` to `21.0.0`.
- `CHANGELOG.md` — major-version entry: schema change, source dedup at the deserializer.
- `conftest.py` (library tests) — flip `Source._use_name_as_id = True` for deterministic test ids.

**Tests added/changed (e-footprint):**
- `tests/abstract_modeling_classes/test_explainable_object_base_class.py` (and adjacent subclass tests) — round-trip with the new id-ref shape; subclass `from_json_dict` no longer constructs Sources directly.
- `tests/api_utils/test_json_to_system.py` —
  - top-level `"Sources"` block round-trips;
  - source identity restored across `to_json` → `from_json_dict` for sources shared by multiple `ExplainableObject`s;
  - canonical `Sources.USER_DATA` and `Sources.HYPOTHESIS` are re-identified by id on reload (Python `is` check);
  - sentinel id strings (`"user_data"`, `"hypothesis"`) pinned by an explicit assertion — they are part of the on-disk schema;
  - `upgrade_version_20_to_21` correctly migrates a frozen v20 fixture;
  - one round-trip over every concrete `ExplainableObject` subclass to prove no load path drops the source ref;
  - one test for the lazy `explain_nested_tuples` path resolving refs after load.
- `tests/api_utils/fixtures/v20_system.json` (new) — frozen v20 system JSON spanning all `ExplainableObject` subclasses.

**Acceptance:**
- `to_json` → `from_json_dict` round-trip yields one `Source` instance per id (Python identity), shared by every `ExplainableObject` referencing it.
- `Sources.USER_DATA` / `Sources.HYPOTHESIS` re-identify with the live singletons across reload.
- Loading the frozen v20 fixture via `json_to_system` produces an in-memory result equivalent to one freshly built from current code paths.
- Sentinel id strings unchanged from those declared above.
- All existing library tests pass.

**Depends on:** none.

---

## Task 2 — Library: `confidence` + `comment` on `ExplainableObject` (v21.0.0)

**Status:** Done.

**Goal:** Add the two new per-value annotations to `ExplainableObject`. Purely additive on top of Task 1.

**Files touched (e-footprint):**
- `efootprint/abstract_modeling_classes/explainable_object_base_class.py` —
  - `ExplainableObject.__init__` gains `confidence: Literal["low", "medium", "high"] | None = None` and `comment: str | None = None`;
  - both attrs propagate through `__copy__`;
  - base `to_json` emits both fields when not `None`, omits otherwise;
  - extend `_apply_json_source` → `_apply_json_metadata(obj, json_dict, sources_dict)` to also set `confidence` / `comment` from the json dict;
  - missing fields read as `None` (purely additive at read time).
- `pyproject.toml` (library) — version stays `21.0.0` (folded into the same major release as Task 1).
- `CHANGELOG.md` — added to the `21.0.0` entry.

**Tests added/changed (e-footprint):**
- `tests/abstract_modeling_classes/test_explainable_object_base_class.py` —
  - default `None` for both fields;
  - round-trip with both fields set on a representative subclass;
  - `__copy__` propagates both fields;
  - loading old-shape JSON (no `confidence`/`comment` keys) yields `None`.
- Extend the all-subclass round-trip in `tests/api_utils/test_json_to_system.py` to also set `confidence` / `comment` and assert equality after load.

**Acceptance:**
- Both fields default `None`, are user-settable via constructor, round-trip cleanly, and are omitted from JSON when `None`.
- Loading a JSON without these fields succeeds with both attrs set to `None`.

**Depends on:** Task 1.

---

## Task 3 — Interface: pin to `efootprint ^21.1.0` + regenerate bundled reference data

**Goal:** Pin the published library and re-save bundled reference-data JSONs in the new schema. Mechanical.

**Files touched (e-footprint-interface):**
- `pyproject.toml` — bump `efootprint` dependency pin to `^21.1.0`. Refresh `poetry.lock`.
- `model_builder/domain/reference_data/*.json` — regenerated by running `tests/unit_tests/domain/test_reference_data.py` as a script (existing tooling).
- `model_builder/version_upgrade_handlers.py` — add a no-op (or pass-through) entry for the v20→v21 system bump if the interface tracks library schema versions; otherwise leave untouched.

**Tests added/changed:**
- Existing reference-data and integration tests must pass against the regenerated JSONs.

**Acceptance:**
- `poetry install` resolves `efootprint==21.1.x`.
- `pytest tests --ignore=tests/e2e` green.
- Bundled reference-data JSONs contain the top-level `"Sources"` block and id-ref shape.

**Depends on:** Task 2 (library published to PyPI, or pinned via local editable path during dev — pin to PyPI before merging).

---

## Task 4 — Interface: form pipeline backend (parser, factory, `available_sources`)

**Status:** Done.

**Goal:** Wire the four new metadata fields through the parser → factory chain server-side. Add `ModelWeb.available_sources`. Ships without UI: hidden inputs, if present, would be parsed and applied; the form_field_generator builds the metadata payload but no template consumes it yet.

**Files touched:**
- `model_builder/domain/entities/web_core/model_web.py` — new `available_sources` property: collect distinct `Source` instances across all `ExplainableObject`s in the system (by id, structurally guaranteed unique post-Task 1), then append `Sources.USER_DATA` / `Sources.HYPOTHESIS` if missing. Returns a list ordered by name.
- `model_builder/adapters/forms/form_field_generator.py` — for each input field, build a `metadata` payload alongside the existing `source` payload: current `confidence`, current `comment`, current source id/name/link, and `available_sources` (id/name/link list) for the picker.
- `model_builder/adapters/forms/form_data_parser.py` — recognise reserved suffixes `__confidence`, `__comment`, `__source_name`, `__source_link`, `__source_id` (checked **before** the generic `__` → `form_inputs` branch). They flow into `parsed[attr]["confidence" / "comment" / "source"]` (source as a sub-dict with `id`, `name`, `link`).
- `model_builder/domain/object_factory.py` — new `_apply_metadata(explainable_object, parsed_value, available_sources, pending_sources)` helper. Used by both `create_efootprint_obj_from_parsed_data` and `edit_object_from_parsed_data`. Each caller hoists `available_sources = model_web.available_sources` and an empty `pending_sources: dict` before its loop and threads them through. Rules:
  - resolve submitted source against `available_sources` by id; if id missing or unknown but a name is provided, mint a new `Source(name, link, id=submitted_id)`;
  - `pending_sources` is a per-submission dict keyed by submitted id, so two fields in the same form submission carrying the same client-generated id resolve to the *same* `Source` instance (same-form cross-field source sharing);
  - confidence: carry the submitted value (one of `low`/`medium`/`high`) or `None` if absent — value-change-driven reset is enforced client-side, not on the server, so explicit user submissions are honored;
  - comment: carry the submitted value, with empty string normalized to `None`.

**Tests added/changed:**
- `tests/unit_tests/adapters/forms/test_form_data_parser.py` — cover all five new reserved suffixes; cover ordering vs. the generic `__` branch.
- `tests/unit_tests/domain/test_object_factory.py` — cover create and edit paths applying metadata; cover the value-changed → confidence-reset / comment-carry rule; cover source resolution against `available_sources` (existing pick by id, custom name+link mints a new Source).
- `tests/unit_tests/domain/test_model_web.py` (or equivalent) — `available_sources` returns deduplicated list; sentinels always present.
- One integration test under `tests/integration/...`: post an edit with full metadata via the parser → factory chain; assert the resulting `ExplainableObject` carries the metadata, and that its `Source` is the same Python instance as the one already in the model when an existing source is picked.

**Acceptance:**
- All listed unit + integration tests pass.
- `pytest tests --ignore=tests/e2e` green.
- No visible UI change (no template consumes the new payload yet).

**Depends on:** Task 3.

---

## Task 5 — Interface: confidence badge + source editor templates + JS widget; rewrite `source.html`

**Status:** Done.

**Goal:** Surface the new metadata in the input form. Confidence badge inline right of the input/unit; source line becomes server-rendered and clickable, opening an inline editor for source + comment. Hidden inputs piggyback on the existing edit form's Save button.

**Files touched:**
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/source.html` — rewritten. Server-rendered source line + comment line + collapsed inline editor wrapper. Hidden inputs: `<prefix>_<attr>__source_id`, `__source_name`, `__source_link`, `__comment`. Comment uses `components/truncating_text.html`.
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/confidence_badge.html` (new) — badge + dropdown menu + hidden `__confidence` input. "Set confidence" affordance when `None`; colored badge for `low`/`medium`/`high`.
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/source_editor.html` (new) — collapsed inline editor matching `mockup.html`: source `<select>` populated from `available_sources`, custom-name + link fields revealed by a "custom" option, comment textarea (`maxlength="2000"`), "Apply" / "Cancel" actions. Apply writes to hidden inputs; Cancel restores from hidden inputs without mutating them. Quiet collision notice when free-entry name matches a canonical `Sources.*` name.
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/dynamic_form_field.html` — slot the confidence-badge partial right of input/unit; wire the new source partial.
- `theme/static/scripts/source_metadata.js` (new, ~80 lines vanilla JS) — confidence dropdown open/close + value selection; source-editor open/close + Apply/Cancel; custom-name collision detection against `available_sources` names. **Form-level source registry**: when the user creates a new custom source via the editor, generate a stable client-side id (e.g. `crypto.randomUUID().slice(0, 6)`) on Apply, write it into the field's hidden `__source_id`, and inject the new source into every other source `<select>` in the same form so siblings can pick it. Backend `_apply_metadata` deduplicates by this id via `pending_sources`.
- `theme/static/scripts/dynamic_forms.js` — `updateSource` no longer rewrites the source div. On input value change: pulse the badge with a `confidence-just-reset` animation and clear the hidden `__confidence` input. The reset is purely client-side; the server honors whatever `__confidence` is in the submission.

**Tests added/changed:**
- Existing template-rendering tests pass.
- `npm run jest` — basic unit coverage for the new JS module if the project has Jest harness for it (open the editor, write to hidden inputs on Apply, restore on Cancel).
- No new Python tests — server-side coverage is in Task 4.

**Acceptance:**
- Manual smoke test: open the model builder, open an input form, see the confidence badge + clickable source line; open the editor, pick an existing source, type a comment, hit Apply, hit Save; verify the value persists and the badge reflects state.
- Cancel after typing does not change the saved comment.
- Editing the input value pulses the badge and clears the displayed confidence; on Save, server forces `confidence = None` while comment carries.

**Depends on:** Task 4.

---

## Task 6 — Interface: source table — two new columns + row edit affordance

**Goal:** Add `Confidence` and `Comment` columns to `source_table.html`. Inputs get an inline edit affordance that reuses the source/comment editor from Task 5; calculated rows render both columns empty and non-editable.

**Files touched:**
- `model_builder/templates/model_builder/result/source_table.html` — two new columns inserted after the existing `Source` column. Per-row edit affordance on input rows only. Row-edit affordance opens the same `source_editor.html` partial used in the form, posting through the same `edit_object` path (one shared write path).
- `model_builder/adapters/views/views.py` — if needed, expose `available_sources` to the source-table context.

**Tests added/changed:**
- Adjust any existing snapshot/render test for the source table.
- Add an E2E case in Task 8 covering edit-from-source-table.

**Acceptance:**
- Source table renders two new columns; inputs are editable inline; calculated rows are not.
- Existing source-table tests still pass.

**Depends on:** Task 5 (reuses the editor partial).

---

## Task 7 — Interface: xlsx export columns

**Goal:** Add `confidence` and `comment` columns to the xlsx export of the source table.

**Files touched:**
- `model_builder/adapters/views/views.py` (`download_sources`) — emit two new columns after `Source link`.

**Tests added/changed:**
- `tests/unit_tests/adapters/views/test_download_sources.py` (or wherever the export is covered) — assert column headers and values.

**Acceptance:**
- Downloading the xlsx for a system with metadata-bearing inputs includes `confidence` and `comment` columns populated from the underlying `ExplainableObject`s.

**Depends on:** Task 4.

---

## Task 8 — Interface: E2E coverage

**Goal:** Lock the user-visible behavior in Playwright.

**Files touched:**
- `tests/e2e/test_source_metadata.py` (new).

**Tests added/changed:** scenarios —
- Set confidence on an input via the badge dropdown; reload; confidence persists.
- Set a comment via the source editor; reload; comment persists and renders truncated with click-to-expand.
- Edit source via the editor: pick an existing canonical source from the dropdown; verify the picked `Source` instance is reused (assert via the source table, no duplicate row).
- Edit source via the editor: free-entry custom name + link; verify a new Source is created.
- Edit source via the editor: free-entry name colliding with a canonical `Sources.*` name; verify the quiet notice is shown and a distinct Source is created (no auto-snap).
- Edit the input value with metadata present; verify badge pulses and confidence resets to unset; verify comment persists.
- Open the editor, type into the comment, hit Cancel; verify the saved comment is unchanged.
- Download → upload round-trip preserves confidence, comment, and source identity (no source duplication).
- Edit metadata from the source-table row affordance.

**Acceptance:**
- `poetry run pytest tests/e2e/test_source_metadata.py -n 4` green against a running server.

**Depends on:** Tasks 5, 6.

---

## Ordering rationale

- **Task 1 → Task 2** — Task 2 depends on Task 1's centralized `_apply_json_metadata` helper and the new loader path. Splitting them keeps the structural Source-id work (with its v20→v21 schema migration) reviewable on its own; the metadata-fields PR is then a clean additive minor bump.
- **Task 2 → Task 3** — interface can only pin a published library version. During development, work against the local editable path; flip the pin before merging the interface PR.
- **Task 3 → Task 4** — `available_sources` and the form pipeline depend on the new `Source.id` and the runtime guarantee that each id resolves to one instance per loaded model.
- **Task 4 → Task 5** — the templates emit hidden inputs that Task 4's parser/factory consume. Shipping Task 4 first means the backend can ride existing form submissions without UI change; Task 5 then turns the UI on.
- **Task 5 → Task 6** — the source-table edit affordance reuses the editor partial introduced in Task 5.
- **Tasks 6 and 7** are independent of each other; both depend on Task 4 (and Task 6 also on Task 5). Either can land first.
- **Task 8** lands last because it covers the full end-to-end user flow including round-trip persistence.
