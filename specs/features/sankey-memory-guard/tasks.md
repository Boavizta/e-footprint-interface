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
- Enforce mode compares cgroup working set with the configured computation threshold, initially hypothesized at 80% of
  capacity with an absolute override and no fixed reserve.
- The first unsafe sampled completion raises `ComputationMemoryLimitExceeded`, then latches the request monitor into
  observation-only behavior so rollback guard computations cannot raise it again.
- The middleware provides the existing generic recoverable-error response only as a fallback for undecorated
  model-builder routes; existing decorated non-Sankey views render the exception's safe generic message unchanged.
- An interrupted transactional edit follows existing `ModelingUpdate` rollback, does not persist the rejected edit,
  and leaves the restored model usable. Interrupted results and exports preserve the already-valid persisted model.
- `sankey_diagram()` catches the capacity exception inside its existing generic decorator and replaces only the graph
  surface with the dedicated template.
- The Sankey explanation reports peek-only attribution-source coverage `X%` and cgroup capacity `Y GiB`, labels coverage
  as non-linear, and recommends reducing usage-pattern complexity or timespan, splitting the model, or using a larger
  instance.
- Completion, abort, and post-request evidence remain correlated; post-request full GC and the separate 60% worker
  recycle policy still run after an aborted response.
- Tests cover threshold boundaries, absolute overrides, single-trip behavior, graph integrity, rollback/non-persistence,
  result preservation, generic fallback, specialized Sankey rendering, and the user-visible E2E flow.

**Depends on:** Task 2.

---

## Task 4 — Calibrate and approve enforcement rollout

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
- The selected threshold leaves demonstrated headroom for the largest observed elementary/native allocation and for
  rendering the recoverable response on the smallest supported container; any deviation from the 80% hypothesis is
  documented with evidence.
- Temporary detailed timing counters are removed after representative production evidence, while bounded operational
  start/progress/completion/abort and worker-lifecycle records remain.
- The spec's two open calibration questions are resolved, the final threshold rationale is recorded, and enforcement
  is enabled first in pre-production through `COMPUTATION_MEMORY_GUARD_MODE=enforce`; production activation remains an
  explicit deployment decision after that release is observed.

**Depends on:** Task 3 and representative observation data from Task 2.

---

## Ordering rationale

Task 1 lands the framework-owned contracts first, independently of Django and container policy. Task 2 is the first
behavioral pause point: it wires the first consumer and yields useful production diagnostics without rejecting any
request. The runtime reader, middleware, adaptive sampler, structured logs, and Gunicorn counters stay together because
splitting them would leave incomplete or uncorrelated evidence. Task 3 adds the second behavioral milestone—safe
interruption and recovery—and keeps the exception, rollback behavior, middleware fallback, Sankey branch, and template
together because there is no safe user-visible pause point among them. Task 4 is deliberately separate: enforcement
must be calibrated from deployed observation rather than approved from synthetic tests alone.
