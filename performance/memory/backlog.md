# Memory optimization backlog

Priorities are evidence-driven and should be revised as more topologies are profiled.

| Priority | Candidate | Expected effect | Evidence / validation needed | Complexity |
|---|---|---|---|---|
| P0 | Progressive calculation memory breaker | Abort a cold Sankey before the container OOM-kills its only worker | Validate maximum growth between reactive-slot callbacks and choose cgroup headroom | Medium, cross-repository |
| P0 | Persist the scalar attribution matrix in recovery storage | Avoid rebuilding the hourly graph after a Redis miss | Matrix is tiny relative to the calculated hourly graph; measure cache/read cost | Medium |
| P1 | Topology-aware preflight warning | Warn before a model becomes unlikely to produce a Sankey | Calibrate coordinate-hours by calculation family across adversarial topologies | Medium |
| P1 | Recycle only after high retained cgroup working set | Recover allocator-retained memory without reacting to reclaimable page cache | A local SQLite copy-up demonstrated that raw cgroup usage may be dominated by unrelated file cache | Low; guard already exists |
| P2 | Evict hourly values after attribution rows are reduced | Reduce warm-worker retained memory while keeping dependency invalidation | Requires a safe reactive-core eviction primitive and recomputation analysis | High |
| P2 | Reduce explanation-array retention during matrix construction | Reduce cold peak, currently dominated by hourly NumPy buffers | Native allocation profile and semantic review of explainability requirements | High |
| P3 | Reduce static application/import baseline | Leave more of the 4 GiB budget to calculations | Warm full-stack PSS is only ~238 MiB, so current leverage is low | Unknown |

Worker recycling addresses retained/fragmented memory after a request. It cannot protect against the fresh working-set
peak of one calculation; the progressive breaker remains necessary even if recycling is effective.
