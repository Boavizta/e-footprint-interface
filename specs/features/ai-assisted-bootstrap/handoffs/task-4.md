# Task 4 — PoC retirement and delivery

Repository: `e-footprint-interface`. Implementation commit: `c3a10f79`; review range begins at `18d2659eca43eb8beb1baf81a30cd301c524b138`. Companion library `afc60887fa05c34d18d5969a45276bb08d3dace0` is unchanged.

## Review pointers

- The obsolete edit/read-back helper, edit prompt, floating template and edit-only integration tests are deleted. Shared generation/manual-edit round-trip coverage remains in `tests/integration/test_ai_bootstrap.py`; ordinary sequential job deletion coverage remains in `tests/e2e/objects/test_jobs.py`.
- Delivery documentation covers ownership (`specs/architecture/layers-and-wrappers.html`), both entries and tour handling (`onboarding.html`), active-slot replacement and view controls (`workspace.html`), and full-builder HTMX settle state (`rendering.html`). `AGENTS.md` routes future work to these pages; `CLAUDE.md` remains its symlink.
- `ai_sandbox/README.md` records original PoC revision `1b2ea43740f76b1edcf7f345ed922582d2142bc4` and final relevant pre-removal revision `18d2659eca43eb8beb1baf81a30cd301c524b138`, with Git history as the recovery mechanism.

## Delivery evidence

Required Python, Jest, browser, JS/Sass, dependency-source, runtime-only import/provider-stub, offline CLI dry-run/replay and obsolete-reference checks completed. Browser tests and runtime dependency installation required the approved sandbox escalation for local socket binding and package download. Inference was stubbed; no paid provider call was made. No unresolved checks remain.

Material implementation detail: AI input and summary panels mark `data-ai-bootstrap-panel`; the entire builder response renders panel visibility plus canvas/Results width classes because HTMX settle reapplies response classes after `openSidePanel()`.
