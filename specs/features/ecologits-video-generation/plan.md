# EcoLogits video-generation integration — Implementation plan

**Status:** Plan — under review.
**Date:** 2026-05-26.
**Spec:** [`spec.md`](spec.md).

## 1. Approach

Mirror the existing EcoLogits LLM trio (`EcoLogitsGenAIExternalAPIServer` /
`EcoLogitsGenAIExternalAPI` / `EcoLogitsGenAIExternalAPIJob`) with a new
video-generation trio living next to it under
`efootprint/builders/external_apis/ecologits/`. The Job calls
`ecologits.estimations.impacts_video_generation` once per relevant input
change, caches the full output as an `ExplainableDict`, and extracts the
GWP-only attributes the rest of e-footprint already knows how to consume —
keeping ADPe/PE/WCF in the cache for a future Boavizta integration without
re-querying. The Server aggregates per-Job request-level outputs into the
three standard hourly footprints, so system-wide rendering, JSON
round-trip, and impact repartition work without special-casing.

On the interface side this is a class-registration + form-cascade
extension: add the wrapper-class mapping, surface the new API in
`ExternalAPIWeb.available_classes`, verify (and extend if missing) the
boolean `SourceObject` widget and the `conditional_list_values` cascades —
`provider → model_name` in the API form and the cross-object
`model_name → resolution` hop in the Job form (Task 5) — then cover the flow
with one E2E test. No new HTMX flows, no schema changes, no new render strategy.

The shared `ecologits_dag_structure.py` is renamed to the plural
`ecologits_dag_structures.py` and grows a `get_formula(dag, task_name)`
helper parametrized by DAG, so the video module can reuse the LLM-side
explainability-tree wiring against the new
`ecologits.impacts.video.dag`.

## 2. Affected modules

### Library (`e-footprint`)

| Module / file | Change type | Note |
|---|---|---|
| `efootprint/builders/external_apis/ecologits/ecologits_video_external_api.py` | new | Houses the three new classes: `EcoLogitsVideoGenExternalAPIServer`, `EcoLogitsVideoGenExternalAPI`, `EcoLogitsVideoGenExternalAPIJob`. |
| `efootprint/builders/external_apis/ecologits/ecologits_dag_structures.py` | rename + extend | Rename from `ecologits_dag_structure.py` (singular). Export both LLM and video `__dependencies` and a `get_formula(dag, task_name)` helper. |
| `efootprint/builders/external_apis/ecologits/ecologits_unit_mapping.py` | extended | Add video-DAG keys: `server_accelerator_power` (`u.kW`), `server_accelerator_energy` (`u.kWh`), `server_accelerator_count` (dimensionless), `video_width`, `video_height`, `video_frames_count` (dimensionless), `server_lifetime` (`u.s`), `non_audio_weight` and the `n / m / m1 / m2 / n1 / n2 / g` regression coefficients (dimensionless). WCF-only nodes (`request_usage_wcf`, `if_electricity_mix_wue`, `datacenter_wue`) need no mapping — not extracted. |
| `efootprint/builders/external_apis/ecologits/sources.py` (or wherever `ecologits_source` lives) | extended | Add `ecologits_video_defaults_source = Source("Ecologits impacts_video_generation defaults", "https://github.com/mlco2/ecologits/tree/main/ecologits/estimations/video.py")`. |
| `efootprint/all_classes_in_order.py` | modified | Add the three new classes to `ALL_EFOOTPRINT_CLASSES`. None belong in `CANONICAL_COMPUTATION_ORDER` (builders sit outside `core/`). |
| `CHANGELOG.md` | modified | Entry under upcoming release. |
| `tests/builders/external_apis/ecologits/` | new test module | Unit + integration coverage for the three classes, the unit mapping, and the DAG helper. |

### Interface (`e-footprint-interface`)

