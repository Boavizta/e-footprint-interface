# Development observation and monitor hardening — 2026-08-28

## Scope

The first observation-only deployment exercised three-, four-, and five-pattern cold Sankeys on the development
production architecture. It established real request, cgroup, OOM, and worker-restart behavior; it did not validate an
enforcement response. The monitor was then hardened locally to correct cache/topology diagnostics and reduce sampling
cost, then validated again on the development production architecture before enforcement work.

The hosting platform exposed two different finite cgroup capacities for the same M deployment: 2,926 MiB before a
redeployment and 3,176 MiB afterward; the post-fix deployment reported 2,975 MiB. Every interpretation below uses the
capacity reported by that process's cgroup; the cause of the platform variability is external to this investigation.

## First dev deployment

| Scenario | Start / peak working set | Slots / elapsed | Monitor cost | Outcome |
|---|---:|---:|---:|---|
| Three-pattern cold Sankey | 1,376.5 / 2,157.9 MiB | 3,945 / 3.816 s | 77.9 ms callback; 68.9 ms reads; 0.9 ms logging | Completed; post-GC 2,086.4 MiB; worker recycled |
| Four-pattern cold Sankey | 805.2 / 2,937.8 MiB | 4,539 / 6.409 s | 413.0 ms callback; 394.6 ms reads; 2.4 ms logging | Completed with about 238 MiB headroom; post-GC 2,867.2 MiB; worker recycled |
| Five-pattern cold Sankey | 1,271.3 / at least 3,080.3 MiB | Last bounded progress: slot 3,868 at 5.751 s; killed at 42.1 s | At last progress: 362.2 ms callback; 346.1 ms reads; 2.3 ms logging | HTTP 502 and worker SIGKILL |

Ordinary observed requests spent roughly 2–3% of their elapsed time in the monitor, while warm-cache Sankeys spent
less than 1 ms there. The near-limit requests reached roughly 6% because observation mode continued per-slot sampling
after crossing the candidate abort point. Memory reads dominated the cost; bounded logging remained about 1–2 ms per
request.

The five-pattern worker-exit evidence recorded `oom=1`, `oom_kill=1`, `max=279702`, and `sock_throttled=4`. The OOM and
OOM-kill counters confirm a cgroup memory kill rather than a Gunicorn timeout or manual termination. `max` is a
cumulative cgroup limit-hit counter, not a byte quantity or a peak-memory measurement. The replacement worker appeared
immediately and completed application imports about five seconds later. Most of the user-visible delay was the roughly
36 seconds between the last emitted progress record and the kill, not worker boot.

That gap does **not** show that one elementary reactive calculation ran for 36 seconds. Progress logs are deliberately
bounded to new 128 MiB high-water bands or exceptional jumps, so successful callbacks can continue without producing a
record. The surviving log only establishes the last emitted high-water milestone; it does not identify the final
callback before kernel reclaim and thrashing ended in OOM.

## Candidate threshold interpretation

On the 3,176 MiB container, 80% is 2,540.8 MiB and would have predicted an interruption of the five-pattern request at
about 4.2 seconds. The approved initial 85% candidate is 2,699.6 MiB and would have predicted interruption at about
4.5–4.9 seconds, leaving roughly 476 MiB of nominal cgroup headroom. Three patterns stayed below both candidates; four
patterns exceeded both and completed only because this deployment was observation-only.

These observations select 85% as the configurable candidate; they do not prove it safe for enforcement. Validation
must still cover the largest elementary/native allocation and enough response-rendering headroom on the smallest
supported capacity. The independent post-request worker recycling threshold remains 60%.

## Hardening driven by the evidence

- Sankey cache state now begins unknown, becomes cold when an attribution source or matrix slot computes, and becomes
  warm only on successful completion without attribution computation.
- Successful hydration supplies usage-pattern count and modeled hours; operations that fail before hydration preserve
  explicit unavailable values.
- The per-sample checkpoint reads only cgroup current and inactive file. Full diagnostic snapshots and process RSS are
  taken only when a record is emitted, and the process handle is reused.
- Observation emits one `would_abort` record at the candidate crossing and then returns to 16-slot sampling. The
  reserved enforcement mode retains per-slot checkpoints inside the 256 MiB warning window.
- Worker-exit records omit process RSS because Gunicorn runs the exit hook in the master; the exited worker PID and
  cgroup event deltas remain valid.

## Post-fix local Docker gate

Seven interleaved fresh 4 GiB containers per mode used the same five-pattern cold-Sankey fixture and production GC
behavior:

| Mode | Median cold-calculation time | Difference from off |
|---|---:|---:|
| Off | 0.175 s | baseline |
| No-op observer | 0.178 s | +1.71% |
| Hardened observation | 0.176 s | +0.57% |

The observation result passes the 3% local gate. The no-op/observation ordering is within run-to-run noise at these
durations.

## Representative post-fix dev gate

Commit `d4d612f4` was deployed in observation mode on a 2,975 MiB cgroup. The previously failing edge reference import
completed with HTTP 302, and the following builder request returned HTTP 200 with populated pattern-count and
modeled-hours fields. This confirms that topology diagnostics no longer turn a valid `EdgeUsagePattern` import into an
application failure.

A cold four-pattern, 26,280-hour Sankey completed 4,539 slots in 6,404.1 ms. Its observer callbacks consumed 137.103 ms
(about 2.14% of elapsed time), including 120.072 ms of memory reads and 3.028 ms of bounded logging, so the deployed
monitor passes the 3% observation gate. The sampled working-set peak was 2,925.7 MiB.

The single `would_abort` record appeared at 2,529.2 MiB, matching the configured 85% candidate of about 2,528.75 MiB.
Its sample count was 623; completion reached 690 samples, exactly the expected ordinary-cadence backoff rather than
continued per-slot sampling. The cold completion reported `attribution_matrix_cached=false`. A subsequent warm Sankey
completed with zero slots and `attribution_matrix_cached=true`.

Post-request collection ran and the worker recycled above the independent 60% threshold. The worker-exit record kept
the exited PID and cgroup counters, omitted process RSS, and reported zero OOM/OOM-kill deltas. The cold request
completed only about 49 MiB below the natural cgroup limit, so four patterns leave little unguarded headroom. That
borderline completion strengthens the case for recoverable enforcement at the candidate threshold; it does not itself
validate the future enforcement response.
