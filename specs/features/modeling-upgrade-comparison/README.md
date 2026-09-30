# Modeling upgrade comparison — draft feature kickoff

Status: draft for a separate `spec-specify` session · 2026-09-30.
No spec, implementation plan or UI design has been approved for this feature.

## User outcome

After a library upgrade changes calculated footprints, users need a summary of **every object whose
footprint diverges from the saved historical result**. Clicking an object should display its historical
and recalculated footprints together on the same graph. Opening an old JSON and opening an old shared
publication should behave consistently.

This was identified while reviewing [public modeling sharing](../public-model-sharing/spec.html).
Develop this as a small prerequisite, separately from publication mechanics. Refine it with
`spec-specify` in another session; do not treat this kickoff as a finished specification.

## Existing behavior, verified on 30 September

- The library's [persistence contract](../../../../e-footprint/specs/architecture/persistence.html)
  reuses selected saved calculated values only on an exact `efootprint_version` match. On a mismatch,
  supported major-schema migrations run and the current engine recalculates on read.
- `json_to_system` retains surviving historical values in an in-memory `_version_baseline`;
  `System.has_version_baseline` / `compare_to_version_baseline()` expose a comparison hook. The
  baseline is not serialized. This is partial historical-result comparison, not old-engine replay.
- Some files contain only inputs. The pre-23 migration discards old calculated values. A baseline
  or a particular object/series may therefore be unavailable; the future UI must not fabricate one.
- Interface `SystemImportService.import_system` materializes and reserializes the imported model
  under the running version. It loses that temporary baseline before showing the imported workspace.
  Session upgrades also persist the new version without an upgrade-result UI.
- Current explicit exports include selected calculated results; an older save/load design incorrectly
  said all calculated values were omitted. That documentation is corrected in the sharing review batch.
- Version matching checks the e-footprint version, not a full dependency/data fingerprint.
- Existing library roadmap item: [Upgrade-time drift visualization](../../../../e-footprint/specs/roadmap.md).
  It suggests persisting a compact comparison summary if needed, not historical timeseries by default.
  The requested graph overlay may need a different retention choice; assess this during specification.

Investigation checks: 19 library persistence tests and 7 interface migration/import tests passed.
A simulated 25.0.0 → 25.0.1 version change (unchanged formulas, zero numerical delta) confirmed that
library loading retained a baseline and interface importing lost it. This was not a replay of two
historical numerical engines. The interface checks used an isolated v25.0.0 source snapshot because
its environment was stale then; the user has since updated the worktree environment to efootprint 25.0.0.

## Questions for the future specification

- Which footprint measures and graph granularity should be shown per object? How are units,
  time alignment and meaningful numerical tolerances handled?
- How do we identify and present added, removed or transformed objects across schema migrations?
- How do we distinguish unavailable historical totals/series from actual zero differences?
- What historical data or derived summary must survive requests, cache recovery, export/import
  and a later upgrade, within the existing workspace size budget?
- Where does the summary appear, and how can it be reopened without occupying a comparison slot?
- How do methodology changes and any upstream-data changes relate to the version signal?
- What exact evidence verifies equal behavior for files and shared snapshots?

## Boundaries

Use library-owned numerical comparison and existing result graph conventions where useful. Keep
stored source documents intact. Full execution of an old library environment is not requested.
Do not limit the intended summary to the overall headline total: the user's request is all objects
with footprint divergences and a clickable two-footprint graph. Historical-availability limitations
must remain explicit until this feature is specified.

This is interface-driven cross-repository work. Keep its eventual spec/plan/tasks in this folder,
including any library tasks in the single driving task list.