| Module / file | Change type | Note |
|---|---|---|
| `model_builder/domain/efootprint_to_web_mapping.py` | modified | Two entries: `"EcoLogitsVideoGenExternalAPI": ExternalAPIWeb`, `"EcoLogitsVideoGenExternalAPIJob": JobWeb`. |
| `model_builder/domain/entities/web_builders/services/external_api_web.py` | modified | Add `EcoLogitsVideoGenExternalAPI` to `ExternalAPIWeb.available_classes`. Path confirmed during planning. |
| `model_builder/adapters/forms/form_field_generator.py` | extended | Add a boolean branch alongside `list_values` / `conditional_list_values` (currently falls through to `input_type: "str"` at line 328, rendering a plain text input). For the cross-object `resolution` field (dotted `depends_on="external_api.model_name"`), the `conditional_list_values` branch resolves the dotted path via `model_web` and re-keys the emitted `dynamic_lists` entry by the referenced API object's id, so the existing single-hop cascade applies (see Task 5). |
| `theme/static/scripts/dynamic_forms.js` | unchanged (revisited) | No change needed. The cascade is split across two forms — `provider → model_name` in the API form, `model_name → resolution` cross-object in the Job form — so no single form holds a multi-level chain; the existing single-hop listener suffices once the generator re-keys the cross-object entry (Task 5). NB: a three-level same-form chain-propagation path was built in Task 2 on a misdiagnosis and removed in Task 4 as it had no consumer. |
| `model_builder/templates/model_builder/side_panels/dynamic_form_fields/bool.html` | new | Checkbox/toggle template for boolean `SourceObject` rendering. Wired from the new generator branch above. |
| `tests/integration/` | new test | Load a fixture system containing the new classes and assert round-trip + emissions calc. |
| `tests/e2e/` | new test | Add the API + job through the model-builder UI, save, assert non-zero footprint in results. |
| `CHANGELOG.md` | modified | Entry under upcoming release. |

### Class shape (substantive design)

- **`EcoLogitsVideoGenExternalAPI`** inputs:
  - `provider: SourceObject` — `list_values` = sorted set of unique providers parsed from the `"provider/model_name"` slugs in `video_models.json`. Default `"openai"`.
  - `model_name: SourceObject` — `conditional_list_values` keyed by provider. Default `"sora-2-pro"`.
  - `datacenter_location` and `data_center_pue` are **calculated attributes**, not inputs: inferred from `ecologits.estimations.video._PROVIDER_CONFIGURATIONS[provider]` (which now ships per-provider `datacenter_location`, `datacenter_pue`, `datacenter_wue`). Mirrors how `EcoLogitsGenAIExternalAPI` infers them from `PROVIDER_CONFIG_MAP`. Not surfaced in the UI.
  - `average_carbon_intensity` is also a **calculated attribute** (derived from `datacenter_location` via the EcoLogits electricity-mix repository), again mirroring `EcoLogitsGenAIExternalAPI`. The Job feeds it into the DAG as `if_electricity_mix_gwp`, so grid carbon intensity is an explicit, traceable node in the impacts explanation graph rather than an anonymous inline lookup.
  - `datacenter_wue` deliberately **not** exposed — feeds water only (out of GWP scope); the Job reads it inline from `_PROVIDER_CONFIGURATIONS[provider]` inside `update_impacts` (no shared graph node).
  - Historical note: these three were originally user inputs (location/PUE as advanced params, WUE a hardcoded `0.5`) because EcoLogits shipped no per-provider video config. Once it did, they became inferred.
- **`EcoLogitsVideoGenExternalAPIJob`** inputs:
  - `external_api: EcoLogitsVideoGenExternalAPI`.
  - `resolution: SourceObject` — `"<short> (<width> x <height>)"` format (same as `VideoStreamingJob`); `conditional_list_values` keyed by `model_name` from the catalog. Parsed back into `(w, h)` with the same regex idiom before calling EcoLogits.
  - `duration: ExplainableQuantity` (`u.s`), default `SourceValue(8 * u.s)`.
  - `with_audio: SourceObject` (boolean), default `SourceObject(True)`.
- **Cached impacts dict** (`update_impacts`): one `impacts_video_generation` call per relevant input change, stored as `ExplainableDict` with logical deps on `duration`, `resolution`, `with_audio`, plus API-level DC params. All extracted attributes read from this dict — same pattern as the LLM Job.
- **Extracted per-Job calculated attributes**: `generation_latency` (`u.s`), `request_energy` (`u.kWh`), `request_usage_gwp` (`u.kg`), `request_embodied_gwp` (`u.kg`). `update_request_duration` points at `generation_latency`.
- **`update_data_transferred`** estimates per-call bytes as
  `duration × bits_per_pixel × pixel_count × fps`, mirroring
  `VideoStreamingJob.update_dynamic_bitrate`. `bits_per_pixel`
  (`0.1 * u.bit`), `fps` (`24 / u.s`, matching EcoLogits'
  `duration_to_frames`), and the local `datacenter_wue = 0.5` are
  **internal e-footprint hypotheses constructed fresh inside the update
  method** — never module-level singletons, so they don't end up as shared
  nodes across calculation graphs (same rule as `bytes_per_token` in the
  LLM Job). `pixel_count` is parsed from the resolution label.
