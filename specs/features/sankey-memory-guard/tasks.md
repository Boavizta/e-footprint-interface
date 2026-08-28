# Reactive computation memory guard — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

## Task 1 — Add library computation-observation primitives

**Goal:** Give interface callers a safe, scoped way to observe every newly completed reactive slot, and expose a
domain-owned, peek-only attribution coverage query. This is the cross-repository library prerequisite; it does not
introduce deployment policy or user-facing behavior.

**Repository:** `e-footprint/`.

**Files touched:**
- `efootprint/abstract_modeling_classes/reactive_core/graph.py`
- `efootprint/abstract_modeling_classes/reactive_core/__init__.py`
- `efootprint/core/attribution/__init__.py`
- `specs/architecture/recomputation/lifecycle.html`
- `specs/architecture/attribution.html`
- `CHANGELOG.md`

**Tests added/changed:**
- `tests/abstract_modeling_classes/test_reactive_core.py`
- `tests/core/attribution/test_attribution.py`

**Acceptance:**
- `observe_computations(callback)` observes each successful cache-miss computation, including nested scalar,
  structure, and computed-dict slots; cached reads emit nothing.
- Observer scopes restore the previous process-local observer on normal exit and exceptions, including nested scopes;
  no observer leaves the existing hot path effectively inert.
- The callback runs after the new value and dependency edges are coherent. If it raises, the engine removes and
  unlinks that new value, restores the slot's prior dependency edges, unwinds the computation stack, and leaves the
  slot retryable without discarding already-successful child caches.
- The callback receives enough non-user-authored slot identity for exceptional-jump diagnostics and is documented as
  forbidden from mutating the model or pulling reactive values.
- The attribution helper returns cached and total `impact_repartition_rows` source-slot counts for the sources required
  by `System.impact_repartition_matrix`, unwraps contextual relationship proxies, and never computes a missing value.
- Focused library tests pass and the observer lifecycle and attribution coverage contracts are documented.

**Depends on:** none.

---

## Task 2 — Ship observation-only request and worker diagnostics

**Goal:** Instrument model-builder requests and Gunicorn workers with bounded, correlated memory evidence while
preserving application behavior. This creates the deliberate production-observation pause point before enforcement.

**Repository:** `e-footprint-interface/` (using the editable Task 1 library while developing).

**Files touched:**
- `e_footprint_interface/runtime_memory.py` (new)
- `e_footprint_interface/computation_memory_middleware.py` (new)
- `e_footprint_interface/settings.py`
- `gunicorn.conf.py`
- `performance/memory/scripts/profile_model.py`
- `performance/memory/README.md`
- `specs/architecture.md`
- `CHANGELOG.md`

**Tests added/changed:**
- `tests/unit_tests/test_runtime_memory.py` (new)
- `tests/unit_tests/test_computation_memory_middleware.py` (new)
- `tests/unit_tests/test_gunicorn_config.py`

**Acceptance:**
- Runtime memory reads cgroup v1/v2 capacity, current usage, inactive file cache, working set, process RSS, and
  `memory.events` safely, with explicit behavior for unavailable or unlimited cgroups.
- Computation and worker-recycling numeric thresholds resolve once per process from cgroup capacity and their separate
  ratio/absolute-override settings; the existing 60% recycling behavior remains intact.
- `COMPUTATION_MEMORY_GUARD_MODE=off|observe|enforce` is parsed and validated, defaults to `off`, and pre-production can
  select `observe`; this task's observer records but does not raise in observation mode.
- Middleware scopes the observer around every `/model_builder/` request before `ModelWeb` construction, does no
  monitoring work for unrelated routes, and always restores the observer.
- Every completed callback is counted. Memory is sampled every 16 slots away from the tentative limit and every slot
  within 256 MiB; progress logs are limited to operation start, each new 128 MiB high-water band, an unusually large
  between-sample jump, completion, or abort.
- Correlated structured records include the approved privacy-safe route, timing, PID, topology, attribution-cache,
  RSS, raw cgroup, inactive-file, working-set, capacity, peak, slot-count, and sampling-overhead fields. They contain no
  model names, values, JSON, or user-authored labels.
