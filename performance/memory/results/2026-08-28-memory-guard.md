# Memory-guard enforcement calibration — 2026-08-28

## Decision

The 85% working-set threshold is approved for an enforcement trial in development. It is **not** approved for
production yet. Development must run the five-pattern cold Sankey with enforcement enabled and confirm the recoverable
response, post-request collection, worker recycle, replacement-worker readiness, and zero OOM-counter delta. Production
activation remains an explicit decision after that release has been observed.

No fixed reserve is added. On the smallest reproduced 2,926 MiB cgroup, 15% is 438.9 MiB. The breaker crossed its
2,487.1 MiB threshold at 2,495.6–2,495.9 MiB sampled working set. That left 430.1–430.4 MiB of working-set headroom and
396.8–397.2 MiB below the hard limit after including inactive file. The largest measured between-sample increase was
28.2 MiB, so the remaining headroom was at least 15.2 times that jump by working set and 14.1 times it by raw cgroup
usage.

This is evidence for a circuit-breaker reserve, not a mathematical allocation bound. The observer runs after an
elementary calculation returns and cannot see a native allocation that peaks and frees entirely inside that calculation.

## Environment and method

- Interface base commit `72395aa9`; production `Dockerfile`; fresh image `efootprint-memory-profile:task4`
- Python 3.12.14, efootprint 23.0.0b3, psutil 7.2.2
- Docker Desktop Linux 6.10.14, arm64
- Scenario C smart-building model expanded to five shared edge usage patterns
- Automatic cyclic GC disabled during each calculation, matching Gunicorn request handling
- Every row is a fresh container; the 4,096 MiB comparison used three interleaved repetitions per mode
- The near-limit comparison used a 2,926 MiB cgroup, the smallest capacity observed in development: seven interleaved
  off/no-op/observe repetitions and three enforcement repetitions
- `results-then-sankey` computes results, deletes the model, collects, rehydrates, and computes Sankey in one process;
  it covers result priming and allocator history without carrying a calculated matrix into the Sankey

Raw compact rows are in [`2026-08-28-memory-guard.csv`](2026-08-28-memory-guard.csv). The profiler's 5 ms sampler can
miss brief native peaks; the reactive callback's largest jump is the enforcement-relevant checkpoint measurement.

## Timing and overhead

### Fresh five-pattern cold Sankey

| Capacity | Mode | Repetitions | Median calculation | Difference from off | Median callback / reads / logging |
|---:|---|---:|---:|---:|---:|
| 4,096 MiB | off | 3 | 1.651 s | baseline | — |
| 4,096 MiB | no-op | 3 | 1.692 s | +2.5% | — |
| 4,096 MiB | observe | 3 | 1.684 s | +2.0% | 17.1 / 12.1 / 1.7 ms |
| 2,926 MiB | off | 7 | 1.621 s | baseline | — |
| 2,926 MiB | no-op | 7 | 1.642 s | +1.3% | — |
| 2,926 MiB | observe | 7 | 1.649 s | +1.7% | 28.5 / 23.2 / 1.8 ms |
| 2,926 MiB | enforce | 3 | 1.534 s to abort | not comparable to completion | 28.7 / 23.7 / 1.6 ms |

Both completed observation comparisons pass the 3% gate. The no-op observer remains within run-to-run noise. The
near-limit observer sampled 787 times rather than 322 because it used per-slot checkpoints inside the 256 MiB warning
window until emitting one `would_abort` record, then returned to ordinary cadence.

### Result-primed and allocator-history sequence

| Capacity | Mode | Repetitions | Median combined calculation | Difference from off | Median callback / reads / logging |
|---:|---|---:|---:|---:|---:|
| 4,096 MiB | off | 3 | 2.439 s | baseline | — |
| 4,096 MiB | no-op | 3 | 2.402 s | -1.5% | — |
| 4,096 MiB | observe | 3 | 2.432 s | -0.3% | 29.3 / 21.8 / 1.6 ms |
| 2,926 MiB | off | 7 | 2.401 s | baseline | — |
| 2,926 MiB | observe | 7 | 2.445 s | +1.8% | 40.8 / 32.4 / 1.8 ms |
| 2,926 MiB | enforce | 3 | 2.352 s to abort | not comparable to completion | 46.5 / 36.8 / 1.7 ms |

