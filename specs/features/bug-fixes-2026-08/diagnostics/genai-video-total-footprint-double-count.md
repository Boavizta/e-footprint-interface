# GenAI video `total_footprint` exceeds category totals: hourly rounding accumulates over the modeling period

- **Status:** CONFIRMED
- **Confidence:** high — the shipped template reproduces the discrepancy, the public total is exactly the rounded form of the unrounded category aggregate, and removing the device fabrication stream from the calculation disproves double counting as the mechanism.
- **Reported:** On the unmodified GenAI video template, `total_footprint` sums to 10,512 g while `fabrication_footprints` + `energy_footprints` sum to 10,213 g; the reported 299 g difference appeared to equal `Device.instances_fabrication_footprint`. The interface charts and Sankey show the category-conserving 10.2 kg, so the report identified direct API reads of `total_footprint` as the affected surface. The discrepancy is real, but the double-counted-device hypothesis did **not** hold: the apparent equality is a rounding-scale coincidence.

## Root cause

`System._objects_by_category()` assigns every linked object to the first matching category and then stops, so one object cannot be counted in multiple categories (`e-footprint/efootprint/core/system.py:192-200`). Both public breakdowns read exactly those categorized objects: fabrication reads `instances_fabrication_footprint`, and energy reads `energy_footprint` (`e-footprint/efootprint/core/system.py:202-223`). The `total_footprint` getter independently snapshots the same `_objects_by_category()` result and sums the same two footprint attributes (`e-footprint/efootprint/core/system.py:277-296`). There is therefore no separate device term in the total formula.

The divergence is introduced only at the getter's return statement: `round(total_footprint, 4)` rounds the **hourly kg timeseries** before any caller sums it over the period (`e-footprint/efootprint/core/system.py:293-298`). `ExplainableHourlyQuantities.__round__` applies `numpy.round` to every array element, confirming that the four decimals are per-hour rather than period-total precision (`e-footprint/efootprint/abstract_modeling_classes/explainable_hourly_quantities.py:156-160`). A four-decimal kg quantum is 0.1 g per hour; repeated across the template's 8,760 hours, sub-quantum errors can accumulate to hundreds of grams.

Reproduction on 2026-08-31 with e-footprint 23.0.0 loaded the committed inputs-only GenAI video template (`e-footprint-interface/model_builder/domain/reference_data/modeling_templates/introductory/genai_video.json:1-43`) through `json_to_system`, then compared:

```text
system.total_footprint.sum()                                      10511.999130 g
sum(system.total_fabrication_footprints +
    system.total_energy_footprints).sum()                         10212.806702 g
difference                                                          299.192429 g
sum(device.instances_fabrication_footprint)                         299.651265 g
round(unrounded_category_timeseries_in_kg, 4).sum()               10511.999130 g
system.total_footprint == round(unrounded_category_timeseries, 4)          True
```

This directly tests the hypothesis: the exact observed difference is not the exact device footprint (they differ by about 0.459 g), while applying the production rounding operation to the category aggregate reproduces `total_footprint` exactly. A second discriminating calculation removed device fabrication before rounding: its raw total was 9,913.155 g, its rounded-hourly total was 9,636.000 g, and adding the 299.651 g device stream changed the rounded result by 876.001 g. That non-linear quantization behavior is incompatible with a device being added twice and explains why the displayed 299 g figures can look related.

The laptop is a legitimate category contribution, not an exceptional total-only term: the template authoring path attaches `Device.laptop()` to the single usage pattern (`e-footprint-interface/scripts/intro_template_scenarios/genai_video.py:133-150`), and `Device.instances_fabrication_footprint` is defined as the sum of its per-usage-pattern fabrication values (`e-footprint/efootprint/core/hardware/device.py:141-154`).

The current tests miss this because `tests/test_system.py` checks the fabrication and energy category dictionaries separately (`e-footprint/tests/test_system.py:255-259`, `e-footprint/tests/test_system.py:285-314`) but has no assertion that `total_footprint` conserves their combined value. Its fixture uses whole-kg hourly values (`e-footprint/tests/test_system.py:34-56`, `e-footprint/tests/test_system.py:172-180`), for which four-decimal kg rounding is invisible. The focused current suite passes (`poetry run pytest tests/test_system.py -q`: 30 passed), confirming the coverage gap rather than contradicting the reproduction.

The interface's plotted values are insulated because `EmissionsCalculationService` builds every series from `total_energy_footprints` and `total_fabrication_footprints` (`e-footprint-interface/model_builder/domain/services/emissions_calculation_service.py:63-78`, `e-footprint-interface/model_builder/domain/services/emissions_calculation_service.py:92-116`). It reads `total_footprint` only to select a display unit (`e-footprint-interface/model_builder/domain/services/emissions_calculation_service.py:84-94`), so this scenario's plotted magnitudes conserve the categories, although a value very near a unit-selection threshold is an adjacent theoretical presentation risk. Sankey values come from the attribution matrix fold, which sums each matrix row without normalization or rescaling (`e-footprint/efootprint/core/attribution/__init__.py:194-224`); this matches the architecture invariant that atom sums equal eager stream totals and renderers only group them (`e-footprint/specs/architecture/attribution.html:3-6`).

## Fix approach

Remove the `round(..., 4)` operation from `System.total_footprint` and return the already-unit-normalized, labeled aggregate directly. This is the smallest correct fix: it preserves category membership, explainability, dependency tracking, units, and the existing aggregation order while making the total conserve its component streams. It also restores the documented boundary that Pint quantities flow through calculations unchanged and magnitude-aware formatting happens only at render time (`e-footprint/specs/architecture/layers-and-modeling.html:46`).

