# Scoped simplified-input catalog — refactor planning context

Captured on 8 October 2026 from an audit of simplified-inputs implementation and local performance measurements.

## User intent and status

Prepare a focused refactor that avoids building the complete simplified-input catalog where a caller needs only a subset, if the measured savings justify the complexity. The user requested this context dump so they can run `spec-plan` in a fresh session.

This is planning input, not an approved implementation plan. The user has not approved the recommendation's precise scope, a new API, or implementation. Do not infer approval of every possible optimization below. By default this workspace is discussion-only; edits need explicit authorization. Creating this feature working set was explicitly authorized.

Driving repository: **e-footprint-interface**. No library changes appear necessary. Read [spec.html](spec.html), then the architecture router and owning pages before planning. Do not generate implementation tasks or implement application changes during `spec-plan`.

Suggested fresh-session prompt:

> Use spec-plan for scoped-simplified-input-catalog. Read its spec.html and context.md, recheck the current callers and contracts, and propose the smallest justified scope. Preserve current behavior. Distinguish the empty-settings shortcut, scoped readers, and write-path changes; do not treat the earlier audit recommendation as an approved design.

## Current implementation and nearby changes

- [domain/services/simplified_inputs.py](../../../model_builder/domain/services/simplified_inputs.py) owns `FieldAddress`, `FieldDescriptor`, `FieldCatalog`, `input_eligibility()`, `build_catalog()`, `complete_selection()`, and `validate_definition()`.
- `build_catalog(model_web, *, can_edit_timeseries)` loops over all hydrated objects and all constructor parameters. It computes eligibility, resolves conditional controller paths, builds reverse dependent links, then propagates ineligibility back to controllers.
- Constructor signatures are already cached by the library's `get_init_signature_params()`. Repeated per-instance type/eligibility checks and descriptor allocation remain substantial.
- [adapters/presenters/simplified_inputs.py](../../../model_builder/adapters/presenters/simplified_inputs.py) exposes `input_catalog()` and `build_workspace_context()`. Even when `addresses` selects one field, the presenter currently builds and scans the full catalog first.
- [adapters/forms/simplified_input_context.py](../../../model_builder/adapters/forms/simplified_input_context.py): `bookmark_context()` builds the full catalog when the caller supplies none. It needs the requested descriptor's eligibility/controller, saved settings, and the included controller's label.
- Full catalogs are normally built **once per request and reused**, not once per rendered field. Existing reuse should be preserved. Error recovery intentionally loads fresh accepted state and consequently builds a fresh catalog.
- `ModelWeb` hydration happens before catalog construction. Scoped catalogs alone do not avoid hydration, persistence, or HTML rendering.

Two nearby refactors are already committed:

- `00d17179` — `[REFACTO] Move interface config normalization into domain`. `normalize_interface_config()` lives in [domain/interface_config.py](../../../model_builder/domain/interface_config.py), imported by repositories and migration handlers.
- `bc0b4cb5` — `[REFACTO] Let form strategies identify bookmark field owners`. `FormStrategy.iter_creation_fields()` / `iter_edition_fields()` provide owner–field pairs. `WithStorageFormStrategy` adds nested Storage pairs. Generic bookmark code no longer knows Storage context prefixes. Wrappers declare `nested_input_owner_attributes` for creation settings.

Use those owner–field iterators when identifying an edit panel's requested subset; do not reintroduce Storage-specific discovery into the builder.

At capture time the checkout also contains unrelated changes, including local dependency configuration, agent tooling, simplified-inputs plan edits, and an uncommitted form-dependency invariant test. Preserve them. Recheck Git status and current dependencies in the next session.

## Catalog consumer audit

