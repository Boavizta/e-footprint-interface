# Attribution memory optimization — Cold-context implementation notes

These notes preserve load-bearing details discovered by the experiments. They supplement `plan.html` and `tasks.md`;
they do not introduce additional scope.

## Existing experiment

The local sibling worktree `../e-footprint-source-eviction/` is on branch
`experiment/source-scoped-attribution-eviction`, based on e-footprint `dev` commit `d76b858d`. Its changes are
deliberately uncommitted. Treat the diff as experimental evidence, not as an authoritative patch: inspect it, reproduce
the tests, and implement/review it through Tasks 1 and 2.

## Task 1: Sankey source lifetime

The tested implementation adds `transient=True` to `computed_structure`, rejects the contradictory combination
`serialize=True, transient=True`, and exposes value eviction that calls the slot's existing `_drop_value()` without
invalidating its dependency edges.

Only attribution-specific helper structures are marked transient:

- `EdgeDevice`: four structures;
- `ServerBase`: three structures;
- `Storage`: two structures.

`System.impact_repartition_matrix` must append one source's already-reduced `impact_repartition_rows` before evicting
that source's transient structures. The period-sum rows remain cached; only the hourly helpers used to build them are
released. A future input edit still traverses the preserved graph edge and invalidates the rows/matrix. Their next pull
recomputes both the affected transient helpers and source rows.

`computed_structure` stores arbitrary raw values and does not attach them—or explainable objects nested inside them—to
the owning `ModelingObject`. Eviction therefore only drops the slot's strong reference. It does not call
`set_modeling_obj_container(None, None)` on structure contents and does not itself modify explanations.

## Task 2: exact attributed-footprint control flow

Keep the public signature:

```python
attributed_footprint(obj: ModelingObject, phase: LifeCyclePhases)
```

Replace the system-wide `atoms(system, phase)` loop with the same source order returned by `attribution_sources(system)`.
Within each source, retain the existing atom order and add each matching `atom.value` directly to the single running
`total`. After that source's atoms have been consumed:

1. finalize the running total's explanation;
2. clear the finalized arithmetic value parents through that finalizer;
3. evict the source's transient attribution structures;
4. continue adding the next source's matching atoms to the same total.

Do **not** first aggregate into a per-source numerical subtotal and then add the subtotal to `total`. That changes
float32 addition grouping and produced slightly different period sums in an early harness. Progressive finalization of
the one running total preserves the original numerical operation order; both phase arrays then matched clean `dev`
byte-for-byte.

Equivalent control-flow sketch:

```python
total = EmptyExplainableObject()
level = type(obj)
for system in obj.systems:
    for source in attribution_sources(system):
        for atom in source.attribution_atoms(phase):
            node = next((node for node in atom.chain() if isinstance(node, level)), None)
            if node == obj:
                total += atom.value
        total.finalize_explanation()
        evict_attribution_source_intermediates(source)
```

Preserve the existing phase-specific label and final `.to(u.kg)` behavior.

## Composable formula finalization

Today `ExplainableObject.set_modeling_obj_container()` performs formula materialization and parent release inline when a
calculated value is attached. Extract that behavior into an idempotent public method:

```python
def finalize_explanation(self):
    if self.left_parent is not None or self.right_parent is not None:
        self.explain_nested_tuples = self.compute_explain_nested_tuples()
        self.left_parent = None
        self.right_parent = None
    return self
```

Have `set_modeling_obj_container()` call it. Progressive attributed-footprint calculation then uses the same lifecycle
operation without pretending its temporary total is a calculated attribute.

A finalized but unattached running total must remain composable: after more arithmetic, a later finalization must reuse
its stored nested formula. Update `compute_explain_nested_tuples()` with this ordering:

1. When `return_self_if_self_has_mod_obj_container_or_no_ancestors=True`, first preserve the existing boundary rule:
   return `self` if it is attached or has no direct ancestors; retain the existing invalid-source check.
2. Otherwise, if `self.explain_nested_tuples` already exists, return it.
3. Only then recurse through `left_parent` and `right_parent`.

The ordering is essential. Checking the stored formula before the established attached-boundary rule expands ordinary
calculated attributes and breaks existing concise explanations. Never checking the stored formula makes a progressively
finalized unattached value impossible to compose and raises because its parents have already been cleared.

## Explanation behavior accepted for this feature

The clean-`dev` on-demand attributed result is never attached/finalized. Although it has arithmetic parents,
`explain()` reads `explain_nested_tuples` and currently renders an empty formula (`label = = = value`). Task 2 fixes
that bug as a consequence of progressive finalization.

On the five-pattern reference model, the complete usage formula contains 175 matching atoms from 74 sources and renders
to 337,627 characters. This is not caused by cache eviction and is not evidence of duplicated impact. Atom values are
temporary arithmetic expressions rather than attached explanation boundaries, so their formulas expand down to normal
attached attributes. The hourly arrays remain byte-identical and conservation tests pass.

Shipping the complete formula is approved. A future compact, deep-divable ephemeral explanation-boundary pattern is
parked under `specs/backlog/attributed-footprint-explanability/` and is not a Task 2 dependency.

## Benchmark correctness trap

Relationships read through a `System` can yield `ContextualModelingObjectAttribute` wrappers. Passing such a wrapper as
the attribution target makes `type(obj)` the wrapper class; no atom chain contains a node at that level, so the function
traverses and allocates the full attribution path but returns zero. This produced initially plausible yet semantically
invalid memory measurements.

For the reference benchmark, deliberately select the underlying object (the experiment used
`list(system.edge_usage_patterns)[0]._value`) and assert non-zero manufacturing and usage period sums before accepting a
measurement. Production behavior for contextual targets is a separate concern and must not be silently folded into this
optimization.

## Required verification

- Framework test: a formula can be finalized, used as a parent in further arithmetic, finalized again, and still
  explain correctly; both finalized objects have cleared value parents.
- Regression tests: existing concise formulas for attached calculated attributes remain unchanged.
- Attribution tests: both manufacturing and usage arrays, shape, dtype, start date, unit, label and sums match clean
  `dev`; `explain()` contains the complete non-empty derivation.
- Reactive test: an evicted transient structure is void, its cached descendant remains coherent, and a later input edit
  invalidates that descendant through the preserved edge.
- Repeated-target benchmark: retain five non-zero attributed results, not contextual-wrapper zero results.
- Full library suite and the fresh-process measurements specified in `plan.html` must pass before committing Task 2.
