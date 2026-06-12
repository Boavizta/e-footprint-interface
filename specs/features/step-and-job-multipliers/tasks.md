# Step and job multipliers — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).
**Cross-repo feature:** Tasks 1–2 land in `e-footprint` (library), Tasks 3–5 in `e-footprint-interface`. A PyPI release of the library separates Task 2 from Task 3 (constitution §2.4: interface `pyproject.toml` must reference PyPI before merge).

## Task 1 — Weighted-dict groundwork in the library (repo: e-footprint)

**Status:** Done

**Goal:** Land the shared list / plain-number → weighted-dict normalizer and prove `ExplainableObjectDict` works as a relationship carrier, without touching the three target relationships yet. `EdgeDeviceGroup` adopts the normalizer as its first consumer.

**Files touched:**
- `efootprint/abstract_modeling_classes/explainable_object_dict.py` (normalizer helper: list → `{entry: SourceValue(1 * u.dimensionless)}` with duplicates accumulating; dict values passed through if `ExplainableObject`, else wrapped as `SourceValue(n * u.dimensionless)`; `__setitem__` stays strict)
- `efootprint/core/hardware/edge/edge_device_group.py` (constructor uses the normalizer; validation — dimensionless, ≥ 0 — stays or moves into the normalizer)

**Tests added/changed:**
- Unit tests for the normalizer (list with duplicates, plain-number dict, pass-through, rejection of negatives / wrong dimension).
- Tests asserting dict keys participate in container registration / recomputation triggers like list entries (formalizing the EdgeDeviceGroup precedent).
- Existing EdgeDeviceGroup tests stay green; new ones cover plain-number sugar (`{device: 3}`).

**Acceptance:**
- `EdgeDeviceGroup(name, sub_group_counts=[g1], edge_device_counts={d1: 3})` works; full library pytest suite green; no change to any serialized output.

**Depends on:** none.

---

## Task 2 — Convert the three relationships to weighted dicts (repo: e-footprint)

**Status:** Done

**Goal:** `UsageJourney.uj_steps`, `UsageJourneyStep.jobs`, and `RecurrentServerNeed.jobs` become weighted `ExplainableObjectDict`s (same attribute names); all calculations honor the weights; pre-feature JSONs upgrade automatically. This is the whole modeling-semantics change in one review.

**Files touched:**
- `efootprint/core/usage/usage_journey.py` (`uj_steps` dict; `update_duration()` = Σ weight × `user_time_spent`; concat sites like `self.devices + self.uj_steps` adjusted; `param_descriptions`)
- `efootprint/core/usage/usage_journey_step.py` (`jobs` dict; weighted delay accumulation in `hourly_avg_occurrences_per_usage_pattern`; static weight labels "Times per journey" / "Times per step" / "Times per occurrence" set at normalization)
- `efootprint/core/usage/edge/recurrent_server_need.py` (`jobs` dict; `param_descriptions` drops the duplicate-entry idiom)
- `efootprint/core/usage/job.py` (all four `.count(self)` sites → dict lookups; step-side occurrences = journey starts × step weight × job multiplier)
- `efootprint/api_utils/version_upgrade_handlers.py` (new handler: `"uj_steps"`/`"jobs"` id-lists → count dicts, duplicates → n; format version bump)
- Construction sites across builders, default/doc objects, and tests (mechanical churn)
- `CHANGELOG.md`

**Tests added/changed:**
- Weighted duration, job × step composition, RSN job multipliers, per-relationship independence (same job, different multiplier in two steps), 0-weight, validation rejection.
- Occupancy-window tiling invariant (Σ step windows = journey duration) with fractional weights.
- JSON round-trip with non-default weights; upgrade-handler test on a pre-feature fixture containing duplicate job entries.
- All-multipliers-at-1 integration test asserting results identical to pre-change baselines.

**Acceptance:**
- Full library pytest suite green; a pre-feature system JSON loads and computes identical results; spec §2 library-side criteria met. Released to PyPI after merge (version bump per library release process).

**Depends on:** Task 1.

---

## Task 3 — Interface adopts the new library; parent panels gain weighted tables (repo: e-footprint-interface)

**Status:** Done (against the editable local e-footprint 22.0.0 — PyPI pin deferred to release; `pyproject.toml`/`poetry.lock` deliberately left out of the commit)

**Goal:** Bump `efootprint`, absorb the dict semantics, and deliver the first user-visible change: the journey panel's steps table and the step/recurrent-need panels' jobs tables render as weighted (`dict_count`) tables in journey order, with "Times per…" wording. Everything else behaves as before.

