# Attributed-footprint explainability boundaries

**Status:** Parked investigation.  
**Recorded:** 2026-08-28.  
**Related active feature:** `specs/features/attribution-memory-optimization/`.

## Problem encountered

`efootprint.core.attribution.attributed_footprint(obj, phase)` returns an hourly `ExplainableHourlyQuantities`, but it is
an on-demand function result rather than a calculated attribute attached to a `ModelingObject` reactive slot.

Arithmetic initially represents a derivation through `left_parent` and `right_parent`. Attached calculated attributes
are finalized when the framework assigns their modeling-object container: their nested formula is retained and their
arithmetic parents are cleared. The on-demand attributed-footprint result never crosses that attachment boundary, so its
formula is not finalized. Calling `explain()` currently renders an empty derivation resembling:

```text
Attributed energy footprint =  =  = <hourly result summary>
```

The hourly values, plotting and period sums are correct; only the displayed derivation is missing.

## Why the straightforward fix is problematic

The attribution memory experiment finalizes the running result after each impact source so its arithmetic parents can be
released before that source's transient attribution structures are evicted. This makes `explain()` functional, but the
reference five-pattern smart-building model produces a 337,627-character usage formula.

That formula is not evidence of duplicated impact:

- the result's 43,800 float32 hourly values are byte-identical before and after the optimization;
- period sums are identical and attribution conservation tests pass;
- the target receives 175 atoms from 74 sources: one network, seven servers and 66 edge appliances;
- expanding the atoms yields 597 additive terms, 1,995 multiplications, 1,122 divisions and 3,321 leaf occurrences
  representing 894 distinct value objects.

The expression becomes enormous because an attribution atom is a temporary arithmetic result emitted by a generator. It
is neither an attached calculated attribute nor an ancestor-free root, so it is not an explanation boundary. Formula
finalization recursively expands it until reaching ordinary attached inputs and calculated attributes.

Deleting a `computed_structure` cache does **not** cause this expansion. Structure eviction only drops the slot's cached
reference and preserves reactive dependency edges; it does not detach or mutate explainable values inside the structure.
The expansion is caused by explicitly materializing the previously missing attributed-footprint formula.

## Why atoms cannot simply become calculated attributes

Atoms are numerous, short-lived projections over source-specific containment coordinates. Giving every atom a normal
calculated-attribute address would introduce combinatorial reactive slots, caching and persistence concerns for values
whose purpose is streaming attribution. It would blur the current distinction between modeled calculated state and
temporary attribution projections.

Making an atom or per-source subtotal act as a formula boundary without making it a calculated attribute would therefore
introduce a new framework pattern: an **ephemeral explanation boundary**.

## Required properties of a future solution

An ephemeral boundary should:

- appear as one meaningful term in its parent's formula;
- retain its label, value summary and source/coordinate identity;
- allow a user to inspect its own deeper derivation;
- remain outside reactive caching and persistence unless deliberately promoted;
- avoid retaining the NumPy arrays and arithmetic value trees that the memory optimization is trying to release;
- preserve the independence of the reactive dependency graph from cached values.

These requirements imply separating lightweight symbolic explanation metadata from live numeric ancestry, or recomputing
details lazily when requested. A label/value-only source subtotal is insufficient because it makes deeper explanation
impossible. Keeping today's nested `ExplainableObject` references is also insufficient because those references can keep
large hourly arrays alive.

## Memory evidence and current fallback

For one non-zero edge usage pattern in the five-pattern reference model:

| Cold read | Baseline peak RSS | Source eviction only | Eviction + formula finalization |
|---|---:|---:|---:|
| Manufacturing | 1,322.5 MiB | 722.6 MiB | 496.8 MiB |
| Usage | 2,074.5 MiB | 962.5 MiB | 614.9 MiB |
| Both phases retained | 2,819.6 MiB | 1,329.7 MiB | 752.3 MiB |

Source eviction without parent finalization preserves current explanation behavior and substantially helps a single
temporary result. It does not bound multiple retained results: five usage-pattern results peaked at 2,423 MiB, compared
with 2,344 MiB on the baseline, because every returned arithmetic tree retained its recomputed generation. Formula
finalization held the same run to 657 MiB but exposed the enormous derivation.

Until explanation boundaries are designed, the active memory optimization must choose explicitly between the safe but
partial eviction-only gain and the larger gain coupled to a formula-presentation change.

## Questions for promotion to an active feature

1. What is the meaningful immediate explanation layer: atom, impact source, stream, or another attribution concept?
2. Should deeper detail be stored symbolically or recomputed lazily on demand?
3. Can the existing serialized `explain_nested_tuples` representation be adapted without resolving references back to
   live value objects?
4. What API should expose a temporary explanation boundary without pretending it is a reactive calculated attribute?
5. How should Python `explain()` and the interface's calculation-graph presentation handle very large derivations?
6. What memory and latency bounds must the new representation meet on long, multi-pattern systems?
