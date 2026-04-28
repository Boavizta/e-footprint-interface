# Source metadata — implementation plan

**Status:** Plan — under review.
**Date:** 2026-04-28.
**Spec:** [`spec.md`](spec.md).

## 1. Approach

Two attributes — `confidence` and `comment` — are added to `ExplainableObject` (library), default `None`, threaded through `__init__`, `to_json`, `from_json_dict`, and `__copy__`. They are user-settable on inputs only; they stay `None` on calculated values. The same JSON shape change is purely additive, so loading an old payload is a no-op. While we are in `to_json`, we replace the inline `{"name": ..., "link": ...}` with `self.source.to_json()` to remove the duplication called out in the spec.

Source identity on JSON load is restored at one place — the deserializer — using a `(name, link) → Source` registry kept in a `ContextVar` set by `json_to_system` and consulted by `Source.from_json_dict`. The registry is seeded with all `Sources.*` canonical singletons so reloads also re-identify with the Python constants. Outside a load (live `ExplainableObject.from_json_dict` calls used by calculus-graph deserialization, by tests, etc.), the ContextVar is unset and `Source.from_json_dict` falls back to today's "mint a new instance" behavior — no signature changes ripple through every subclass.

On the interface, the existing `source.html` partial — today a client-side label derived from "is the input value different from default?" — is replaced by a server-rendered, interactive source-and-comment line backed by the live `ExplainableObject.source` / `.comment`. A new confidence-badge partial is rendered inline next to the input. Both badge and source line use HTMX to submit small partial updates through the existing `edit_object` endpoint; the form parser and object factory grow handlers for the three new metadata attributes. The "carry comment, reset confidence on value change" rule is enforced server-side in the factory's edit path so it survives any client tampering. A new `ModelWeb.available_sources` property returns the deduplicated source list scoped to the current modeling, with `Sources.USER_DATA` and `Sources.HYPOTHESIS` always appended.

## 2. Affected modules

### Library (`e-footprint`)

| Module / file | Change type | Note |
|---|---|---|
| `efootprint/abstract_modeling_classes/explainable_object_base_class.py` | modified | Add `confidence`/`comment` slots, init args, `to_json`/`from_json_dict` round-trip, `__copy__` propagation. Replace inline source dict with `self.source.to_json()`. ContextVar `_source_registry` consulted in `Source.from_json_dict`. |
| `efootprint/abstract_modeling_classes/explainable_quantity.py` | modified | Thread `confidence`/`comment` through subclass `__init__`/`from_json_dict`/`to_json`. |
| `efootprint/abstract_modeling_classes/explainable_hourly_quantities.py` | modified | Same. |
| `efootprint/abstract_modeling_classes/explainable_recurrent_quantities.py` | modified | Same. |
| `efootprint/abstract_modeling_classes/explainable_timezone.py` | modified | Same. |
| `efootprint/abstract_modeling_classes/source_objects.py` | modified | `SourceObject`/`SourceValue`/`SourceTimezone`/`SourceHourlyValues`/`SourceRecurrentValues` accept and forward `confidence`/`comment` (default `None`). |
| `efootprint/builders/timeseries/explainable_hourly_quantities_from_form_inputs.py` | modified | Forward new kwargs through init + JSON. |
| `efootprint/builders/timeseries/explainable_recurrent_quantities_from_constant.py` | modified | Same. |
| `efootprint/api_utils/json_to_system.py` | modified | Set `_source_registry` ContextVar (seeded with `Sources.*` singletons) for the duration of the load; reset in `finally`. |
| `tests/abstract_modeling_classes/test_explainable_object_base_class.py` (and adjacent subclass tests) | modified | Round-trip, copy-semantics, `None` defaults. |
| `tests/api_utils/test_json_to_system.py` | modified | New test: source identity restored across `to_json` → `from_json_dict` for sources shared by multiple `ExplainableObject`s; canonical `Sources.*` re-identification on reload. |

### Interface (`e-footprint-interface`)

