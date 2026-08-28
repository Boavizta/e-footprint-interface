# Memory-guard enforcement calibration — 2026-08-28

## Decision

Task 4 acceptance is satisfied. The 85% working-set threshold, with no fixed reserve, passed the development
enforcement gate and is technically approved for production activation. Activation remains an explicit operator
deployment decision; this calibration neither changes production configuration nor makes activation automatic.

No fixed reserve is added. On the smallest reproduced 2,926 MiB cgroup, 15% is 438.9 MiB. Across all scenarios, the
worst breaker crossing reached 2,502.4 MiB sampled working set and 2,535.7 MiB raw cgroup usage. That left at least
423.6 MiB of working-set headroom and 390.3 MiB below the hard limit after including inactive file. The largest measured
between-sample increase was 134.5 MiB in the same-model result-primed scenario, so the remaining headroom was at least
3.1 times that jump by working set and 2.9 times it by raw cgroup usage.

This is evidence for a circuit-breaker reserve, not a mathematical allocation bound. The observer runs after an
elementary calculation returns and cannot see a native allocation that peaks and frees entirely inside that calculation.

## Environment and method

- Production image/base commit `72395aa9`; profiler script mounted from commit
  `501663cbf47be0d116dfb02cfec4a014fa67f805`; fresh image `efootprint-memory-profile:task4`
- Python 3.12.14, efootprint 23.0.0b3, psutil 7.2.2
- Docker Desktop Linux 6.10.14, arm64
- Scenario C smart-building model expanded to five shared edge usage patterns
- Automatic cyclic GC disabled during each calculation, matching Gunicorn request handling
- Every row is a fresh container; the 4,096 MiB comparison used three interleaved repetitions per mode
- The near-limit comparison used a 2,926 MiB cgroup, the smallest capacity observed in development: seven interleaved
  off/no-op/observe repetitions and three enforcement repetitions for both fresh cold and same-model result-primed
  Sankeys; allocator history has seven completed repetitions per mode and three enforcement repetitions
- `results-primed-sankey` computes results and Sankey on the same hydrated model, retaining shared calculation caches
- `results-then-sankey` computes results, deletes the model, collects, rehydrates, and computes Sankey in one process;
  it covers allocator history without carrying calculation caches into the Sankey

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

### Same-model result-primed Sankey

| Capacity | Mode | Repetitions | Median combined calculation | Difference from off | Median callback / reads / logging |
|---:|---|---:|---:|---:|---:|
| 2,926 MiB | off | 7 | 1.760 s | baseline | — |
| 2,926 MiB | no-op | 7 | 1.749 s | -0.6% | — |
| 2,926 MiB | observe | 7 | 1.760 s | 0.0% | 20.2 / 14.7 / 1.9 ms |
| 2,926 MiB | enforce | 3 | 1.582 s to abort | not comparable to completion | 20.1 / 14.9 / 1.7 ms |

Result priming reduced elapsed time by reusing shared calculated slots but increased retained peak memory: completed
runs reached about 2,780 MiB working set, roughly 147 MiB above a cold Sankey after rehydration. It also exposed the
134.5 MiB largest between-sample jump used for the conservative headroom decision.

### Allocator-history sequence

| Capacity | Mode | Repetitions | Median combined calculation | Difference from off | Median callback / reads / logging |
|---:|---|---:|---:|---:|---:|
| 4,096 MiB | off | 3 | 2.439 s | baseline | — |
| 4,096 MiB | no-op | 3 | 2.402 s | -1.5% | — |
| 4,096 MiB | observe | 3 | 2.432 s | -0.3% | 29.3 / 21.8 / 1.6 ms |
| 2,926 MiB | off | 7 | 2.401 s | baseline | — |
| 2,926 MiB | no-op | 7 | 2.407 s | +0.2% | — |
| 2,926 MiB | observe | 7 | 2.445 s | +1.8% | 40.8 / 32.4 / 1.8 ms |
| 2,926 MiB | enforce | 3 | 2.352 s to abort | not comparable to completion | 46.5 / 36.8 / 1.7 ms |

The results stage reached about 853 MiB working set. After deletion and full collection, the allocator-history state ranged
from about 620 to 732 MiB. The subsequent completed Sankey still converged on the same 2,633–2,634 MiB working-set peak
as the fresh-worker case. History changed the starting state and allocation reuse, not the final peak for this topology.

## Memory and enforcement behavior

