# Constitution §1.4 — server failures stay visible

Parked by the request-lifecycle simplification (shipped in V1.14.0, decision 10 of its plan).

## Problem

`specs/conventions.md` (JavaScript section) now states that feature JavaScript does not anticipate server errors,
slow responses or request races: the server is the source of truth and its failures stay visible rather than
softened. That rule follows from constitution §1.4 (HTMX-first; minimize JS), but it is only a convention, so it can
be relaxed in ordinary feature work.

## Follow-up

Add one sentence to constitution §1.4 making "server failures are visible, not softened" immutable. Make the change
with the `update-constitution` skill, in its own commit, once more features have tested the convention wording.

## Related

- [`htmx-aware-server-error-handler`](../htmx-aware-server-error-handler/problem.md): an uncaught exception on an HTMX
  request is currently invisible in the browser. Visibility has to come from the server.
