# Mission — e-footprint-interface

## What e-footprint-interface is

A Django web application providing a graphical interface to the [e-footprint](https://github.com/Boavizta/e-footprint) Python library. It lets users build, edit, and visualize digital-service environmental-impact models without writing Python.

The interface wraps the e-footprint library through a Clean Architecture: the domain layer mirrors e-footprint's modeling concepts (servers, jobs, usage patterns, edge devices) as web-aware entities, the use-case layer orchestrates create/edit/delete flows, and the adapter layer talks Django + HTMX + Bootstrap.

## Audience

- **Primary: non-technical product person.** Must be usable with zero Python, zero modeling background. Tone, vocabulary, and defaults are tuned for this user first.
- **Secondary: technical users** (engineers, architects). They should sense that depth and customization exist beneath the surface, and drop into it without friction.
- **Industrial users** modeling edge fleets and mixed web/edge systems.

Guiding principle: *no one left behind, depth available on demand.* Every profile in a product team should be able to use the tool.

## Eco-design and feature choices

The project itself is eco-designed and complexity-aware. Prioritize capabilities people actually use
and keep functionality and implementation lean, simple, maintainable and frugal. Before adding a
convenience, weigh its expected frequency and user benefit against the complexity it introduces.
Prefer existing controls or explicit user actions when the extra effort is negligible and avoids
additional coordination. State unverified usage assumptions; rare but consequential correctness needs
still deserve protection.

Code simplicity supports maintenance but does not establish environmental savings. Consider runtime
work, computation, storage and transfers separately when relevant, and ground resource-impact claims
in evidence.

## In scope (today)

- **Visual model building**: forms and cards for every e-footprint object type (web and edge).
- **Real-time recalculation** with explainable results: every value carries its derivation.
- **Impact visualization**: Sankey diagrams, hourly emissions charts, source tables, xlsx export.
- **Disabled-instead-of-error UX**: action buttons disable preemptively when prerequisites are missing, with a tooltip explaining what to do next.
- **Session-driven state**: the session holds a workspace of up to two models (one active for editing) plus the active-slot pointer; downloads and uploads round-trip the full system state including UI configuration.
- **Dict-based relationships** for hierarchical edge fleets (`EdgeDeviceGroup` with sub-groups and device counts).
- **Onboarding and contextual help**: first-run example picker with starter examples, a guided tour, the help-drawer overlay, and a web/edge mode toggle. See [Examples and onboarding](architecture/onboarding.html).

## Out of scope (today, by deliberate choice)

- Multi-user collaborative editing of the same model.
- Persistent per-user model libraries (Django auth exists for admin; the modeling state itself is session-only).
- i18n; English only.
- Mobile-first UX (desktop-first; mobile is best-effort).
- SPA migration (HTMX is the chosen interactivity model).

## Main components

- `model_builder/` — the main Django app, structured by Clean Architecture:
  - `domain/` — entities, services, interfaces. Pure Python, no Django.
  - `application/use_cases/` — `CreateObjectUseCase`, `EditObjectUseCase`, `DeleteObjectUseCase`, and supporting orchestration.
  - `adapters/` — views, repositories, presenters, forms, ui_config (Django + HTMX).
  - `templates/` — Django templates with Bootstrap + HTMX.
- `theme/` — frontend assets (SCSS, Bootstrap compilation, vanilla JS utilities, charts bundle).
- `e_footprint_interface/` — Django project configuration (settings, URLs, WSGI).
- **Dependency**: [`efootprint`](https://pypi.org/project/efootprint/) as the modeling engine.

## Distribution & ecosystem

- **Production**: https://e-footprint.boavizta.org
- **Pre-production**: https://dev.e-footprint.boavizta.org
- **Hosting**: Clever Cloud (PostgreSQL + Docker).
- **Repo**: https://github.com/Boavizta/e-footprint-interface
- **License**: Apache-2.0.
- **Maintenance**: Vincent Villet (Publicis Sapient), hosted by Boavizta.
