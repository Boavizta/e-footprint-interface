# Roadmap — e-footprint-interface

This file tracks active workstreams and the near/mid/far horizon. Detailed plans live under `specs/features/<feature-name>/`.

## Active streams

### Tutorial-and-documentation overhaul (in flight, multi-step)

Path: `specs/features/tutorial-and-documentation/`.

The major workstream covering: disabled-instead-of-error UX, single-source-of-truth descriptive content shared with the library, contextual help, web-vs-edge UX, onboarding starter templates and guided tour, e-footprint docs overhaul.

Status:

- Step 1 (disabled-instead-of-error UX) — **shipped**.
- Step 2 (SSOT metadata in the library) — planned next; library-side work coordinated via `../../e-footprint/specs/roadmap.md`.
- Steps 3–7 — see `specs/features/tutorial-and-documentation/99-implementation-plan.md`.

### Recurrent quantities — weekly-pattern builder (planned)

Path: `specs/features/recurrent-quantities-weekly-pattern-builder/`.

Composite form field for `ExplainableRecurrentQuantities` with day profiles + week assignment. Spec is locked; needs a plan.

## Mid-term horizon

### Edge modeling toggle and UX

Part of the tutorial-and-documentation Step 5. Adds the navbar edge-mode toggle and edge badges on cards. Pre-requisite for the IoT industrial onboarding template.

### Onboarding flow (templates + tour)

Tutorial-and-documentation Step 6. Template picker, three starter templates (e-commerce, AI chatbot, IoT industrial), guided first-run tour.

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
