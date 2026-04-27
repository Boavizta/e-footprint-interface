# Constitution — e-footprint-interface

These are the project's immutable rules. They must be respected by every code change, by every author (human or agent), and they are amended only deliberately, not by drift. If a proposed change requires breaking a rule here, raise it explicitly and update the constitution before the change ships.

---

## 1. Engineering principles

1. **Clean Architecture: dependency direction is sacred.** Inner layers (`domain/`, `application/`) never import outer layers (`adapters/`, Django, HTMX, templates). Zero Django imports in `domain/` and `application/`. Tests under `tests/integration/` enforce this by running adapters → use cases → domain without any Django scaffolding.
2. **Repository pattern.** The domain depends on `ISystemRepository`, never on a concrete implementation. `SessionSystemRepository` and `InMemorySystemRepository` are interchangeable adapters.
3. **The library is the domain truth.** `efootprint` (the package) owns modeling logic. `ModelWeb` wraps and exposes; it never re-implements modeling. When a question is "what does this calculation mean?", the answer lives in the library, not here.
4. **HTMX-first; minimize JS.** Prefer partial HTTP updates over client-side state. Vanilla JS where unavoidable; no SPA framework, no client-side routing, no client-side data layer.

## 2. Quality gates (a change is not ready until)

1. Important changes have been tested. Reserve Playwright E2E tests for critical flows and high-risk changes; cover other logic with unit and integration tests.
2. Full pytest suite passes: `tests/unit_tests`, `tests/integration`, `tests/e2e`.
3. Jest passes (`npm run jest`).
4. `pyproject.toml` and `poetry.lock` reference `efootprint` from PyPI (not a local editable path) before any commit reaches `main`. Enforced by a pyproject.toml-parsing test.
5. If Django models change, a migration file is committed.
6. `CHANGELOG.md` entry added.

## 3. Agent-facing rules

1. **Never paper over a bug.** If you discover unrelated bad behaviour while working on a task — a stale card after mutation, a missing form attribute, a brittle assertion — fix it on the spot or surface it explicitly. Never hide it with a `page.reload()`, a defensive branch, or a renamed test.
2. **Never skip hooks (`--no-verify`)** unless explicitly authorized.
3. **Ask before destructive operations** (force pushes, branch deletions, hard resets).

Other coding-style, layering, and testing rules live in `architecture.md`, `conventions.md`, and `testing.md`.

## 4. Out of scope (rejected by default)

- Internationalization (English only).
- Replacing Django, HTMX, Bootstrap, or Playwright.
- Backward-compatibility shims (no other consumers).
- SPA migration (React, Vue, Svelte, etc.).
- Multi-user collaborative editing of the same model.
- Mobile-first or responsive-first UX (desktop-first; mobile is best-effort).

## 5. Amending the constitution

A change to this file requires:

1. A short justification ("why now") proposed alongside.
2. An explicit acknowledgment of which downstream artifacts (`architecture.md`, `conventions.md`, CI tests) need to follow.

Use the `update-constitution` skill, or just edit deliberately with a separate commit — never blend constitutional changes into a feature commit.
