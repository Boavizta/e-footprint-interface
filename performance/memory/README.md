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

The repository-level `.dockerignore` excludes local databases, environments, dependency directories, caches, secrets,
and profiler artifacts. Keep it aligned with new local-only outputs: Git-ignored does not automatically mean
Docker-ignored.

Run each calculation in a fresh 4 GiB container. Mount the model read-only; do not copy large models into this folder:

```bash
MODEL=/absolute/path/to/system.json
SCRIPT=/absolute/path/to/e-footprint-interface/performance/memory/scripts/profile_model.py

docker run --rm --memory=4g --entrypoint poetry \
  -v "$MODEL:/fixture.json:ro" -v "$SCRIPT:/tmp/profile_model.py:ro" \
  -v "$(cd ../e-footprint && pwd):/opt/e-footprint:ro" -e PYTHONPATH=/opt/e-footprint \
  efootprint-memory-profile:local run python /tmp/profile_model.py /fixture.json \
  --patterns 2 --scenario cold-sankey --monitor-mode observe --disable-gc-during-calculation
```

Mounting the sibling checkout exercises the observation API being co-developed in `e-footprint`; the production
dependency declaration remains pinned to PyPI. Use an absolute sibling path if the command is launched elsewhere.

## Observation rollout gate

Before setting `COMPUTATION_MEMORY_GUARD_MODE=observe` in development or pre-production, run a controlled A/B/C profile
against the same model, image, memory limit, pattern count, scenario, and GC setting:

```bash
for RUN in 1 2 3 4 5 6 7; do
  for MODE in off noop observe; do
    docker run --rm --memory=4g --entrypoint poetry \
      -v "$MODEL:/fixture.json:ro" -v "$SCRIPT:/tmp/profile_model.py:ro" \
      -v "$(cd ../e-footprint && pwd):/opt/e-footprint:ro" -e PYTHONPATH=/opt/e-footprint \
      efootprint-memory-profile:local run python /tmp/profile_model.py /fixture.json \
      --patterns 5 --scenario cold-sankey --monitor-mode "$MODE" --disable-gc-during-calculation
  done
done
```

Compare the median `calculation_elapsed_seconds` values from the `RESULT` records. The no-op run isolates the library
callback cost; it should remain within measurement noise of `off`. Observation may be deployed only when its median
cold-calculation overhead is at most 3%. Also retain `observer_callback_count`, `observer_sample_count`,
`observer_callback_wall_ms`, `observer_max_callback_ms`, `largest_sample_jump_mb`, peak working set, inactive file,
and cgroup peak for later threshold calibration. A failed gate means revise the sampling policy and rerun it; it is
not a reason to enable enforcement. Enforcement remains unavailable until representative development observation has
been reviewed.

The first 2026-08-28 local gate used seven interleaved fresh 4 GiB containers per mode with the introductory
industrial-IoT fixture expanded to five shared edge usage patterns. It passed at +1.7% observation overhead. After the
first dev deployment exposed avoidable near-limit sampling cost, the hardened monitor was measured with the same
seven-run method: median cold-calculation time was 0.175 s off, 0.178 s no-op, and 0.176 s observe. Observation overhead
was +0.57%; the small no-op/observe inversion is measurement noise. The complete dev evidence and both the original
and hardened local gates are recorded in
[`results/2026-08-28-dev-observation.md`](results/2026-08-28-dev-observation.md).

For a hardened observation deployment, verify one representative cold run before starting enforcement work:

1. Confirm completion records populate `usage_pattern_count` and `modeled_hours`; failures before hydration must leave
   both fields explicitly unavailable.
2. Confirm Sankey cache state begins unknown, becomes cold after an attribution source or matrix computation, and is
   marked warm only by a successful completion with no attribution computation.
3. If working set crosses the candidate limit, confirm exactly one `would_abort` record is emitted and sampling then
   returns to the ordinary 16-slot cadence. The approved candidate is 85% of runtime cgroup capacity unless
   `COMPUTATION_MEMORY_LIMIT_RATIO` or `COMPUTATION_MEMORY_LIMIT_MB` overrides it.
4. Confirm worker-exit records retain the exited worker PID and cgroup event deltas but omit process RSS, which would
   otherwise describe the Gunicorn master executing the hook.
5. Compare the deployed monitor timing with the matching `off` run. Observation must remain at or below 3% before
   enforcement implementation begins.

The post-fix representative dev gate passed on commit `d4d612f4`: a cold four-pattern, 26,280-hour Sankey completed in
6,404.1 ms with 137.103 ms of callback time (about 2.14%), correct cold/warm cache state, a single threshold crossing,
ordinary-cadence backoff, and valid worker-exit evidence. Its 2,925.7 MiB peak on a 2,975 MiB cgroup also demonstrates
how little natural headroom remains without enforcement. See the linked report for the full evidence. Do not infer one
long elementary computation from a gap between bounded high-water records: callbacks may continue without emitting
another record.

The runtime setting accepts `off`, `observe`, and the reserved `enforce` value. It defaults to `off`; the current
monitor is observation-only and never interrupts a request, including if `enforce` is selected prematurely.

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
