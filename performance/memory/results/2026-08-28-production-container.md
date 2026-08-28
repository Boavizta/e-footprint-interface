# Production-container memory baseline — 2026-08-28

## Environment and scope

- Current production `Dockerfile`, freshly built from the measured checkout
- Python 3.12.14, efootprint 23.0.0b2, Django 5.2.17, psutil 7.2.2
- Docker Desktop Linux 6.10.14, arm64, hard cgroup limit 4,096 MiB
- Smart-building shared-pattern scenario described in
  [`../scenarios/smart-building-2026-05-07.md`](../scenarios/smart-building-2026-05-07.md)
- Process and cgroup sampling every 5 ms; PSS/USS snapshots at stage boundaries

Dynamic scenarios execute the production-installed code directly in a fresh `poetry run python` process. They use the
real `ModelWeb`, result calculation, `ImpactRepartitionSankey`, and interface Sankey payload builder, but exclude HTTP,
Gunicorn, nginx, cache writes, and response rendering. Static measurements use the complete production entrypoint.

These measurements are a topology calibration, not a universal upper bound. The production host is likely x86_64 and
may have a different allocator/kernel from Docker Desktop arm64.

## Static memory

| State | Main observations |
|---|---|
| Bare profiler Python | 18 MiB RSS |
| Application imports | 182 MiB PSS/USS |
| Imports + heavy-model hydration | 185 MiB PSS/USS |
| Full stack before first request | ~68 MiB summed PSS; worker 20, Gunicorn master 24, supervisor 19, nginx ~5 |
| Full stack after one model-builder request | ~238 MiB summed PSS; worker 180, master 35, supervisor 19, nginx ~5 |

The full container reported about 1.28 GiB raw `memory.current` before its first request and 1.42 GiB afterward, but
about 1.18 GiB was reclaimable
`inactive_file`, largely produced by entrypoint/static-file activity. Its working set was about 238 MiB and matched the
sum of process PSS. Raw cgroup usage must therefore be logged, but must not be treated as equivalent to live anonymous
memory when deciding to recycle a worker.

Static optimization is low leverage for the observed OOM: hydration adds only about 3 MiB above application imports,
and the warmed full stack uses roughly 6% of the 4 GiB budget before calculations.

## Dynamic calculations

The detailed repetitions are in [`2026-08-28-production-container.csv`](2026-08-28-production-container.csv).

| Scenario | Patterns | Worker peak | Cgroup working-set peak | Worker after delete + full GC |
|---|---:|---:|---:|---:|
| Hydrate | 2 | 186 MiB | 158 MiB | 186 MiB |
| Results | 2 | 531 MiB | 503 MiB | 456 MiB |
| Cold Sankey, median of 3 | 2 | 1,225 MiB | 1,198 MiB | 1,165 MiB |
| Cold Sankey | 3 | 1,707 MiB | 1,682 MiB | 1,668 MiB |
| Cold Sankey | 4 | 2,191 MiB | 2,166 MiB | 2,149 MiB |
| Cold Sankey, median of 3 | 5 | 2,674 MiB | 2,650 MiB | 2,630 MiB |
| Results request, GC, rehydrate, then cold Sankey | 5 | 2,674 MiB | 2,650 MiB | 2,641 MiB |

For this topology, every additional shared usage pattern adds almost exactly 483 MiB to the cold-Sankey worker peak.
The relationship is linear across all four measured points, but it must not be generalized to other calculation
families without additional topology cases.

The two-pattern results stage peaks at 531 MiB. In the five-pattern request-history scenario it peaks at 897 MiB, drops
to 775 MiB after deletion and GC, and the subsequent cold Sankey still peaks at 2,674 MiB. On this Linux allocator,
previously retained pages are substantially reused rather than simply added to the fresh Sankey peak.

The second Sankey build on the same model takes 38 ms and adds about 0.1 MiB RSS. This confirms that a warm scalar
attribution matrix is cheap; the cold upstream hourly calculation graph is the memory event.

## Conclusions for the next implementation

1. A progressive calculation breaker is justified. A five-pattern cold Sankey already consumes about 65% of the
   container in the direct process before HTTP-stack overhead and safety margin.
2. Full GC is not a memory-cap mechanism. It returns only about 34–101 MiB after cold Sankey; 1.1–2.6 GiB remains mapped
   until worker exit despite the model being deleted.
3. Worker recycling handles post-request allocator retention, not the in-request peak. A pre-OOM breaker is still P0.
4. The breaker and recycling logs should include process RSS, raw cgroup current, inactive file, and cgroup working set.
5. Persisting the small attribution matrix across Redis misses should avoid the expensive cold path entirely and is the
   next strongest candidate after containment.
6. Before setting a topology preflight formula, profile independent journeys, mixed web/edge models, cumulative storage,
   jobs/server needs, and timezone/alignment cases. The observed 483 MiB/pattern coefficient is specific to this model.