| Module / file | Change type | Note |
|---|---|---|
| `model_builder/domain/entities/web_core/model_web.py` | modified | New `available_sources` property: dedup `(name, link)` across all `ExplainableObject`s, then append `Sources.USER_DATA` / `Sources.HYPOTHESIS` if missing. Returns concrete `Source` instances. |
| `model_builder/adapters/forms/form_field_generator.py` | modified | For each input field, build a `metadata` payload (`confidence`, `comment`, current-source dict, `available_sources` for the picker). Plumbed alongside the existing `source` payload. |
| `model_builder/adapters/forms/form_data_parser.py` | modified | Recognise reserved suffixes `__confidence`, `__comment`, `__source_name`, `__source_link` (checked **before** the generic `__` → `form_inputs` branch). They flow into `parsed[attr]["confidence" / "comment" / "source"]`. |
| `model_builder/domain/object_factory.py` | modified | `_apply_metadata(explainable_object, parsed_meta, value_changed)` helper. Used by both `create_efootprint_obj_from_parsed_data` and `edit_object_from_parsed_data`. Enforces "value changed → confidence forced to `None`, comment carried". Resolves submitted source against `model_web.available_sources` (match on `(name, link)`); if no match, mints a new `Source(name, link)`. |
| `model_builder/templates/model_builder/side_panels/dynamic_form_fields/source.html` | rewritten | Server-rendered source line + comment line + inline editor. Uses `components/truncating_text.html` for the comment. No more JS-driven `updateSource` mutation of this div. |
| `model_builder/templates/model_builder/side_panels/dynamic_form_fields/confidence_badge.html` | new | Small partial — the badge itself + the dropdown menu. Posts via HTMX `hx-post` to a new tiny endpoint (or reuses `edit_object` with a single-attribute payload — see §4 risk). |
| `model_builder/templates/model_builder/side_panels/dynamic_form_fields/source_editor.html` | new | The inline editor: source `<select>` with `available_sources`, custom-name + link inputs, comment textarea, save/cancel. Submits via HTMX. |
| `model_builder/templates/model_builder/side_panels/dynamic_form_fields/dynamic_form_field.html` | modified | Slot in the confidence-badge partial right of the input/unit; wire the new source partial. |
| `theme/static/scripts/dynamic_forms.js` | modified | `updateSource` no longer rewrites the source line — its job is reduced to the dropdown open/close + "value changed → mark badge `confidence-just-reset`" UI hint. The server-side parser is the source of truth for the actual reset. |
| `model_builder/adapters/views/views.py` (`download_sources`) | modified | Add `confidence` and `comment` columns to the xlsx export (after `Source link`). |
| `model_builder/templates/model_builder/result/source_table.html` | modified | Two new columns inserted after `Source`. Per-row edit affordance on input rows only (calculated rows render both columns empty + non-editable). The row-edit affordance opens the same inline source-editor partial used in the form. |
| `tests/unit_tests/adapters/forms/test_form_data_parser.py` | modified | Cover the four new reserved suffixes. |
| `tests/unit_tests/domain/test_object_factory.py` | modified | Cover create + edit metadata application; cover the value-changed → confidence-reset / comment-carry rule; cover source resolution against the registry. |
| `tests/integration/...` | modified | One integration test: post an edit with full metadata via the parser → factory chain, assert the resulting `ExplainableObject`. |
| `tests/e2e/test_source_metadata.py` | new | Set confidence; set comment; edit source (canonical pick + custom + collision notice); edit value with metadata present (badge resets, comment persists); download → upload round-trip preserves both fields. |

## 3. Cross-cutting concerns

- **Tests:**
  - Library: unit tests for serialization round-trip, copy semantics, ContextVar-driven source dedup; one integration test for `json_to_system` proving identity is restored for sources shared by multiple `ExplainableObject`s and that canonical `Sources.*` are re-identified.
  - Interface: parser unit tests for the four new suffixes; factory unit tests for the metadata-apply rule; one integration test for the full edit chain; one E2E covering set/edit/round-trip.
- **Migrations:** none. The library JSON change is purely additive; absent fields read as `None`. `interface_config` schema is unchanged. No Django models change. No version bump.
- **Docs:**
  - `e-footprint-interface/specs/architecture.md` — one line under "Composite form field metadata" or a new "Source metadata" subsection: how the new metadata payload flows through `form_field_generator` → templates → `form_data_parser` → `object_factory`.
  - `e-footprint-interface/specs/conventions.md` — note the reserved `__confidence` / `__comment` / `__source_name` / `__source_link` suffixes and that they are checked before the generic `__` form-inputs branch.
  - `e-footprint/AGENTS.md` (or its architecture spec) — note that JSON load now scopes a `Source` dedup registry via `ContextVar`, seeded with `Sources.*`.

