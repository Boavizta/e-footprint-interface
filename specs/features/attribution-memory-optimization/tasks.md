# Attribution memory optimization — Tasks

**Status:** Tasks — implementation approach approved.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).
**Required implementation context:** [`implementation-notes.md`](implementation-notes.md).

## Task 1 — Bound cold Sankey retention by attribution source

**Goal:** Reduce each source to cached period-sum rows and release its attribution-only hourly structures before
processing the next source, without changing calculations or reactive invalidation.

**Files touched:**

- `e-footprint/efootprint/abstract_modeling_classes/reactive_core/{computed_slots.py,__init__.py}`
- `e-footprint/efootprint/core/attribution/__init__.py`
- `e-footprint/efootprint/core/system.py`
- `e-footprint/efootprint/core/hardware/{edge/edge_device.py,server_base.py,storage.py}`
- `e-footprint/tests/abstract_modeling_classes/test_reactive_core.py`
- `e-footprint/tests/integration_tests/test_recompute_counter.py`
- Relevant attribution/Sankey tests and library documentation or changelog

**Tests and evidence:**

- A transient structure can be evicted while its cached descendant remains coherent; a later input edit still
  invalidates the descendant through the preserved dependency edge.
- Reject a computed structure declared both `serialize=True` and `transient=True`.
- Complete library suite passes (experiment baseline: 1,506 passed, 9 skipped, 67 subtests passed).
- Four patterns: median peak RSS falls from 2,239.1 to 656.0 MiB and median latency from 1.242 to 1.161 seconds,
  with the same 4,538 reactive callbacks.
- Five patterns: median peak RSS falls from 2,739.5 to 778.8 MiB and median latency from 1.546 to 1.452 seconds.

**Acceptance:** Sankey matrix/payload values are unchanged; fresh-process peak RSS is at least 60% lower on both
fixtures; no material latency regression; invalidation and serialization semantics remain correct.

**Depends on:** none.

---

## Task 2 — Implement bounded direct attributed-footprint retention

**Goal:** Keep `attributed_footprint(obj, phase)` and its hourly numerical result unchanged while finalizing its previously
missing formula and releasing each source's transient attribution arrays before processing the next source.

**Files touched:**

- `e-footprint/efootprint/core/attribution/__init__.py`
- Attribution tests under `e-footprint/tests/core/attribution/` and integration tests
- Profiling evidence under `e-footprint-interface/performance/memory/results/`
- Library documentation/changelog if the experiment meets its semantic and memory gates

**Tests and evidence:**

- Capture baseline peak RSS for manufacturing, usage, and sequential both-phase reads from fresh processes.
- Implement a source-wise fold: aggregate the requested object, make formula finalization composable, clear arithmetic
  parents, then evict the source's transient values.
- Compare hourly magnitude arrays, dates, units, labels, period sums and formulas exactly enough to rule out a public
  explainability regression.
- Measure repeated calls to quantify the latency exchanged for bounded retention.

**Acceptance:** Hourly arrays remain byte-identical; the complete derivation replaces the pre-existing empty
`explain()` output; one-target and repeated-target peaks remain materially bounded; the full library suite passes. The
large formula is accepted for this feature. Designing compact, deep-divable ephemeral explanation boundaries remains
out of scope in `specs/backlog/attributed-footprint-explanability/`.

**Experiment result:** Exact float32 values were preserved. Median one-target peaks fell from 1,322.5 to 496.8 MiB for
manufacturing, 2,074.5 to 614.9 MiB for usage, and 2,819.6 to 752.3 MiB for sequential phases. Five retained usage
targets fell from 2,344 to 657 MiB, with latency rising from 1.66 to 2.33 seconds. Composable finalization exposes the
complete, very large formula; that behavior is approved for this feature.

**Depends on:** Task 1, whose transient-eviction primitive it reuses.

---

## Task 3 — Adopt and validate the optimized library in the interface

**Goal:** Release/adopt the completed library optimization and verify it under the interface's Docker and memory-guard
environment before deployment.

**Files touched:**

- `e-footprint-interface/pyproject.toml` and `poetry.lock`
- `e-footprint-interface/performance/memory/results/`
- Both repositories' changelogs and any architecture/contributor note required by the shipped pattern

**Tests and evidence:**

- Build the deployment-shaped Docker image without a local editable dependency.
- Repeat cold system-result, Sankey, and attributed-footprint scenarios with cgroup working-set and process RSS data.
- Run affected interface smoke tests and the applicable repository quality gates.

**Acceptance:** The interface consumes a released/PyPI dependency; Docker results confirm the expected memory reduction;
the memory guard remains a fallback rather than the normal outcome for the five-pattern reference model.

**Depends on:** Tasks 1 and 2 (or Task 2's documented no-ship decision).

---

## Ordering rationale

The already-measured Sankey optimization establishes the reusable eviction primitive first. Direct attributed footprint
then tests the harder formula-retention boundary without expanding its API. Interface adoption comes last so it can pin
one coherent library release and validate the combined behavior in the actual deployment shape.
