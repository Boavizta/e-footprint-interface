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

## Implementation verification — 2026-08-31

The accepted implementation was remeasured against a fresh `git archive` of clean library commit `d76b858d`. Each cell
used three new interface-Poetry Python processes, the same external fixture expanded through
`performance.memory.scripts.profile_model.add_usage_patterns`, `ModelWeb` hydration, automatic GC disabled during the
calculation, and a 5 ms `psutil` RSS sampler. The target was explicitly unwrapped with
`system.edge_usage_patterns[0]._value`; every returned period sum was asserted non-zero. The five-target case retained
all five unwrapped pattern results.

| Scenario | Baseline RSS runs | Implemented RSS runs | Reduction by median | Baseline latency runs | Implemented latency runs |
|---|---:|---:|---:|---:|---:|
| Manufacturing | 1,333.3 / 1,333.7 / 1,333.7 MiB | 504.7 / 502.2 / 510.9 MiB | 62.2% | 0.874 / 0.881 / 0.884 s | 0.852 / 0.826 / 0.838 s |
| Usage | 2,087.1 / 2,089.1 / 2,088.0 MiB | 604.3 / 620.2 / 631.3 MiB | 70.3% | 0.987 / 1.001 / 0.994 s | 0.922 / 0.920 / 0.938 s |
| Manufacturing then usage | 2,835.9 / 2,836.2 / 2,836.4 MiB | 745.3 / 758.7 / 743.4 MiB | 73.7% | 1.361 / 1.358 / 1.392 s | 1.313 / 1.299 / 1.301 s |
| Five retained usage targets | 2,350.7 / 2,350.1 / 2,351.1 MiB | 632.0 / 645.3 / 649.2 MiB | 72.6% | 1.599 / 1.612 / 1.609 s | 2.253 / 2.241 / 2.254 s |

All implemented and baseline processes produced the same 43,800-element float32 arrays, UTC start date, kilogram unit,
phase label and period sums. The manufacturing bytes had SHA-256
`e56f63dc92657bfd0e77c712045aa5d7a09667d852bee6e95dce4c810c14f532` and sum `23,763.796875 kg`; usage had
SHA-256 `7b555316d772ee895a9f6af24968273db788824ae62d863b7da6b878bba9e80e` and sum `14,705.853515625 kg`.
The implemented explanation lengths were 255,769 characters for manufacturing and 337,627 for usage.

## Tests

- Focused ExplainableObject, attribution, and recomputation tests: 65 passed, 9 subtests passed.
- Full library suite: 1,520 passed, 2 skipped in 42.10 seconds.
- Library documentation: `mkdocs build --strict` passed.
