# Global review — Run A

Repository and reviewed feature range: `e-footprint-interface` `56f8278addf36c9551cff873466aed89ea2decc3..1b2a9d026553019a6b4b6f51e58de4c65e535d48`. Library unchanged at `14852b3a0beeee3bcf7ac428d2406c5e26e856e1`.

## Review pointers

- `edit_simplified_input()` returns the generic 500 modal when initial hydration/catalog construction fails. A request arriving after both repository payloads expire has no accepted field to render; attempting the field-recovery helper repeated `SessionExpiredError` and lost the modal. The adapter regression evicts actual stored cache payloads and submits the stale field address. Accepted-field recovery remains on the edit path after the initial model/catalog are usable.

## Deferred network interruption UX

- Request-with-no-response messaging is parked in the [network-interruption-message backlog](../../../backlog/network-interruption-message/problem.md). Run A covers HTTP 422/500 responses and adds no dedicated network message or reconciliation.

## Coverage limits

- Literal full non-E2E Python and Jest validation used a temporary archive of committed `1b2a9d02`, existing installed dependencies, and temporary generated bundle/staticfiles outputs. The clean tracked Python collection excludes the 14 private smoke cases supplied by a non-versioned workspace module and private JSON files; their earlier diagnostic coverage remains applicable. The installed editable library points to the intended unchanged library HEAD; this does not constitute a fresh PyPI installation.
- The working checkout still has the unrelated editable dependency and untracked VS Code extension suite that prevent its literal Python/Jest commands from passing. Preserve those edits; restore the publishable dependency deliberately before merge.
- The existing full E2E coverage was reused for unchanged browser behavior; the global correction is covered at the real Django adapter/cache boundary. Retain the three intermittent timing failures recorded in `task-3.md` even though they did not reproduce in its final full run.