Do not special-case or subtract `Device.instances_fabrication_footprint`; the device is already present exactly once and such a change would undercount real fabrication. Do not round only after `.sum()` inside the getter: `total_footprint` is contractually an hourly timeseries (`e-footprint/efootprint/core/system.py:277-279`), and presentation rounding belongs to callers/renderers. Rebuilding the getter from the public category properties would also fix the number, but is a broader and potentially slower rewrite than removing the sole lossy operation; the current snapshot avoids repeated object-graph walks intentionally (`e-footprint/efootprint/core/system.py:282-286`).

## Files to touch

- `e-footprint/efootprint/core/system.py:277-298` — return the unrounded total timeseries.
- `e-footprint/tests/test_system.py:255-314` — add a regression proving the system total equals the combined category total for fractional hourly kg values that rounding would materially distort.
- `e-footprint/CHANGELOG.md` — record the corrected API total under `Unreleased`, as required by the library quality gate (`e-footprint/specs/constitution.md:18-25`).

## Tests

- Add a focused `System` unit regression in `e-footprint/tests/test_system.py` using fractional per-hour kg inputs below/around the fourth decimal and enough hours to expose accumulated quantization. Assert that both the hourly result and its period sum conserve `sum(total_fabrication_footprints.values()) + sum(total_energy_footprints.values())`.
- Keep the regression generic rather than depending on the interface-owned GenAI fixture; the defect is in the library aggregation formula and affects any long, low-intensity system.
- Run `poetry run pytest tests/test_system.py`.
- Run `poetry run pytest tests/api_utils_tests/test_minimal_serialization_contract.py`: `total_footprint` is a serialized computed slot, and existing coverage requires a materialized same-version total to round-trip identically (`e-footprint/tests/api_utils_tests/test_minimal_serialization_contract.py:44-66`) and invalidate after edits (`e-footprint/tests/api_utils_tests/test_minimal_serialization_contract.py:137-158`).
- Run the full e-footprint pytest suite, the constitutional completion gate (`e-footprint/specs/constitution.md:18-25`). As downstream validation, load the GenAI video template in e-footprint-interface and confirm the headline API total, category chart, and Sankey agree at approximately 10.2 kg; no interface code change is expected.

## Acceptance criteria

- For the unmodified GenAI video template, `system.total_footprint.sum()` equals the sum over all `system.total_fabrication_footprints` and `system.total_energy_footprints` categories, subject only to normal float32 arithmetic tolerance; it no longer reports approximately 10.512 kg against approximately 10.213 kg of components.
- The returned `total_footprint` remains an explainable hourly kg timeseries labeled `Total carbon footprint` and retains dependencies on every included source.
- Device fabrication remains included exactly once.
- Category chart and Sankey totals remain unchanged and agree with the corrected API total at display precision.
- Serialization round-trip and invalidation tests pass.

## Risks and side effects

- API consumers will receive more precise hourly magnitudes and a lower/correct period total where the old per-hour rounding biased the result. Any consumer snapshotting the erroneous number will observe an intentional correction.
- Removing the rounding node changes the human-readable explanation formula for `total_footprint`, but not its inputs or dependency cone. This is desired because calculation precision must not be a presentation concern.
- `total_footprint` is marked `serialize=True` (`e-footprint/efootprint/core/system.py:277`), and same-version JSON loads trust stored computed caches without recomputation (`e-footprint/efootprint/api_utils/json_to_system.py:155-180`; `e-footprint/specs/architecture/persistence.html:3-10`). A normal patch release version change will make older cached totals version-mismatched and therefore lazily recomputed. If the fix is distributed without changing `efootprint.__version__`, an already-exported 23.0.0 values-bearing file could retain its rounded cached total until an input invalidates it; release packaging must not do that.
- The committed GenAI template is inputs-only (its `System` entry contains no `total_footprint` or calculation graph at `e-footprint-interface/model_builder/domain/reference_data/modeling_templates/introductory/genai_video.json:35-43`), so it needs neither regeneration nor data migration.

## Flags

- **Invariant:** total footprint must conserve the fabrication and energy category streams. This is consistent with the attribution conservation invariant (`e-footprint/specs/architecture/attribution.html:3-6`) and with the display-boundary rule (`e-footprint/specs/architecture/layers-and-modeling.html:46`).
- **Serialization/migration:** no JSON shape changes, schema bump, or migration handler is required. Preserve the existing `serialize=True` contract and verify round-trip/invalidation. Ensure the eventual release version differs from 23.0.0 so old values-bearing caches are demoted rather than trusted.
- **Cross-repository ordering:** implementation lands in `e-footprint` only because the interface constitution makes the library the owner of modeling truth (`e-footprint-interface/specs/constitution.md:9-12`). Then validate e-footprint-interface against that library revision; no interface file or template regeneration is part of the fix.
- **Local validation:** the exact reproduction completed, as did `tests/test_system.py` (30 passed). The reproduction constructed `BoaviztaCloudServer` from template inputs and contacted the configured Boavizta API, so small source-data drift is possible; the identity `total_footprint == round(category aggregate, 4)` is deterministic and is the causal evidence. The full library suite, serialization suite, and interface UI/Sankey checks were not run during this diagnosis-only pass; none is known to be unavailable locally.

## Decisions

- 2026-08-31 — Diagnose as a library-wide precision/conservation bug, not a GenAI-video or device-allocation bug.
- 2026-08-31 — Fix at `System.total_footprint` by removing calculation-layer rounding; retain all category and device membership unchanged.
- No user decision fork remains.

