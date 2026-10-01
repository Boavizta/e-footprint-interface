# Repository-specific workflow guidance — e-footprint-interface

This file is local to this repository; the synchronization script never overwrites it.

- Architecture entry point: `specs/architecture/index.html`; read the index, then only the owning pages. Use the task router and actual page names rather than inventing documentation paths.
- Standards: `specs/constitution.md`, `specs/conventions.md`, `specs/testing.md`. These remain authoritative; the shared skills do not weaken their gates.
- The library owns modeling semantics; `ModelWeb` exposes them. Preserve Clean Architecture, repository ownership, session persistence, and HTMX update behavior. Follow supported create/edit/preview/import/export paths when a boundary changes.
- Validation: `poetry run pytest tests --ignore=tests/e2e`, `poetry run pytest tests/e2e -n 4` with the required local server, and `npm run jest`. See the testing guide for fixtures and environment setup. Apply the constitution's migration, publishable-dependency and changelog gates. Do not use production services for validation.
- FULL review surfaces: domain/application boundaries, repositories and session persistence, migrations and serialization, auth/security, form parsing or validation ownership, HTMX/OOB state transitions, and library/interface contracts. Small display-only templates or styles can qualify for LIGHT; a path alone does not imply a hard implementation task.
- Cross-repository work: one working set in the driving repo, explicit file ownership, one baseline and commit range per affected repo. Test against the intended library checkout. Preserve pre-existing `pyproject.toml`/`poetry.lock` edits; the PyPI dependency must be restored deliberately before merge.
- Documentation promotion: owning architecture pages, conventions, testing and user-journey pages under `specs/design/`. Keep `CHANGELOG.md` and the roadmap accurate. Never automatically retire Django migration or serialization-upgrade tests at archive.

Workflow/tooling instructions and commands: `specs/agent-tooling.md`.