- Gunicorn worker lifecycle logs compare cgroup `oom` and `oom_kill` counters so a kernel kill can be distinguished from
  timeout or manual termination even when no request completion log exists.
- Controlled disabled/no-op/observe runs are repeatable, no-observer overhead is within measurement noise, and initial
  observation overhead targets at most 3% of cold-computation time.

**Depends on:** Task 1.

---

## Task 2b — Harden production observation from dev evidence

**Goal:** Correct the diagnostic gaps and remove avoidable sampling cost revealed by the first dev deployment before
enforcement behavior is built. Preserve the bounded-log design and the per-computation enforcement checkpoint while
making observation mode cheap enough to leave enabled during calibration.

**Repository:** `e-footprint-interface/`.

**Evidence from the first dev observation:**

| Scenario | Start / peak working set | Slots / elapsed | Monitor cost | Outcome |
|---|---:|---:|---:|---|
| Three-pattern cold Sankey | 1,376.5 / 2,157.9 MiB | 3,945 / 3,816 ms | 77.9 ms callback; 68.9 ms reads; 0.9 ms logging | Completed; post-GC 2,086.4 MiB; recycled |
| Four-pattern cold Sankey | 805.2 / 2,937.8 MiB | 4,539 / 6,409 ms | 413.0 ms callback; 394.6 ms reads; 2.4 ms logging | Completed with 238 MiB headroom; post-GC 2,867.2 MiB; recycled |
| Five-pattern cold Sankey | 1,271.3 / at least 3,080.3 MiB | Last progress at slot 3,868 / 5,751 ms; killed at 42.1 s | At last progress: 362.2 ms callback; 346.1 ms reads; 2.3 ms logging | 502 and SIGKILL; `oom=1`, `oom_kill=1`, `max=279702`, `sock_throttled=4` |

- The same M deployment exposed cgroup capacities of 2,926 MiB before redeployment and 3,176 MiB afterward. Treat the
  runtime cgroup value as authoritative and preserve this variability in the report; Clever Cloud investigation is
  external to this task.
- At 3,176 MiB, an 80% threshold would be 2,540.8 MiB and would have interrupted the five-pattern run around 4.2 s.
  The approved initial 85% threshold is 2,699.6 MiB and would have interrupted it around 4.5–4.9 s with about 476 MiB
  nominal headroom. Three patterns fit below either threshold; four patterns exceed both. Keep the ratio configurable;
  Task 4 validates 85% under enforcement before production rollout rather than selecting between the two values.
- Ordinary observed requests spent roughly 2–3% in the monitor; warm-cache Sankeys spent under 1 ms. Near-limit runs
  reached roughly 6% because observation continued per-slot sampling long after the candidate abort point. Memory
  reads, not logging, dominate: logging remained around 1–2 ms per request.
- The OOM worker was replaced immediately and finished application imports about five seconds later. Most user-visible
  delay came from approximately 36 seconds of kernel reclaim/thrashing before the kill, not worker boot.

**Current implementation defects to address:**

- `ComputationMemoryMonitor` initializes every Sankey as `attribution_matrix_cached=True` and changes it to `False`
  only after the matrix slot completes. The OOM run therefore claimed a cache hit in every surviving progress record.
- Middleware constructs monitors with `usage_pattern_count=None` and `modeled_hours=None` and never updates them after
  `ModelWeb` hydration, so every production record lacks topology.
- Every sample calls the full snapshot reader: cgroup current, the complete `memory.stat` parse, and process RSS. In the
  near-limit phase this produced 1,000+ filesystem reads and hundreds of milliseconds of avoidable work.
- Observation mode continues sampling every slot after the candidate threshold has already been crossed, even though
  only one `would_abort` point is needed to predict enforcement behavior.
- Gunicorn `child_exit` executes in the master, but the lifecycle record combines the dead worker PID with RSS measured
  from the master process. The cgroup values and OOM deltas are valid; that process-RSS identity is not.
- Bounded 128 MiB high-water logging intentionally means the last progress record before OOM need not be the last
  successful callback. Do not infer that the 36-second log gap was one elementary calculation.

**Files touched:**
- `e_footprint_interface/runtime_memory.py`
- `e_footprint_interface/computation_memory_middleware.py`
- `gunicorn.conf.py`
- `performance/memory/results/2026-08-28-dev-observation.md` (new)
- `performance/memory/README.md`
- `CHANGELOG.md`