- **Server class**: same three `update_instances_*` methods and the two
  repartition-weight updaters as the LLM Server. Don't preemptively factor
  a shared base class — see Alternatives.

## 3. Cross-cutting concerns

- **Tests.**
  - *Library unit:* per-class construction with defaults, default-value round-trip, `update_impacts` invalidation on each relevant input change, unit-mapping coverage for every key the video DAG produces, the `get_formula(dag, task_name)` helper for both LLM and video DAGs.
  - *Library integration:* a small system with one video API + one Job + one Server aggregator runs end-to-end, JSON round-trips with calculated attributes preserved (constitution §2.3), produces non-negative hourly footprints monotonically increasing in `duration`. **Structural assertions only** (units, presence, non-negative, monotonicity) — no literal magnitudes, so EcoLogits regression re-fits don't churn the test.
  - *Anti-drift test (load-bearing).* Assert
    `ecologits.estimations.video.duration_to_frames(d) == int(d * 24 + 1)`
    for several `d`. If upstream changes the formula, our `fps = 24 / u.s`
    hypothesis in `update_data_transferred` drifts away from the
    assumption EcoLogits' compute-side regression is calibrated against,
    and the network-energy contribution to GWP silently skews. The test
    is *meant* to fail loudly on upstream changes.
  - *Interface unit + integration:* form generation for the new classes including the `provider → model_name` cascade, the cross-object `model_name → resolution` re-keying (Task 5), and the boolean widget; loading a fixture system containing the new classes through `ModelWeb` round-trips.
  - *Interface E2E:* one new test under `tests/e2e/` — add the API, attach a job, save, assert a non-zero footprint in results.
- **Migrations.** No JSON schema change planned (adding classes is additive). No new migration handler needed in `efootprint/api_utils/version_upgrade_handlers.py`.
- **Docs.** Class-level docstrings and `param_descriptions` are the SSOT (constitution §1.4) — mkdocs reference and the interface help drawer pick them up automatically through `EfootprintDescriptionProvider`. Add entries alongside External APIs section. `CHANGELOG.md` entry on both repos.

## 4. Risks

- **EcoLogits private branch slips past Vivatech 2026.** The `ecologits-video` branch pins to a commit on `samuelrince/ecologits-private`; the post-Vivatech swap to the public PyPI release is a separate planned commit per `PRIVATE_INTEGRATION.md`. Mitigation: keep the integration in its own branch; don't merge to `dev` before the public release lands.
- **Cross-object `model_name → resolution` cascade (corrected from the original "three-level same-form chain" framing).** The cascade is not a single in-form chain: `provider → model_name` is in the API form, and `model_name → resolution` is cross-object in the Job form (`resolution.depends_on="external_api.model_name"`). No form holds a three-level chain, so the JS chain-propagation explored here was removed in Task 4. The remaining gap — the resolution datalist's `filter_by` points at the non-DOM dotted id `..._external_api.model_name` — is closed in Task 5 by re-keying the entry by the selected API object's id at form-generation time (each API has a fixed `model_name`), reusing the single-hop listener with no new JS. Risk is implementation scope, not capability uncertainty.
- **Boolean `SourceObject` widget — confirmed missing, extension scoped.** `form_field_generator.py:301–328` has branches for `list_values` and `conditional_list_values` only; a boolean `SourceObject(True)` falls through to `input_type: "str"` and renders as a text input where the user must type "True" / "False" with no validation. No precedent in the codebase (zero `SourceObject(True|False)` instances). Mitigation: new `bool.html` template + a generator branch, both in §2 Affected modules.
- **LLM and video DAGs share only some node names.** `request_usage_wcf` and the `server_accelerator_*` family are video-only. The shared `get_formula(dag, task)` helper must key by `(dag, task_name)`, not assume node-name overlap. Mitigation: helper signature already takes `dag` explicitly.
- **Anti-drift test breaks on EcoLogits re-fits.** This is intentional — the test is the load-bearing signal that our `fps` hypothesis needs revisiting. Documented in the test rationale so a future agent doesn't "fix" it by softening the assertion.
- **Friendly labels.** Catalog uses lowercase slugs (`openai`, `sora-2-pro`, `bytedance/seedance-1.5-pro`). First iteration shows them verbatim. Risk: minor UX friction at Vivatech. Mitigation: revisit only if user feedback flags it.