## 4. Risks

- **ContextVar leakage.** If `json_to_system` raises, the registry must be reset. Mitigation: set/reset in a `try`/`finally`. Side concern: nested `json_to_system` calls (does that exist? — not in tree today, but still) — use `Token.var.reset(token)` rather than naive overwrite.
- **Subclass JSON signatures.** Several `from_json_dict` overrides instantiate the class directly. Threading two new optional kwargs through each is mechanical but easy to miss for a class. Mitigation: a single library-side test that round-trips one instance of every concrete `ExplainableObject` subclass with both fields set, asserting equality.
- **Confidence-badge endpoint shape.** Two options: (a) reuse `edit_object` with a single-attribute payload (simplest, one endpoint), or (b) add a dedicated `set-explainable-metadata` endpoint. Recommendation: **(a)** — `edit_object` already runs the parser and factory; threading a single-attribute payload through it costs nothing and avoids a parallel write path. The badge POSTs `<prefix>_<attr>__confidence` only and HTMX-swaps the badge partial.
- **Source-line truth swap.** `updateSource()` in `dynamic_forms.js` currently rewrites the source div on every keystroke, baking in the assumption "any change → user data". With the source line now server-rendered and authoritative, that JS is contradicted. Mitigation: drop the source-rewriting branch from `updateSource`; the server-side factory still defaults the source to `Sources.USER_DATA` on value change (see existing `edit_object_from_parsed_data` line 174), so the actual data follows. Document this in the conventions one-liner.
- **Source picker dedup vs. existing duplication.** Today `web_explainable_quantities_sources` and the xlsx export already silently dedupe nothing. Once the library-side dedup lands, both consumers automatically behave better — no breaking change, but a behavioural change worth noting in CHANGELOG.
- **Comment textarea vs. JSON size.** No data-model cap; recommend a 2 000-char soft cap in the UI textarea (HTML `maxlength`) for layout sanity, as the spec hints.

## 5. Alternatives considered

- **Per-consumer source dedup** (only in the picker, not in the deserializer). Rejected per spec §7: it's symptom-level and leaves the same duplication in the source table and xlsx export.
- **Threading an explicit `source_registry` kwarg through every `from_json_dict` signature** instead of a ContextVar. Rejected: ripples through every concrete subclass and every modeling-object class that constructs `ExplainableObject`s during load, with no behavioural upside. The ContextVar is local to the load call and easy to reset.
- **Confidence/comment on `Source`** instead of `ExplainableObject`. Rejected per spec §2: two values citing the same source can carry different confidence/comments.
- **Dedicated metadata endpoint** instead of reusing `edit_object`. Rejected (see risk above): would parallel the existing parser/factory write path with no win.
- **Client-side enforcement of the "reset confidence on value change" rule.** Rejected as the only enforcement: server-side authority is necessary so the rule survives client-side tampering or stale forms. Client-side animation (`confidence-just-reset` pulse) is kept as UX feedback only.

## 6. Constitutional notes

- **§1.1 (Clean Architecture).** Confidence/comment travel through the existing parser → factory → domain chain. No new layer crossings; templates and views stay in adapters.
- **§1.3 (library is the truth).** All metadata mechanics live in `ExplainableObject`; the interface only renders and forwards. Compliant.
- **§1.4 (HTMX-first; minimize JS).** Confidence dropdown and source editor save via HTMX `hx-post`/swap. Vanilla JS is limited to dropdown open/close and the reset-pulse animation. Compliant.
- **§2.4 (PyPI-pinned `efootprint`).** This feature spans both repos. During development the interface will pin to a local editable `efootprint`; the library change must be cut, published, and re-pinned in `pyproject.toml` before the interface PR merges to `main`. Standard cross-repo workflow.
- **§4.** Nothing here re-opens a rejected scope item.

No constitutional amendment needed.

## 7. Open questions

- **Confidence-badge endpoint** — confirm the "reuse `edit_object` with a single-attribute payload" choice (risk §4) before starting interface work.
- **Available-sources dedup key with `None` link.** Recommendation: dedup key is `(name, link)` with `link or None` normalised to `None` (no empty-string vs `None` ambiguity). Confirm before tasks.
- **Free-entry collision UX.** Spec §4 says "kept as a distinct `Source` instance, with a quiet notice". The plan keeps that exactly. Confirm we are not auto-snapping silently.