**Tests added/changed:**
- `tests/unit_tests/test_runtime_memory.py`
- `tests/unit_tests/test_computation_memory_middleware.py`
- `tests/unit_tests/test_gunicorn_config.py`

**Acceptance:**
- Completed model operations populate usage-pattern count and modeled hours whenever a `ModelWeb` was hydrated; cached
  requests and failures before hydration retain an explicit unavailable value rather than guessed topology.
- A Sankey observation starts with attribution-cache state unknown, changes to cold as soon as an attribution source or
  matrix slot computes, and reports warm only when the request completes without attribution computation. A worker OOM
  can therefore never leave progress records falsely claiming that the matrix was cached.
- Worker-exit records do not label the Gunicorn master's RSS as the dead worker's RSS: they either omit process RSS or
  identify the measuring process separately, while preserving cgroup counters and the exited worker PID.
- The per-sample enforcement path reads only the values required to compare cgroup working set with the threshold.
  Process RSS and the complete diagnostic snapshot are read only for emitted records; one `psutil.Process` instance is
  reused and `inactive_file` is extracted without constructing a dictionary for all of `memory.stat`.
- Observation mode emits one correlated `would_abort` record on first crossing the candidate threshold, then backs off
  to the ordinary 16-slot cadence. Enforcement mode retains per-computation sampling inside the configured 256 MiB
  warning window and will raise immediately in Task 3.
- High-water, exceptional-jump, completion, post-request, worker lifecycle, and OOM-counter records remain bounded and
  preserve their existing privacy constraints.
- The dev evidence is recorded: three-pattern peak, four-pattern borderline completion, five-pattern OOM, capacity
  variation between 2,926 and 3,176 MiB, monitor timings, worker-restart timings, and cgroup OOM/max counters.
- Focused tests cover warm, cold, interrupted and pre-hydration metadata; observe-mode backoff; lightweight versus full
  snapshots; configured-threshold warning behavior; and correct worker-exit identity.
- Repeatable local Docker measurements plus one representative dev run show at most 3% observation overhead before
  Task 3 begins. If the target is missed, the report records the remaining cost and the task stays open.
- Task 2b must not implement the capacity exception, rollback handling, Sankey error template, or enforcement rollout;
  those remain Tasks 3 and 4. The approved initial enforcement ratio is 85%.

**Depends on:** Task 2 and the first dev observation run.

---

## Task 3 — Add recoverable enforcement and Sankey guidance

**Goal:** Turn the observed threshold into a single-trip request circuit breaker that preserves model consistency and
gives Sankey users an actionable graph-space explanation. The capability lands behind configuration and remains off
until Task 4 approves rollout.

**Repository:** `e-footprint-interface/`.

**Files touched:**
- `e_footprint_interface/runtime_memory.py`
- `e_footprint_interface/computation_memory_middleware.py`
- `model_builder/domain/exceptions.py`
- `model_builder/adapters/views/sankey_views.py`
- `model_builder/templates/model_builder/result/sankey_memory_limit.html` (new)
- `performance/memory/scripts/profile_model.py`
- `specs/architecture.md`
- `CHANGELOG.md`

**Tests added/changed:**
- `tests/unit_tests/test_computation_memory_middleware.py`
- `tests/unit_tests/adapters/views/test_sankey_views.py`
- `tests/unit_tests/adapters/views/test_views_edition.py`
- `tests/integration/test_edition.py`
- `tests/e2e/pages/sankey_page.py`
- `tests/e2e/test_sankey.py`

**Acceptance:**
- Enforce mode compares cgroup working set with the configured computation threshold, initially set to 85% of capacity
  with an absolute override and no fixed reserve.
- The first unsafe sampled completion raises `ComputationMemoryLimitExceeded`, then latches the request monitor into
  observation-only behavior so rollback guard computations cannot raise it again.
- The middleware provides the existing generic recoverable-error response only as a fallback for undecorated
  model-builder routes; existing decorated non-Sankey views render the exception's safe generic message unchanged.
- An interrupted transactional edit follows existing `ModelingUpdate` rollback, does not persist the rejected edit,
  and leaves the restored model usable. Interrupted results and exports preserve the already-valid persisted model.