| Scenario / mode | Slots / samples | Largest jump | Peak process RSS | Peak raw cgroup | Inactive file | Peak working set | Post-GC working set |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fresh cold, observe, 4,096 MiB | 5,132 / 322 | 24.8 MiB | 2,658.0 MiB | 2,666.9 MiB | 33.3 MiB | 2,633.7 MiB | 2,600.6 MiB |
| History, observe, 4,096 MiB | 10,448 / 655 | 28.0 MiB | 2,658.0 MiB | 2,666.9 MiB | 33.3 MiB | 2,633.6 MiB | 2,590.1 MiB |
| Fresh cold, observe, 2,926 MiB | 5,132 / 787 | 24.8 MiB | 2,657.9 MiB | 2,666.8 MiB | 33.3 MiB | 2,633.5 MiB | 2,600.5 MiB |
| Same-model primed, observe, 2,926 MiB | 6,140 / 429 | 134.2 MiB | 2,804.8 MiB | 2,813.8 MiB | 33.3 MiB | 2,780.5 MiB | 2,757.9 MiB |
| History, observe, 2,926 MiB | 10,448 / 1,123 | 28.0 MiB | 2,658.1 MiB | 2,666.9 MiB | 33.3 MiB | 2,633.7 MiB | 2,599.7 MiB |
| Fresh cold, enforce, 2,926 MiB | 4,463 / 744 | 24.8 MiB | 2,520.5 MiB | 2,528.9 MiB | 33.3 MiB | 2,495.7 MiB | 2,466.5 MiB |
| Same-model primed, enforce, 2,926 MiB | 5,742 / 403 | 134.5 MiB | 2,512.2 MiB | 2,520.7 MiB | 33.2 MiB | 2,487.4 MiB | 2,224.1 MiB |
| History, enforce, 2,926 MiB | 9,779 / 1,080 | 28.0 MiB | 2,520.6 MiB | 2,529.0 MiB | 33.3 MiB | 2,495.8 MiB | 2,461.7 MiB |

All nine enforcement runs raised the typed capacity exception and exited normally; none was kernel-killed. The worst
crossing was 15.3 MiB above the configured threshold because the check follows a completed reactive slot. Fresh and
allocator-history post-GC retention remained above the independent 60% recycling threshold. Same-model primed retention
varied from 834.6 to 2,224.4 MiB, so the production policy would recycle two of those three workers and safely retain
the other after sending the response.

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

## Development enforcement gate

Commit `501663cbf47be0d116dfb02cfec4a014fa67f805` was deployed to development with
`COMPUTATION_MEMORY_GUARD_MODE=enforce` and the default 85% ratio. The runtime reported cgroup capacity to one decimal
place as 3,149.0 MiB, yielding an approximately 2,676.7 MiB threshold at the same precision. Because enforcement checks
after a completed reactive calculation, the two independent four-pattern requests crossed that reported threshold by
about 4.8 MiB and 6.2 MiB before raising once. This historical deployment predates the `limit_mb` record field, so its
exact byte-valued threshold is not recoverable from the rounded log; current records retain the resolved limit directly
for exact audits. Four patterns were sufficient to trigger the guard on this deployment; the five-pattern topology was
already covered by the production-container Docker matrix.

| Request | Worker | Abort working set | Raw cgroup / inactive file | Working-set / raw headroom | HTTP response | Post-GC working set | Response to replacement boot | OOM / OOM-kill delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `47be174d…` | 36 | 2,681.5 MiB | 2,689.1 / 7.6 MiB | 467.5 / 459.9 MiB | 200, 1,017 bytes | 2,641.4 MiB | 0.578 s | 0 / 0 |
| `e697158b…` | 56 | 2,682.9 MiB | 2,703.8 / 20.9 MiB | 466.1 / 445.2 MiB | 200, 1,017 bytes | 2,395.3 MiB | 0.580 s | 0 / 0 |

Each correlated request contains one `abort` record and no second trip during cleanup. In both cases the HTTP 200 was
logged before full collection, the recycling decision, worker exit, and replacement boot. The smallest demonstrated
post-crossing reserve was therefore 466.1 MiB by working set and 445.2 MiB by raw cgroup usage. Even against the larger
134.5 MiB between-sample jump from the local same-model scenario, those reserves are 3.5 and 3.3 times the jump. The
1,017-byte response also demonstrates that the recoverable response could be rendered inside the remaining reserve.

After the first replacement booted, it handled ordinary user requests returning 200 and 204, completed a three-pattern
Sankey with HTTP 200, and was then recycled normally for retained memory. The next worker handled more ordinary 200
traffic before the second four-pattern attempt. The first replacement boot record appeared 0.578 seconds after the
aborted response; health traffic followed 10.6 seconds after boot and the first ordinary user-facing 200 followed after
12.1 seconds. The second replacement booted 0.580 seconds after its response; the supplied excerpt ends at that boot, so
it does not independently show the next request.

Across the excerpt there is no `monitor_error`, HTTP 5xx, gateway error, or positive `oom`/`oom_kill` delta. The user
separately confirmed that the recoverable Sankey guidance rendered; the access log alone establishes the successful
HTTP response, not its visual presentation. Together with the production-container matrix, this passes every rollout
gate. Production activation is approved technically but remains a separate, explicit operator deployment decision.