| Operation | Current entry point | Required information | Assessment |
| --- | --- | --- | --- |
| Configure workspace | `views_simplified_inputs.simplified_inputs()` → `build_workspace_context(configure=True)` | All eligible fields, dependency links, and explanations for unavailable controllers | Keep the complete catalog. |
| Consumption workspace / imported-model opening | `simplified_inputs()` and `views.render_model_builder()` → `build_workspace_context(configure=False)` | Included fields plus their required dependency closure | Candidate if saved selection is sparse; benefit shrinks with broad selections. |
| Single-field refresh | `simplified_input_field()` → `build_workspace_context(addresses={address})` | One selected field and relevant dependency closure | Strong scoped-read candidate. |
| Focused timeseries panel | `simplified_timeseries_panel()` | Selection, eligibility, and editor for one field | Strong scoped-read candidate. Preserve supported-editor checks. |
| Lazy Sources bookmark controls | `simplified_input_bookmark()` → `bookmark_context()` | One field's eligibility/settings and its included controller's label | Strong scoped-read candidate. |
| Rejected-edit restoration | `_rejected_simplified_input()` → fresh `ModelWeb` → `render_input_fields_oob()` | Recovery addresses against the freshly stored, accepted model | Candidate, but preserve fresh-state restoration; do not reuse the possibly mutated request model/catalog. |
| Object edit panel | `FormContextBuilder.build_edition_context()` | Strategy-exposed fields and their required dependent closure | Candidate with a modest end-to-end benefit on large models. |
| Sources table | `views.source_table()` | Descriptors for source-row addresses plus relevant dependencies | Lower priority: rows may cover much of the model, and some represent computed rather than constructor fields. |
| Simplified value edit | `edit_simplified_input()` → `EditSimplifiedInputUseCase` | Submitted field and all affected dependent chains, including other owners | Technically scopeable; stronger behavioral risk than reads. Keep full catalog initially unless justified. |
| Configure save / bookmark settings patch | `save_simplified_inputs()` / `patch_simplified_inputs()` → `UpdateSimplifiedDefinitionUseCase` | Entire retained definition, submitted entries, explicit exclusions, and dependency completion | Cannot safely scope to just patched addresses under the current validation contract. Keep full catalog initially. |
| Ordinary create/edit/delete, including relationship mutations | `persist_structural_change()` → `reconcile_simplified_definition()` | Surviving retained settings, pending settings, and dependency completion after mutation/hooks | Possible subset; simpler initial opportunity is avoiding a catalog when no retained or pending field settings exist. |

Source owners:

- [views_simplified_inputs.py](../../../model_builder/adapters/views/views_simplified_inputs.py)
- [views.py](../../../model_builder/adapters/views/views.py)
- [form_context_builder.py](../../../model_builder/adapters/forms/form_context_builder.py)
- [application/use_cases/simplified_inputs.py](../../../model_builder/application/use_cases/simplified_inputs.py)
- [create_object.py](../../../model_builder/application/use_cases/create_object.py), [edit_object.py](../../../model_builder/application/use_cases/edit_object.py), [delete_object.py](../../../model_builder/application/use_cases/delete_object.py)
- Relationship mutations also pass the catalog factory through their ordinary edit use cases.

Creation-form bookmark rendering itself does not build a catalog: it uses generated eligibility and candidate requirement metadata. Distinguish this from persistence of pending creation settings.

## Behavioral constraints

1. **Preserve a single eligibility contract.** Do not duplicate a simpler rule inside each narrow view.
2. **Visible form exclusions are not simplified eligibility.** `attributes_to_skip_in_forms` controls ordinary layout. Simplified inputs may expose skipped constructor attributes.
3. **A controller needs its full dependent closure.** Example: API Provider → API Model → Resolution on every linked video job. A subset limited to the controller's object is incorrect.
4. **Unsupported dependents make their controllers ineligible transitively.** Checking only the requested annotation misses this. Include the relevant dependent closure before propagating ineligibility.
5. **Dependent lookup is reverse lookup.** Following a requested field's `depends_on` gives its controller, not the objects that depend on that field. Cross-object reverse links may require model-wide discovery even for a small requested subset.
6. **Instance-specific timeseries support matters.** Class annotations alone do not determine whether the saved builder/value is editable. Preserve the lightweight editor-support callback and avoid instantiating builders during eligibility checks.
7. **Unknown / structural / computed-only fields retain current handling.** Scope construction must not manufacture eligibility for a source row that is absent from constructor descriptors.
8. **Settings writes validate more than active selections.** Retained help-only entries and explicit exclusions are part of the existing definition. Scope cannot be only included fields or the patch's keys.
9. **Structural reconciliation runs after mutation and hooks.** Relinking can change dependency ownership; creating a job can add a newly required dependent. Discover links against the resulting model.
10. **Recovery must use accepted persisted state.** Failures may occur before persistence, during persistence, or during presentation after acceptance. Preserve existing restoration semantics and HTTP error behavior.
11. **No new hydration or persistence contract is implied.** This feature concerns catalog work, not a partial `ModelWeb` loader, stored metadata index, or model serialization changes.

