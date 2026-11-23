# Roadmap — e-footprint-interface

This file tracks active workstreams and the near/mid/far horizon. Detailed plans live under `specs/features/<feature-name>/`.

## Active streams

### Comprehension harness — Python stack written, one flow narrated

The spec-driven workflow moved to plans written into the code as pieces and delivered in lots
([`workflow.md`](workflow.md)). The tools, the stage skills and the roles are installed
([`comprehension_harness/README.md`](../comprehension_harness/README.md)), and so is the Python stack
they read (`.agents/repository.md` § "The stack"; its contract is
[`comprehension_harness/stack.md`](../comprehension_harness/stack.md)): the three calls, the pytest plugin that records
what a test crossed, the source index on Python's `ast`, the title reader, the watch loop, the
journey helper. One flow is narrated, the AI-assisted bootstrap, and its page renders
(`npm run comprehension:render`). The same flow has the first journey drawn from a run of its
browser test, *Start a modeling with AI* (`npm run journey:render`).
Next: the first feature planned in pieces, and the other flows narrated and given a journey as
they are touched. The hand-drawn journeys of `specs/design/journeys/` stay until a drawn one
replaces each. A feature in flight on `plan.html` and `tasks.md` is finished by hand.

An experiment ports the bug batch `bug-fixes-2026-10`, runs B and C, to pieces one bug at a time, to
find what the harness needs for bugs:
[`features/comprehension-harness-bug-fixes/experiment.md`](features/comprehension-harness-bug-fixes/experiment.md).
Tasks 9 and 10 are ported on the bug forms they asked for (reproductions, evidence, template sites),
approved and fixed as one small run of `feature-implement` (2026-11-23). What that run showed is in the
experiment, and changed the skills and the harness: a bug batch is now diagnosed and planned in pieces.
Task 7 is ported into the same plan (2026-11-23); next Tasks 16, 12 and 2, then the four are approved and
fixed together.

### AI-assisted bootstrap — specification approved, planning pending

[First production feature](features/ai-assisted-bootstrap/spec.html): guided web-modeling bootstrap
with one model, synchronous inference, manual refinement and a small toolbar cleanup. The spec was
approved on 2026-11-06; the draft plan awaits a fresh spec-plan session and review. The production
feature replaces the experimental UI and AI editing path; PoC close-out follows delivery.
[AI assistance roadmap](features/ai-assistance/roadmap.md) orders the next steps: edge bootstrap,
then asynchronous AI provider I/O, then Boavizta-owned API credentials and provider-contract clarification. General AI editing and the broader architecture refactoring are
outside this first feature.

### AI bootstrap for edge systems — implemented, awaiting the answers on its delivery and the archive

[`features/ai-bootstrap-edge/spec.md`](features/ai-bootstrap-edge/spec.md): a Web only / Web + edge
scope choice in the description panel, with instructions, guidance and review checklist per scope,
and optional edge device groups. First step of the [AI assistance roadmap](features/ai-assistance/roadmap.md)'s
follow-ups. Spec and plan approved on 2026-11-17; delivery in four lots (one in e-footprint) approved on 2026-11-17;
the four lots built and reviewed on 2026-11-18. Open: the decisions to answer on the delivery page and
the gates of [`features/ai-bootstrap-edge/gates.md`](features/ai-bootstrap-edge/gates.md); the interface's
deployment waits for the `efootprint` release that scales server calls with every device. Then `feature-archive`.

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

### Timeseries builders — unify `builders/timeseries` with `time_builders` (planned, parked)

The class-based `builders/timeseries` objects (form-input-driven, editable in the interface) currently cover exponential growth, constant recurrent values, and the shipped recurrent-quantities weekly-pattern builder, while the richer functional helpers in the library's `time_builders` module (linear growth, sinusoidal/daily fluctuation, calendar/frequency, from-list) are not available as editable objects. Unify them: expose the `time_builders` patterns as form-input objects (with a `form_inputs` attribute) so any usage series can be built and edited in the interface. Origin: EcoScan feedback (`user_research/2026-05-19-ecoscan.md`); the library tutorial already covers timeseries discoverability in the meantime.

## Mid-term horizon

### Clean Architecture refactoring — draft kickoff

[Discussion context and proposed roadmap](features/clean-architecture-refactoring/README.md)
preserve the distinction between editor-specific lifecycle policies and presentation. Prioritize
explicit relationship/deletion semantics and mutation results independent of canvas refreshes;
move remaining web wrappers incrementally. No broader implementation is approved. The separately
authorized `bug-fixes-2026-10` Task 6 canvas-placement cleanup is recorded there to avoid duplication.

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

- The library's [Astra/Sol shadow-review experiment](../../e-footprint/specs/features/workflow-improvements/shadow-review.md) ended early by user decision; Codex task and global reviews use GPT-6.1 Sol/high.

- Clean Architecture domain/application/adapters layout.
- HTMX-driven partial updates and the form-rendering pipeline.
- Sankey diagrams, hourly emissions chart, source table, xlsx export.
- Session-driven state and JSON download/upload round-trip.

## Out of scope until re-litigated

- SPA migration (constitution §4).
- Replacing Django, HTMX, Bootstrap, or Playwright (constitution §4).
- i18n (constitution §4).
