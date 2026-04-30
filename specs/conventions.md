# Conventions — e-footprint-interface

These are the strong preferences and patterns the project follows. They are softer than the constitution: deviations are possible with justification, but defaulting to these preserves consistency.

## Code style

### Python

- **PEP 8** + line length **120**. Don't systematically break lines between parameters; prefer long lines under the limit.
- Follow `.pylintrc` for linting.
- **Type hints** where helpful; not strictly enforced.
- **Prefer double quotes (`"`) for strings**, over single quotes (`'`).
- **Keep functions small.** Raise explicit errors with actionable messages.
- **Comments only when the WHY is non-obvious.** Never comment what the code does — only why it does it that way.

### Django

- **Views are thin adapters.** They map request to use case input, call the use case, format response via the presenter. No business logic in views.
- **Templates are small composable partials.** See `model_builder/templates/model_builder/...` for the pattern.
- **Session is authoritative for the current modeling system.** Every request reconstructs `ModelWeb` from the repository.
- **No domain-layer imports of Django, HTMX, or other presentation concerns** (constitution §1.1).

### JavaScript

- **Vanilla JS + small helpers only.** Keep logic minimal; prefer progressive enhancement.
- **Use HTMX attributes for partial updates** rather than large custom JS.
- **New JS modules wrap their internals in an IIFE and dispatch via `data-action`**. Templates declare intent (`data-action="open-source-editor"`); a single delegated listener in the module switches on the action and dispatches to a module-private function. Rationale: keeps `window` clean (no per-widget globals to collide or accidentally expose), survives HTMX swaps with no rebinding (the listener is on `document`), and is compatible with strict CSP later (no inline JS to allow). When two modules need to talk, prefer a custom DOM event over a shared global. See `theme/static/scripts/source_metadata.js` for the reference pattern. Older modules using inline `onclick=` keep working; migrate boy-scout style when you're already touching one.
- **UI-only inputs inside form sections must omit the `name` attribute.** `dynamic_forms.js#displayOnlyActiveForm` only flips `required`/`disabled` on `input[name]`/`select[name]`. Nameless controls (e.g. the source editor's custom-source scratch fields) never submit, so marking them required would only block the form — hidden invalid controls can't be focused, which silently aborts HTMX submission.

### Tests

- Python tests under `tests/` (and app-specific subfolders).
- Playwright E2E tests under `tests/e2e/`.

## Performance preferences

For data and array operations:

- **Prefer vectorized NumPy operations over Python loops.**
- **Use single-pass algorithms** (e.g., `np.bincount`) over multiple iterations.
- **When proposing solutions, include complexity analysis** (e.g., O(n) vs O(n²)) for non-trivial data paths.
- **Trade-offs between readability and performance** should be made explicit in PR descriptions when relevant.

## Editing patterns

- **Make all edits on the same file at once** rather than step-by-step changes.
- **Never paper over a bug** (constitution §3.1). If you discover an unrelated bug while working on a task — a stale card after mutation, a missing form attribute, a brittle assertion — fix it on the spot or surface it explicitly. Never `page.reload()` to hide it, no defensive branch to tolerate it, no renamed assertion to avoid triggering it.

## Documentation upkeep

- If you notice that the AGENTS.md or specs/ files are missing important information that would allow for less context gathering in developments, propose improvements.
- Whenever you implement or change a non-trivial pattern (new web wrapper convention, new HTMX flow, new render strategy, schema migration), proactively check whether `architecture.md`, `conventions.md`, or `testing.md` should be updated and propose the changes.

## Form field metadata suffixes

Five reserved suffixes are recognised by `form_data_parser.parse_form_data` **before** the generic `__` → `form_inputs` branch:

- `__confidence` — `"low"` / `"medium"` / `"high"` or empty (→ `None`)
- `__comment` — free-form text or empty (→ `None`)
- `__source_id` — id of an existing `Source`; empty means custom entry
- `__source_name` — source name (used when id is absent or unknown to mint a new `Source`)
- `__source_link` — source URL (optional, paired with `__source_name`)

These map into `parsed[attr]["confidence"]`, `parsed[attr]["comment"]`, and `parsed[attr]["source"]["id/name/link"]`. Checking them before the generic branch prevents them from landing in `form_inputs`.

## Test conventions

See `testing.md` for the full testing guide. Highlights:

- Use `create_mod_obj_mock` from `tests.utils` instead of raw `MagicMock` when mocking `ModelingObject` subclasses; prefer real `ExplainableObject` / `ExplainableQuantity` instances when possible.
- Build E2E fixtures with efootprint classes and `from_defaults()`, not JSON files.
- Use `click_and_wait_for_htmx()` for HTMX-triggered E2E clicks; don't write raw Playwright clicks for HTMX flows.
- Form data parsing happens in `adapters/forms/`, never in domain. The domain receives parsed dicts.

## Flakiness

If a test fails on the first run but passes on retry, **flag it explicitly** to the developer as a flaky test rather than silently re-running. Flaky tests are bugs.