- Once `ModelWeb` hydration has produced a complete system, `sankey_diagram()` catches the capacity exception inside its
  existing generic decorator and replaces only the graph surface with the dedicated template. A capacity exception
  during earlier hydration uses the generic out-of-band modal rather than fabricating attribution coverage.
- The Sankey explanation reports peek-only attribution-source coverage `X%` and cgroup capacity `Y GiB`, labels coverage
  as non-linear, and recommends reducing usage-pattern complexity or timespan, splitting the model, or using a larger
  instance.
- Completion, abort, and post-request evidence remain correlated; post-request full GC and the separate 60% worker
  recycle policy still run after an aborted response.
- Tests cover threshold boundaries, absolute overrides, single-trip behavior, graph integrity, rollback/non-persistence,
  result preservation, generic fallback, specialized Sankey rendering, and the user-visible E2E flow.

**Depends on:** Task 2b.

---

## Task 4 — Calibrate and approve enforcement rollout

**Status:** Done.

**Goal:** Use representative pre-production evidence to validate headroom and overhead, record the operational
decision, and only then enable enforcement in the deployment environment.

**Repository:** `e-footprint-interface/`; deployment configuration is changed separately where it is hosted.

**Files touched:**
- `performance/memory/results/<calibration-date>-memory-guard.csv` (new)
- `performance/memory/results/<calibration-date>-memory-guard.md` (new)
- `performance/memory/README.md`
- `performance/memory/backlog.md`
- `e_footprint_interface/runtime_memory.py` (only if evidence changes calibrated constants)
- `e_footprint_interface/computation_memory_middleware.py` (remove temporary fine-grained overhead counters after
  validation)
- `specs/features/sankey-memory-guard/spec.html` (resolve rollout/reserve questions)
- `CHANGELOG.md`

**Tests added/changed:**
- `tests/unit_tests/test_runtime_memory.py` (only if calibrated constants change)
- `tests/unit_tests/test_computation_memory_middleware.py` (temporary-counter removal and any calibrated behavior)
- Repeatable Docker profiling scenarios documented under `performance/memory/` rather than nondeterministic CI limits.

**Acceptance:**
- Pre-production evidence covers known five-pattern cold Sankey, fresh-worker, result-primed, and allocator-history
  scenarios on the production container architecture.
- The report compares off, no-op, observe, and enforce-near-limit modes; records latency, callback/sample/logging cost,
  largest between-sample growth, peak RSS and cgroup working set, inactive file, worker restart time, and OOM counters.
- Observation overhead is accepted at no more than 3% of cold-computation time, or the sampling policy is revised and
  re-measured before rollout.
- The approved 85% threshold leaves demonstrated headroom for the largest observed elementary/native allocation and for
  rendering the recoverable response on the smallest supported container; Task 4 validates that assumption and revises
  the configurable ratio only if enforcement evidence disproves it.
- Temporary detailed timing counters are removed after representative production evidence, while bounded operational
  start/progress/completion/abort and worker-lifecycle records remain.
- The spec's remaining calibration questions are resolved, the 85% threshold rationale is recorded, and enforcement is
  enabled first in pre-production through `COMPUTATION_MEMORY_GUARD_MODE=enforce`; production activation remains an
  explicit deployment decision after that release is observed.

**Depends on:** Task 3 and representative observation data from Task 2b.

---

## Ordering rationale

Task 1 lands the framework-owned contracts first, independently of Django and container policy. Task 2 is the first
behavioral pause point: it wires the first consumer and yields useful production diagnostics without rejecting any
request. The runtime reader, middleware, adaptive sampler, structured logs, and Gunicorn counters stay together because
splitting them would leave incomplete or uncorrelated evidence. Task 2b is a targeted evidence-driven hardening commit:
the first deployment exposed correctness and overhead problems that should not be carried into enforcement. Task 3
adds the second behavioral milestone—safe interruption and recovery—and keeps the exception, rollback behavior,
middleware fallback, Sankey branch, and template together because there is no safe user-visible pause point among
them. Task 4 is deliberately separate: enforcement must be calibrated from deployed observation rather than approved
from synthetic tests alone.