**Files touched:**
- `pyproject.toml` / `poetry.lock` (released version from PyPI)
- `model_builder/domain/` + `application/use_cases/` sites that read or mutate `uj_steps` / `jobs` as lists (accordion children, add-step/add-job flows write `{child: 1}` entries, `system_validation_service.py`)
- `theme/static/scripts/dict_count.js` (render rows by iterating the insertion-ordered selected map, all dict fields)
- `model_builder/adapters/ui_config/field_ui_config.json` (count-column wording for `uj_steps` / `jobs`; class-qualified keys if the shared `jobs` attr name needs different labels per parent class)
- `model_builder/domain/reference_data/modeling_templates/` JSONs (regenerate to current format, or rely on load-time upgrade — pick one and test it)
- `CHANGELOG.md`

**Tests added/changed:**
- Jest: `dict_count.js` ordering and value edit.
- Unit: form generation for the three dict fields (ordering, wording), form-data parsing.
- Integration: edit journey/step via parent panel with non-default counts; create step/job from canvas still links with count 1; template models load.

**Acceptance:**
- Full interface pytest + jest green; building, editing, saving, downloading and re-uploading a model with weights works end to end; uploading a pre-feature JSON works; `pyproject.toml` references PyPI.

**Depends on:** Task 2 (released).

---

## Task 4 — Generalize dict-relationship editing; membership sections (repo: e-footprint-interface)

**Status:** Done

**Goal:** The annotation-driven, cached (parent class, child class) → dict attribute resolution replaces the EdgeDeviceGroup-only logic in the dict-mutation endpoints, and child panels gain membership sections: "Used in usage journeys" (step), "Used in usage journey steps" / "Used in recurrent server needs" (job) — with per-parent count edit, unlink, and "Add to…" select.

**Files touched:**
- `model_builder/adapters/views/views_dict_mutation.py` (annotation-driven resolution; computed once and cached)
- `model_builder/templates/model_builder/side_panels/edit/group_membership_section.html` + the view code building its context (generic over dict relationships; titles/labels from `field_ui_config.json`)
- `model_builder/adapters/ui_config/field_ui_config.json` (membership titles, "Add to…" labels)

**Tests added/changed:**
- Unit: resolution over all modeling classes (the cached map matches every `ExplainableObjectDict[X]` init annotation).
- Integration: update-count / link / unlink through the endpoints for all three new relationships; step and job panel membership sections render and mutate correctly.
- Edge-group regression: existing edge inline-count and membership tests stay green on the generalized paths.

**Acceptance:**
- A job's "times per step" is editable from the job's own panel and stays consistent with the step panel's table; edge device group UX unchanged; full pytest + jest green.

**Depends on:** Task 3.

---

## Task 5 — Canvas inline counts and creation-flow field (repo: e-footprint-interface)

**Status:** Done

**Goal:** The remaining spec §4 surfaces: always-visible inline "× n" count on step rows and job chips (immediate recalculation, no unlink ✕ on these rows), 0-multiplier dimming, and the multiplier field in creation panels when created from a parent.

**Files touched:**
- `model_builder/templates/model_builder/object_cards/partials/group_entry_count_unlink.html` (count-only mode)
- `model_builder/templates/model_builder/object_cards/journey_card.html`, `journey_step_card.html`, `resource_need_card.html`, `resource_need_with_accordion_card.html` (inline count after step name / inside job chip, click propagation stopped; dimming at 0)
- Creation flows: add panel + create use case (relationship field prefilled at 1 when `efootprint_id_of_parent_to_link_to` is present)
- `specs/architecture.md` (one-line mention: dict relationships now cover journeys/steps/needs with shared inline-count UX)
- `CHANGELOG.md`

**Tests added/changed:**
- Integration: inline count change posts and recomputes; creation with a non-default multiplier lands the right dict entry.
- E2E: extend the existing edge inline-count Playwright pattern to the journey canvas (edit a step weight and a job count inline, observe recalculation and dimming at 0).

**Acceptance:**
- All spec §2 success criteria met end to end; full pytest + jest + e2e green.

**Depends on:** Task 4.

---

## Ordering rationale

Library before interface because the interface consumes released `efootprint` (constitution §2.4 forbids merging with a local path dependency). Task 1 is split from Task 2 as "infrastructure landed but unused": the normalizer and the dict-as-relationship guarantees are independently reviewable and de-risk the big conversion. Task 2 deliberately aggregates the three attribute conversions, the calculation rewiring, and the upgrade handler — splitting them would leave the suite red or require throwaway shims, and together they form the single behavioral statement "weights exist and old models are unaffected". Task 3 bundles the dependency bump with the `dict_count` ordering fix and the parent-panel tables because the bump alone already flips those panels to dict widgets (annotation-driven forms) — there is no working intermediate state without them. Tasks 4 and 5 are separate user-visible milestones (panel membership editing, then canvas/creation surfaces); 5 depends on 4's count partial generalization and ships the e2e that closes the spec.