## Measured evidence

Environment: local Python 3.12.11, installed editable `efootprint` pointing to the companion repository. Measurements were made on 8 October 2026. Absolute timings depend on machine/process/GC state; do not present microbenchmark ratios as browser speedups.

Synthetic **real object graphs**, not mocked catalogs: each branch has one Server, Storage, Job, UsageJourneyStep, UsageJourney, and UsagePattern. Branches share one Device, Network, and Country; there is one System. Usage patterns have one-month hourly input data. The model is serialized and hydrated through the ordinary `ModelWeb` / in-memory repository path before catalog-only timing.

| Objects | Branches | Constructor descriptors | Conditional links |
| ---: | ---: | ---: | ---: |
| 100 | 16 | 670 | 16 |
| 1,000 | 166 | 6,820 | 166 |
| 5,002 | 833 | 34,167 | 833 |

### Complete catalog versus edit context

21 repetitions per size, repeated in two independent process runs. Warmed code, GC enabled; timings exclude model construction/hydration and HTML rendering. Alternated ordinary edit-context calls with calls reusing the exact same catalog through a temporary in-process patch. Returned context dictionaries were equal.

| Objects | Full catalog median | Server edit-context median | Same context reusing catalog |
| ---: | ---: | ---: | ---: |
| 100 | 1.2 ms | 1.8 ms | 0.6 ms |
| 1,000 | 12.4 ms | 15.6 ms | 3.0 ms |
| 5,002 | 95.5 ms | 108.3 ms | 14.4 ms |

Catalog represented roughly 66%, 79%, and 88% of context-building time. Occasional longer GC samples occurred; medians are not worst-case guarantees. Profiling pointed primarily to repeated eligibility/type checks across all fields, rather than timeseries editor discovery.

### Actual edit-panel view, server-side

Nine measured calls after one warm-up through `open_edit_object_panel()`, including real hydration, context building, HTML rendering, and headers. Only repository retrieval was replaced by an in-memory payload source. No browser/network/session middleware/cache-fetch timings.

| Objects | Catalog median | Whole view median | Median per-request catalog share |
| ---: | ---: | ---: | ---: |
| 100 | 1.2 ms | 17.8 ms | 7% |
| 1,000 | 12.6 ms | 66.5 ms | 19% |
| 5,002 | 66.5 ms | 401.3 ms | 18% |

The share column is the median of per-request ratios, not the ratio of separate medians. Hydration remained a larger cost. Extra cache/network/browser time generally reduces the catalog's share of click latency. These numbers are not a production or browser benchmark.

### Audit-only scoped prototype

No application implementation was changed. An ephemeral in-memory prototype:

1. Scanned each object's `conditional_list_values` to discover controller and dependent addresses.
2. Started from requested addresses and traversed dependent links, with a visited set.
3. Evaluated constructor eligibility and allocated descriptors only for the resulting closure.
4. Propagated ineligibility to controllers inside that closure.

Fifteen repetitions; one ordinary number (`Server.power`) and one controller (`Server.server_type`, requiring its instance count). Descriptor/link results matched the corresponding full-catalog results for these tested cases.

| Objects | Full catalog median | Focused number median, 1 field | Focused controller median, 2 fields |
| ---: | ---: | ---: | ---: |
| 1,000 | 13.577 ms | 0.197 ms | 0.183 ms |
| 5,002 | 103.767 ms | 1.034 ms | 1.015 ms |

This establishes potential savings and the low cost of sparse link discovery for these graphs. It does **not** establish equivalence for cross-object video chains, malformed settings, cycles, unsupported descendants, all source-row types, or recovery behavior. Those are implementation verification work. The prototype scanned conditional metadata directly; a production design must preserve the existing constructor-field boundary when discovering links.

Temporary scripts/results from the investigation were under `/tmp/benchmark_simplified_catalog*` and `/tmp/benchmark_edit_panel*`. They may disappear between sessions; this brief contains the retained evidence and methodology. The focused prototype was executed directly in an interpreter and was not saved. Recreate bounded benchmarks if the plan needs fresh measurements; do not depend on temporary files.

