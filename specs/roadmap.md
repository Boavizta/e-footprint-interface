# Roadmap — e-footprint-interface

This file tracks active workstreams and the near/mid/far horizon. Detailed plans live under `specs/features/<feature-name>/`.

## Active streams

### Public modeling sharing — specification reviewed, implementation pending

The [reviewed spec](features/public-model-sharing/spec.html) and
[interactive journey](design/journeys/share-a-model.html) record the September 30 decisions:
public snapshots in the normal workspace, fork in place, versioned publications with in-place metadata
corrections, verified accounts, a fixed 100-version allowance, and deletion/moderation behavior.
[Planning notes](features/public-model-sharing/planning-notes.md) capture reuse constraints and implementation checks.

### Modeling upgrade comparison — draft prerequisite

The [draft kickoff](features/modeling-upgrade-comparison/README.md) is reserved for a separate `spec-specify`
session before sharing implementation. Define consistent old-JSON/shared-snapshot handling, a summary of
all objects with changed footprints, and historical/current footprints together on a graph.
Existing loading already recalculates after library changes but the interface loses the temporary
historical baseline. This extends the library's existing upgrade-time drift visualization roadmap item.

### Workflow improvements — shadow-review observation

Interface-led features participate in the library's [five-feature protocol](../../e-footprint/specs/features/workflow-improvements/tasks.md).
Its [shared observation record](../../e-footprint/specs/features/workflow-improvements/shadow-review.md)
tracks progress across both repositories; there is no separate interface counter.

### Timeseries builders — unify `builders/timeseries` with `time_builders` (planned, parked)

The class-based `builders/timeseries` objects (form-input-driven, editable in the interface) currently cover exponential growth, constant recurrent values, and the shipped recurrent-quantities weekly-pattern builder, while the richer functional helpers in the library's `time_builders` module (linear growth, sinusoidal/daily fluctuation, calendar/frequency, from-list) are not available as editable objects. Unify them: expose the `time_builders` patterns as form-input objects (with a `form_inputs` attribute) so any usage series can be built and edited in the interface. Origin: EcoScan feedback (`user_research/2026-05-19-ecoscan.md`); the library tutorial already covers timeseries discoverability in the meantime.

## Mid-term horizon

### Candidate refactor — converge creation-time linking paths

Two creation-time linking mechanisms coexist: edge devices/groups link through the
`parent_group_memberships` multi-parent widget (`group_membership_service.py`), while steps/jobs link
through the generic `efootprint_id_of_parent_to_link_to` + `parent_link_count` path
(`ObjectLinkingService`). They coexist because the edge widget supports joining several parents with
per-parent counts at creation, which the single-parent count field doesn't. Candidate: fold edge
creation onto the generic path (extended to multi-parent) so dict-relationship creation has one code path.

### Audit drill-down first-read recompute — loading affordance (descoped)

Drill-down reads pull lazily. An exact-version session is fully cached, so drill-down has no delay; only a
legacy inputs-only session pays a one-time first-read recompute (which then self-heals once persisted).
No loading state was added. Revisit only if that legacy first-read delay becomes a real UX complaint —
then a brief HTMX loading affordance on the drill-down/calculus-graph fetch is enough.

## Far horizon (no commitment)

- Private persistent per-user modeling libraries (public publications are tracked above).
- Multi-user collaboration on a shared model (constitution §4 currently rejects this).
- Mobile-first or responsive-first UX overhaul.

## Stable / not in flight

- Clean Architecture domain/application/adapters layout.
- HTMX-driven partial updates and the form-rendering pipeline.
- Sankey diagrams, hourly emissions chart, source table, xlsx export.
- Session-driven state and JSON download/upload round-trip.

## Out of scope until re-litigated

- SPA migration (constitution §4).
- Replacing Django, HTMX, Bootstrap, or Playwright (constitution §4).
- i18n (constitution §4).
