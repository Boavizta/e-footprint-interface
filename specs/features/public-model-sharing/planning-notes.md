# Public modeling sharing — planning notes

Status: accepted constraints and investigation pointers for a future `spec-plan` pass · 2026-09-30.
This is not an implementation plan or authorization to implement the feature.

## Reuse the workspace boundary

Read the [workspace architecture](../../architecture/workspace.html) and
[persistence architecture](../../architecture/persistence.html) before exploring code.

- `model_builder/adapters/views/views.py::upload_json` routes a single JSON to the active slot and a
  workspace envelope to `_restore_workspace` in `views_workspace.py`. Shared publications follow
  those same destination rules. A two-modeling publication is one version, constrained by the
  existing whole-workspace size limit. JSON export controls are unchanged.
- `WorkspaceIndex` already tracks per-slot sizes against the shared budget. Retain this mechanism
  for public viewing; do not introduce an account byte budget in addition to 100 retained versions.
- `_restore_workspace` currently clears existing slots before all replacements are loaded; its
  over-budget test accepts a partial restore. The new requirement is all-or-nothing replacement
  for both JSON and shared loading, with validation before destructive writes. Cover failures on
  either incoming model and cancellation, not only successful imports.
- Read-only state is per slot and must be enforced on server mutation paths. Do not disable
  interface-only writes or the ordinary export and comparison controls. Loading a publication
  uses visitor-owned session cache entries, never the canonical stored publication as writable cache.
- Fork changes the loaded publication slots to editable copies and records provenance. Owner edit
  retains a publication/base-version association instead. Neither consumes another slot. Plan the
  identity checks for mixed slots, whole-workspace replacement and stale browser tabs: a shared URL
  must not render whichever unrelated modeling was most recently loaded into the session.
- Explicitly loading another version replaces its affected slots and presentation defaults; normal
  refresh retains cached viewing settings. There is no per-publication override store or preference
  migration. No data-loss prompt for a switch touching only read-only slots; prompt if editable
  content would also be replaced. Reuse existing confirmation/export surfaces where practical.

## Publication semantics to keep simple

- Title, public author, tags and article link are the only current-version in-place corrections.
  Other published changes create a version; historical metadata stays fixed except manual requests.
- Count retained versions atomically, including hidden ones. The fixed cap is 100/account; reveal
  the quota at 80, prevent further version creation at 100, and free the count on whole-publication
  deletion. Metadata corrections do not count. No rate limiter, byte quota, per-account override,
  pruning or individual-version deletion is included.
- A stale-base update warns and offers cancel or explicit publication as the next version. Recheck
  concurrency at the write boundary. Do not add merge/diff machinery; ordinary comparison suffices.
- Publish readiness reuses the same validation as Show results for every included modeling.
- Source citation fields are title, public author, exact version, URL and license; preserve them
  across JSON exports/imports. A source disappearing does not change the captured citation.

## Account and contact integration

Boavizta Brevo and a dedicated credential are available. Keep secrets out of repository artifacts.
Choose the account implementation during planning; the existing project has Django auth but no
public account workflow. Standard account tooling can cover verification, recovery and email change;
[django-allauth's single-email change mode](https://docs.allauth.org/en/latest/account/configuration.html#email-addresses)
is one investigated option, not a mandated dependency.

Email change confirms the password, verifies the new mailbox before replacement, and notifies the
old address without needing its approval. Keep one verified sign-in address and preserve ownership.

**Use one shared contact setting**, valued `vincent.villet@publicissapient.com`, for publication
reports, quota guidance and existing equivalent support/security contacts. Search the current
support and privacy surfaces when implementing; do not add separate hardcoded copies or change
unrelated author attribution. This review updates documentation only, not that application setting.

## Governance, removal and documentation

Feature and CC BY 4.0 approval are confirmed following the September 3 Mattermost consultation.
Remaining checks are embedded-data license compatibility and accurate terms/operational disclosures.
Moderator hiding retains content for restoration; owner deletion is permanent in live storage.
Retired slugs remain reserved and all removed version URLs show the neutral unavailable page.
Document seven-day backup rotation and respect deletions if backups are restored.
Exceptional attribution requests use existing contact routes and manual handling, with no new app UI.

When implementing, update the owning workspace/persistence architecture, mission exclusion,
Data & privacy copy, account/save-load journeys and roadmap. Add a short AGENTS.md pointer if the
new per-slot read-only/publication association warrants it; do not describe planned behavior as shipped.

The separate [modeling upgrade comparison draft](../modeling-upgrade-comparison/README.md) must be
refined before sharing implementation relies on a historical-result contract.