## 5. Alternatives considered

- **Share a single Server class with the LLM trio.** Rejected. The Server is the aggregator for one provider/model family; mixing video and LLM Jobs on the same Server muddles per-call assumptions and obscures the hourly footprint shape users expect. Mirror the trio; factor a base class only if real duplication appears across both Server implementations.
- **Derive DC params from a `VIDEO_PROVIDER_CONFIG_MAP`** (LLM-style calculated attributes). Rejected for this iteration — upstream doesn't ship one. Revisit if EcoLogits adds it; switching inputs → calculated attributes is mechanical and doesn't reshape the public API.
- **Expose `datacenter_wue` as an input.** Rejected. It only feeds `request_usage_wcf` (water), which is outside the GWP-only extraction scope per `mission.md`. Read it inline from the EcoLogits per-provider config in `update_impacts` (originally a hardcoded `0.5` before EcoLogits shipped per-provider WUE).
- **Surface ADPe / primary energy / water as e-footprint attributes.** Rejected — mission scope. The EcoLogits dict caches them for the future Boavizta integration; no re-query needed when scope expands.
- **Module-level constants** (`bits_per_pixel`, `fps`, `datacenter_wue`). Rejected. They'd become shared nodes across calculation graphs. Construct fresh inside `update_data_transferred` / `update_impacts`, same rule as `bytes_per_token` in the LLM Job.
- **Surface a preemptive shared base class for the Server/API/Job triplets.** Rejected (constitution §1.3 leanness). Wait until both Servers exist and the actual overlap is visible before extracting.
- **Pretty labels at v1.** Rejected. Verbatim slugs ship now; presentation layer is cheap to add later if needed.

## 6. Constitutional notes

- **e-footprint constitution §1.1** — new code sits in `efootprint/builders/external_apis/ecologits/`, importing from `abstract_modeling_classes/` and `core/`. No imports from `api_utils/`.
- **e-footprint constitution §1.4** — every new class has a docstring, every `__init__` param has a `param_descriptions` entry, every `update_*` method has a docstring describing the calculated attribute. These flow into mkdocs and the interface help drawer; descriptions are not duplicated anywhere else.
- **e-footprint constitution §2.3 / §2.5** — JSON round-trip preserved (covered by integration test); new classes registered in `ALL_EFOOTPRINT_CLASSES`. None belong in `CANONICAL_COMPUTATION_ORDER` (builders sit outside `core/`).
- **e-footprint constitution §2.6** — `CHANGELOG.md` entry on the library side.
- **interface constitution §1.1** — interface-side additions stay in their layers: web wrappers in `domain/entities/web_builders/`, the form-widget extension (if needed) in `adapters/forms/`. No Django imports into `domain/`.
- **interface constitution §1.3** — the library remains the domain truth; the interface only wraps and renders. No re-implementation of EcoLogits logic in interface code.
- **Private-dep envelope** (`PRIVATE_INTEGRATION.md`) — library work lives on the `ecologits-video` branch with `ecologits` pinned to a `samuelrince/ecologits-private` commit. Any incidental LLM-side EcoLogits refactor we'd want on public `dev` lands in a separate commit so it can be cherry-picked. Post-Vivatech, the pin is swapped for the public PyPI release in its own commit and the branch merges back to `dev`.

No constitutional amendment required.

## 7. Open questions

_All open questions from the initial draft were resolved during planning (2026-05-26):_

- _Cascade support — initially framed as a three-level same-form chain; on implementation (Tasks 3–5) found to be a `provider → model_name` cascade in the API form plus a cross-object `model_name → resolution` hop in the Job form. The cross-object hop is handled by re-keying the resolution datalist by API object id at form-generation time (Task 5); no in-form chain exists, so the chain-propagation JS was removed in Task 4._
- _Boolean `SourceObject` widget — investigated; not present. New `bool.html` + generator branch scoped in §2 / §4._
- _Defaults-source URL — set to `https://github.com/mlco2/ecologits/tree/main/ecologits/estimations/video.py` in §2._
- _Anti-drift test scope — limited to `duration_to_frames`; `bits_per_pixel` is purely an e-footprint-side hypothesis with no upstream counterpart to drift against, so a guard test would just assert our own constant equals itself._

None remaining before `spec-tasks`.