Result priming reached about 853 MiB working set. After deletion and full collection, the allocator-history state ranged
from about 620 to 732 MiB. The subsequent completed Sankey still converged on the same 2,633–2,634 MiB working-set peak
as the fresh-worker case. History changed the starting state and allocation reuse, not the final peak for this topology.

## Memory and enforcement behavior

| Scenario / mode | Slots / samples | Largest jump | Peak process RSS | Peak raw cgroup | Inactive file | Peak working set | Post-GC working set |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fresh cold, observe, 4,096 MiB | 5,132 / 322 | 24.8 MiB | 2,658.0 MiB | 2,666.9 MiB | 33.3 MiB | 2,633.7 MiB | 2,600.6 MiB |
| History, observe, 4,096 MiB | 10,448 / 655 | 28.0 MiB | 2,658.0 MiB | 2,666.9 MiB | 33.3 MiB | 2,633.6 MiB | 2,590.1 MiB |
| Fresh cold, observe, 2,926 MiB | 5,132 / 787 | 24.8 MiB | 2,657.9 MiB | 2,666.8 MiB | 33.3 MiB | 2,633.5 MiB | 2,600.5 MiB |
| History, observe, 2,926 MiB | 10,448 / 1,123 | 28.0 MiB | 2,658.1 MiB | 2,666.9 MiB | 33.3 MiB | 2,633.7 MiB | 2,599.7 MiB |
| Fresh cold, enforce, 2,926 MiB | 4,463 / 744 | 24.8 MiB | 2,520.5 MiB | 2,528.9 MiB | 33.3 MiB | 2,495.7 MiB | 2,466.5 MiB |
| History, enforce, 2,926 MiB | 9,779 / 1,080 | 28.0 MiB | 2,520.6 MiB | 2,529.0 MiB | 33.3 MiB | 2,495.8 MiB | 2,461.7 MiB |

All six enforcement runs raised the typed capacity exception and exited normally; none was kernel-killed. The breaker
overshot the configured threshold by less than 9 MiB because the crossing is checked after a completed reactive slot.
Post-GC retention remained above the independent 60% recycling threshold, so the production worker policy should
replace these workers after sending the response.

Direct profiler containers do not run Gunicorn, render the HTTP response, or expose meaningful worker-restart and
per-worker cgroup-event deltas. Those fields therefore remain unavailable locally rather than being fabricated.

## Pre-production evidence carried forward

The observation deployment report remains part of this decision:

- A 2,975 MiB dev cgroup completed a four-pattern cold Sankey at 2,925.7 MiB working set. Observation cost was
  137.103 ms over 6,404.1 ms (2.14%), with 120.072 ms in memory reads and 3.028 ms in logging.
- Its first threshold crossing occurred at 2,529.2 MiB and sampling backed off as designed.
- The response completed before the high-retention worker exited; the replacement worker booted immediately and
  application imports completed in about five seconds. Its OOM and OOM-kill deltas were zero.
- The earlier five-pattern observation-only request was killed after prolonged reclaim pressure, with `oom=1`,
  `oom_kill=1`, `max=279702`, and `sock_throttled=4`. This is the failure mode enforcement is intended to replace.

The deployed observation evidence is sufficient to retire fine-grained timing fields from operational request records.
The local `PROFILE` method retains internal timing accumulation for controlled calibration only. Bounded start,
progress, `would_abort`, completion, abort, post-request, and worker-lifecycle records remain.

## External development gate

After review, deploy this commit to development with `COMPUTATION_MEMORY_GUARD_MODE=enforce`; do not change the 85%
ratio or add an absolute override. Run the known five-pattern cold Sankey and preserve the correlated request and worker
records. Approval for production requires all of the following:

1. The request returns the dedicated recoverable Sankey guidance rather than a 5xx or gateway error.
2. Exactly one abort record is emitted near 85%; no second trip occurs during recovery.
3. The response is logged before post-request collection and any worker exit.
4. The exited worker has zero OOM and OOM-kill deltas, and the replacement worker becomes ready within the observed
   operational window.
5. An ordinary request succeeds on the replacement worker.

If any condition fails, restore development to `observe` and revise the ratio or recovery path before reconsidering
production. Even after a pass, production activation remains a separate deployment decision after one observed release.
