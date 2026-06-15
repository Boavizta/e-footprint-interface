# Roadmap — e-footprint-interface

This file tracks active workstreams and the near/mid/far horizon. Detailed plans live under `specs/features/<feature-name>/`.

## Active streams

### Recurrent quantities — weekly-pattern builder (planned)

Path: `specs/features/recurrent-quantities-weekly-pattern-builder/`.

Composite form field for `ExplainableRecurrentQuantities` with day profiles + week assignment. Spec is locked; needs a plan.

## Mid-term horizon

### Candidate refactor — converge creation-time linking paths

Two creation-time linking mechanisms coexist: edge devices/groups link through the
`parent_group_memberships` multi-parent widget (`group_membership_service.py`), while steps/jobs link
through the generic `efootprint_id_of_parent_to_link_to` + `parent_link_count` path
(`ObjectLinkingService`). They coexist because the edge widget supports joining several parents with
per-parent counts at creation, which the single-parent count field doesn't. Candidate: fold edge
creation onto the generic path (extended to multi-parent) so dict-relationship creation has one code path.

## Far horizon (no commitment)

- Persistent per-user model libraries (multi-model save/load per user).
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