## Recommendation, complexity, and decisions for spec-plan

**Audit recommendation, not approved scope:**

- First assess a cheap no-field-settings/no-pending-settings shortcut in structural reconciliation. Preserve shape validation, title/guidance handling, rollback, and the existing final model save. An empty `FieldCatalog` may allow reuse of existing validation rather than a special validator. Recheck whether retained entries disappear during owner filtering before deciding the shortcut's exact condition.
- If further improvement is warranted, extend the existing catalog mechanism to accept requested addresses, sharing dependency discovery and eligibility rules. Preserve the full-catalog mode for Configure.
- Start with narrow reads: field refresh, focused timeseries, lazy bookmark, affected-field restoration; possibly edit panels and sparse consumption workspaces. Compare their benefit and implementation cost rather than including every reader automatically.
- Keep configuration/value/structural writes using full catalogs initially, apart from the independently justified empty-settings shortcut. Consider broader write scoping later only if evidence warrants its validation burden.
- Avoid persistent catalog caches, another stored model representation, partial hydration, or generic graph/query frameworks for this work.

Complexity assessment:

- Empty-settings shortcut: **low**, with meaningful benefit for ordinary models not using simplified field settings.
- Shared subset construction plus read integration: **moderate**. The algorithm is manageable; preserving existing dependency, eligibility, ordering, and error semantics is the main work.
- Scoping every write: **higher verification burden**, because retained definitions and changing cross-object links broaden the required scope.
- Full catalog: O(constructor fields + conditional links). A straightforward scoped design still discovers links across the model, then evaluates the requested closure: approximately O(objects + conditional links + requested/dependent fields). This is not constant-time access and savings shrink when the closure covers most of the model.

Decisions to resolve in the plan:

1. Is the initial scope just the empty-settings shortcut, or that plus shared scoped readers?
2. Which read callers belong in the first delivery, considering real model sizes and interaction frequency?
3. What exact subset contract preserves dependency closure and controller metadata without duplicating catalog rules?
4. How does the full mode share code without noticeably regressing its current cost?
5. What equivalence tests and bounded measurements are sufficient to justify the change?

The user previously agreed that optimizing one edit-panel catalog build alone was not compelling. The later audit identified broader reuse opportunities and an empty-settings shortcut, but the user has not yet accepted a wider implementation. Do not replace that tradeoff discussion with a blanket performance claim.

## Existing verification to reuse

- [tests/unit_tests/domain/test_simplified_inputs.py](../../../tests/unit_tests/domain/test_simplified_inputs.py): real cross-owner Provider → Model → multiple Resolutions; ineligible required input propagation; unknown fields; validation and selection closure; instance-specific timeseries support.
- [tests/unit_tests/adapters/forms/test_form_context_builder.py](../../../tests/unit_tests/adapters/forms/test_form_context_builder.py): edit/creation owner identity, advanced fields, candidate requirement metadata.
- [tests/unit_tests/adapters/views/test_views_simplified_inputs.py](../../../tests/unit_tests/adapters/views/test_views_simplified_inputs.py): lazy bookmark controls; focused timeseries; rendering only affected editors on large selected models; early and late failure restoration; accepted repository state.
- [tests/integration/test_simplified_inputs.py](../../../tests/integration/test_simplified_inputs.py): atomic edits, rejected exclusions, nested creation settings, creation hooks, newly required fields, structural relinking, deletion cleanup, persistence failures.
- Settings/repository tests cover metadata-only persistence without reserializing model objects; do not weaken that contract.

Plan targeted behavioral equivalence between full and scoped catalogs, including a controller with dependents on other owners and an ineligible descendant. Verify that empty-settings structural operations skip the catalog while preserving saves and rollback. Measure catalog-only and whole-request durations separately. Existing tests that only verify narrow editor rendering do not prove narrow catalog construction.

Owning documentation: [architecture index](../../architecture/index.html), [forms and relationships](../../architecture/forms-and-relationships.html), [workspace](../../architecture/workspace.html), [persistence](../../architecture/persistence.html), and [testing](../../testing.md). Any implemented catalog contract change should update the owning architecture page and the relevant AGENTS/CLAUDE guidance.
