# Memory performance laboratory

This folder makes interface memory investigations reproducible. It complements the historical
[`MEMORY_LEAK_INVESTIGATION.md`](../../archives/investigations/MEMORY_LEAK_INVESTIGATION.md): the archive explains why
freed objects do not necessarily reduce RSS, while this laboratory measures the current application and model topology.

## Questions answered

- What is the static memory cost of Python, application imports, Gunicorn, and the production container?
- What are the peak and retained memories for hydration, results, cold Sankey, and warm Sankey calculations?
- How do duration, usage-pattern count, and model topology change the peak?
- How much headroom must a progressive memory breaker reserve below the container limit?

RSS is useful for the per-worker circuit breaker. PSS avoids double-counting pages shared by Gunicorn's preloaded master
and worker. USS shows memory private to one process. Cgroup usage and peak are the authoritative container-wide figures.

## Reproduce the reference profile

Build the production Dockerfile from a clean checkout:

```bash
docker build -t efootprint-memory-profile:local .
```

Docker currently has no repository-level `.dockerignore`, so a build from a working directory also copies
untracked files. Check that large local artifacts such as `db.sqlite3` are absent from the image before using
entrypoint/cgroup measurements as a production baseline. Git-ignored does not mean Docker-ignored.

Run each calculation in a fresh 4 GiB container. Mount the model read-only; do not copy large models into this folder:

```bash
MODEL=/absolute/path/to/system.json
SCRIPT=/absolute/path/to/e-footprint-interface/performance/memory/scripts/profile_model.py

docker run --rm --memory=4g --entrypoint poetry \
  -v "$MODEL:/fixture.json:ro" -v "$SCRIPT:/tmp/profile_model.py:ro" \
  efootprint-memory-profile:local run python /tmp/profile_model.py /fixture.json \
  --patterns 2 --scenario cold-sankey --disable-gc-during-calculation
```

The GC flag matches production Gunicorn request handling. Omitting it is useful only as an explicit comparison with
ordinary Python automatic collection.

The final `RESULT` line is compact JSON suitable for committing under `results/`. Raw Memray captures, heap dumps, and
other large artifacts belong under `artifacts/`, which Git ignores.

Run at least three fresh-container repetitions before treating small differences as meaningful. The committed reference
is a topology calibration, not a general memory guarantee.

## Scenarios

| Scenario | Meaning |
|---|---|
| `hydrate` | Import application code and construct `ModelWeb`; no result calculation |
| `results` | Hydrate, then compute `system_emissions` |
| `cold-sankey` | Hydrate, then construct attribution data and Sankey from an empty calculation cache |
| `warm-sankey` | Construct the same Sankey twice in one hydrated model; the second build reuses the matrix |
| `results-then-sankey` | Compute results, delete the model, collect, rehydrate, then compute Sankey in the same worker |

Synthetic usage patterns duplicate the first pattern and attach it to the same system. This intentionally stresses the
shared-topology combinatorics seen in production while keeping the source fixture unchanged.

## Reading results

For each stage, compare:

- `stage_peaks.process_rss_mb`: worker peak sampled every 5 ms;
- `stage_peaks.cgroup_current_mb`: raw whole-container usage during that stage;
- `stage_peaks.cgroup_inactive_file_mb`: reclaimable inactive file cache;
- `stage_peaks.cgroup_working_set_mb`: `memory.current - inactive_file`, the actionable live working set;
- milestone `pss_mb` and `uss_mb`: Linux `/proc/<pid>/smaps_rollup` snapshots;
- `post_gc`: memory retained by the allocator after the model is deleted and cyclic GC completes.

Raw cgroup usage can be dominated by reclaimable page cache, especially after `collectstatic`. It remains useful OOM
context, but a worker-recycling decision should not treat it as equivalent to anonymous calculation memory.

The 5 ms sampler can miss shorter native allocation spikes. A production memory breaker therefore needs a safety margin,
and selected cases should eventually be cross-checked with Memray native tracking.

## Reference dataset

[`scenarios/smart-building-2026-05-07.md`](scenarios/smart-building-2026-05-07.md) documents the external model used for the
first baseline. [`results/2026-08-28-production-container.md`](results/2026-08-28-production-container.md) records the
environment, commands, measurements, and interpretation. Optimization candidates live in [`backlog.md`](backlog.md).
