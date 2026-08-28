# Attribution source-scoped eviction experiment — 2026-08-28

## Setup

- Source model: `2026-05-07 scenario C smart building system.json.json`, expanded from two to five edge usage patterns.
- Runtime: fresh macOS Python processes; 5 ms process-RSS sampler; automatic cyclic GC disabled during calculation.
- Baseline: clean e-footprint `dev` at `d76b858d`.
- Experiment: transient attribution structures, source-scoped eviction, and composable formula finalization.
- Target: the first underlying `EdgeUsagePattern`, whose manufacturing and usage results are both non-zero.

These are process-RSS comparisons, not Linux cgroup working-set measurements. Use them for relative algorithmic evidence;
Task 3 repeats the accepted implementation in the deployment-shaped Docker image.

## One target, three fresh processes per cell

| Scenario | Baseline peak RSS, median | Experiment peak RSS, median | Reduction | Baseline latency, median | Experiment latency, median |
|---|---:|---:|---:|---:|---:|
| Manufacturing | 1,322.5 MiB | 496.8 MiB | 62.4% | 0.896 s | 0.974 s |
| Usage | 2,074.5 MiB | 614.9 MiB | 70.4% | 1.129 s | 1.099 s |
| Manufacturing then usage | 2,819.6 MiB | 752.3 MiB | 73.3% | 1.383 s | 1.595 s |

The magnitude arrays have the same shape (`43,800` float32 hours) and byte hash in baseline and experiment. Start date,
unit, label and period sums also match.

## Five retained usage-pattern results

One fresh-process run retained all five returned hourly results:

| Variant | Peak RSS | Latency |
|---|---:|---:|
| Clean `dev` | 2,344 MiB | 1.66 s |
| Eviction without formula finalization | 2,423 MiB | 2.45 s |
| Eviction with composable formula finalization | 657 MiB | 2.33 s |

Eviction alone does not bound repeated reads because each returned arithmetic tree retains the evicted generation. Formula
finalization is therefore part of the memory mechanism, not merely a further micro-optimization.

## Formula finding

The clean function returns an `ExplainableHourlyQuantities`, but its on-demand result is never attached as a calculated
attribute and therefore never finalized. `explain()` currently produces an empty expression (`label = = = value`). The
experiment makes finalization composable across sources, retains the complete nested formula, and clears value parents.
The resulting usage formula is valid but 337,627 characters long for this model. This fixes missing explanation rather
than removing detail. Shipping the complete formula is accepted for this optimization; a compact explanation-boundary
design is parked in `specs/backlog/attributed-footprint-explanability/` and is not a requirement of the active feature.

## Tests

- Focused ExplainableObject and attribution tests: 59 passed, 2 subtests passed.
- Full suite: 1,507 passed, 9 skipped, 67 subtests passed in 37.22 seconds.
