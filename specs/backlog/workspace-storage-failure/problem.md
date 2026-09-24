# Workspace replacement on storage failure

**Status:** Parked reliability investigation; no implementation scheduled.
**Recorded:** 2026-09-24, during Simplified inputs review (formerly SI-2).

## Risk and evidence

A replacement file can load successfully, but storing its models can still fail after the old
workspace has been cleared. The result may be an empty or partially restored workspace without
a clear failure message. The imported file is unaffected; previous workspace changes without
an exported copy could be lost.

Code inspected:

- [views_workspace.py](../../../model_builder/adapters/views/views_workspace.py), `_restore_workspace()`,
  clears existing slot data before storing replacements.
- [cache_backend.py](../../../model_builder/adapters/repositories/cache_backend.py), `CacheBackend.set()`,
  logs write exceptions or dropped Postgres writes without returning a success/failure outcome.
- [session_system_repository.py](../../../model_builder/adapters/repositories/session_system_repository.py),
  `save_data()`, advances slot metadata without a confirmed write outcome.

No storage failure was injected and no data-loss incident was observed. A failure in only one backend
may leave the other copy usable; the outcome depends on which operations fail.

## Why parked

This is an existing persistence concern, independent of Simplified inputs. That feature only moves
existing import/loading and combined-size checks before clearing the workspace. It does not address
failures while writing the prepared replacements.

## Questions before implementation

- Which backend write outcomes count as success, and how should failures reach the UI?
- How can workspace replacement preserve a usable previous state if replacement writes fail?

No replacement protocol is chosen. Checking the incoming file first does not make storage writes
failure-safe; any fix needs focused failure-injection evidence.
