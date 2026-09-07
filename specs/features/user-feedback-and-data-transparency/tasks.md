# User feedback and data transparency — tasks

Status: Tasks — proposed · 2026-09-07

Inputs: [approved specification](spec.html) · [approved plan](plan.html)

Each numbered task is one review-sized, independently shippable commit or pull request. Tasks 1 and 2 may be implemented independently; the remaining tasks follow their stated dependencies. When a task is implemented on its own, its delivery includes the relevant constitution checks, focused test suites, and an `Unreleased` changelog entry. A feature-wide implementation may consolidate those entries before delivery.

## 1. Add a safe, attachment-explicit feedback flow

**Status:** Done

Replace the global GitHub shortcut with a useful Feedback entry that works with and without the model-builder side panel. Keep report content under the user's control: the application may help download the current modeling JSON, but it must never attach it or put model data, user-entered text, exception messages, or tracebacks in a URL.

Implementation units:

- Add an ordinary support route and template with GitHub issue and email fallback actions.
- Progressively enhance that route into the existing builder side panel; leave Home and recovery as normal page navigation.
- Put Feedback in the existing mobile toolbar menu and desktop navbar without creating another permanent toolbar control.
- Provide the explicit “Download my current modeling to include” action. Keep downloading and opening GitHub/email as separate user actions and warn the user to review the public attachment.
- Remove the exception message from generated issue URLs; retain only a non-sensitive exception type when useful.
- Add the same email fallback and attachment warning to the recovery experience while preserving its hydration-free raw download behavior.

Files:

- `theme/templates/navbar.html`
- `theme/templates/base.html`
- `theme/static/scripts/support.js` (new)
- `model_builder/templates/model_builder/upload_download_reboot_model_tooltips.html`
- `model_builder/templates/model_builder/support.html` (new)
- `model_builder/templates/model_builder/recovery.html`
- `model_builder/adapters/views/views_support.py` (new)
- `model_builder/adapters/views/exception_handling.py`
- `e_footprint_interface/urls.py`
- `model_builder/urls.py`
- `js_tests/build_fixtures.py`
- `js_tests/support.test.js` (new)
- `tests/unit_tests/adapters/views/test_views_support.py` (new)
- `tests/unit_tests/adapters/views/test_exception_handling.py` (new or extend the existing exception test module)
- `tests/unit_tests/adapters/views/test_recovery_views.py` (new)

Acceptance:

- Feedback is reachable from the desktop navbar and mobile menu everywhere; the builder uses its existing side panel when JavaScript is available, while the underlying URL remains fully usable alone.
- The feedback UI has neither a free-text field nor an “include my current modeling” checkbox.
- The download action never automatically opens, submits, or attaches anything to GitHub or email.
- Generated GitHub and `mailto:` URLs contain a prompt only and reveal no model content, user content, exception message, or traceback.
- Recovery feedback/download paths do not hydrate or deserialize the model.
- Focus handling, keyboard navigation, external-link behavior, and failed panel loads have explicit test coverage.

Dependencies: none.

## 2. Implement bounded cache retention and supervised expiry cleanup

**Status:** Done

Establish the lifecycle foundation before exposing it in the UI: a one-hour hot-cache TTL for system model data, a session-bound recovery-retention preference, in-place expiry updates for existing recovery entries, and reliable physical deletion of expired cache and session rows.

Implementation units:

- Set `SESSION_COOKIE_AGE` explicitly to 14 days and change only system-model Redis entries from 10 minutes to one hour; keep the generic cache timeout unchanged.
- Define one shared recovery-retention policy with the allowlist `1h, 3h, 6h, 12h, 1d…14d`, a 12-hour default, and a hard cap at the session-cookie age.
- Store the preference in the current Django session. Apply it to future PostgreSQL recovery writes and touch the expiry of each currently occupied slot when it changes; do not alter Redis expiry.
- Return per-slot success/failure information without rolling back successful touches when one slot has already expired or disappeared.
- Add a one-shot management command that deletes expired `django_cache` and `django_session` rows and reports count/duration only.
- Run an immediate purge followed by an hourly purge from the existing production Supervisor configuration. Keep the command safe and idempotent when more than one web scaler runs it.
- Document the supervised maintenance-worker convention in the repository guidance because it is a new production pattern.

Files:

- `e_footprint_interface/settings.py`
- `model_builder/adapters/repositories/session_system_repository.py`
- `model_builder/adapters/repositories/cache_backend.py`
- `model_builder/adapters/repositories/recovery_retention.py` (new, if a dedicated policy module is used)
- `model_builder/management/__init__.py` (new if absent)
- `model_builder/management/commands/__init__.py` (new if absent)
- `model_builder/management/commands/purge_expired_session_data.py` (new)
- `docker/conf/supervisord-prod.conf`
- `AGENTS.md`
- `specs/architecture.md`
- `tests/unit_tests/test_settings.py` (new or extend the existing settings test module)
- `tests/unit_tests/adapters/repositories/test_recovery_retention.py` (new)
- `tests/unit_tests/adapters/repositories/test_workspace_repository.py`
- `tests/unit_tests/management/test_purge_expired_session_data.py` (new)

Acceptance:

- Newly saved system data expires from Redis after one hour, while unrelated cache entries retain their configured policy.
- Recovery retention defaults to 12 hours, accepts exactly the approved choices, cannot exceed 14 days, persists with the session, and is used by subsequent saves.
- Changing retention performs at most one expiry touch per occupied slot (currently at most two), performs no hydration or serialization, and reports partial disappearance safely.
- The purge command removes only expired recovery-cache and session rows, preserves live rows, reveals no identifiers or payloads in logs, and behaves safely under concurrent execution.
- Production Supervisor starts the purge loop immediately and repeats it every 3,600 seconds without coupling cleanup to request traffic.
- Unit/database tests cover boundaries, corrupt or absent session values, empty workspaces, partial touch failure, and concurrent/idempotent cleanup.

Dependencies: none.

## 3. Expose an accurate Data & privacy panel and retention controls

**Status:** Done

Add the user-facing explanation and controls on top of Task 2. Present operational facts in plain language, distinguish the browser, Redis, live PostgreSQL, and backup lifecycles, and show detailed storage size from existing integer metadata.

Implementation units:

- Add `Data & privacy` under the existing Help menu and render it in the builder side panel through a normal, reusable route.
- Explain the opaque two-week browser session cookie, the small workspace index/preferences in `django_session`, the one-hour Redis hot cache, configurable PostgreSQL recovery cache, Boavizta as operator, Clever Cloud as processor/host, Paris hosting, and the security contact.
- State only already-confirmed encryption facts: live PostgreSQL is encrypted at rest; daily PostgreSQL backups are retained for seven days and are not encrypted at rest unless actual activation is later confirmed. Do not make a generic “all data is encrypted” claim.
- Explain that short retention such as six hours normally expires before the nightly backup window but is not a contractual guarantee that data cannot enter a backup.
- Add the retention selector and CSRF-protected update action, including clear per-slot results and wording that expiry is measured from the latest save or retention change.
- Add a total workspace-size accessor that sums existing canonical per-slot byte integers and expose detailed current size plus the configured shared-instance limit in this panel.
- Explain that the production 50 MB value is a public shared-deployment capacity policy, not a JSON-format or model limit, and that self-hosters can raise it.

Files:

- `model_builder/templates/model_builder/components/help_menu.html`
- `model_builder/templates/model_builder/side_panels/data_privacy.html` (new)
- `model_builder/adapters/views/views_support.py`
- `model_builder/adapters/views/data_status.py` (new)
- `model_builder/adapters/repositories/workspace_index.py`
- `model_builder/urls.py`
- `e_footprint_interface/settings.py`
- `theme/static/scss/custom.scss`
- `theme/static/css/bs_main.css`
- `theme/static/css/bs_main.css.map`
- `specs/design/journeys/save-and-load.html`
- `tests/unit_tests/adapters/views/test_data_status.py` (new)
- `tests/unit_tests/adapters/views/test_views_support.py`
- `tests/unit_tests/adapters/repositories/test_workspace_repository.py`

Acceptance:

- The panel is keyboard-accessible from Help and remains usable as a standalone route.
- Its copy clearly separates hot cache, recovery rows, live database storage, and seven-day backups, including which layers are currently known to be encrypted at rest.
- The selector exposes exactly `1h, 3h, 6h, 12h, 1d…14d`, shows 12 hours by default, survives navigation through the session, and immediately updates occupied recovery expiries without touching Redis.
- Current workspace size and configured limit render from stored integer metadata only; opening or refreshing the panel performs no model hydration or serialization.
- Deployment-specific facts remain configurable so a self-hosted installation is not forced to claim Clever Cloud, Paris, 50 MB, or Boavizta operation.

Dependencies: Task 2.

## 4. Add the lightweight real-time shared-budget warning

**Status:** Done

Surface storage pressure only when it becomes actionable. Reuse the canonical size integers and update a stable status region across every persistence boundary without introducing model serialization, hydration, polling, or a permanently visible technical meter.

Implementation units:

- Add a stable `workspace-storage-status` region between the builder toolbar and canvas. Render it empty below 80% of the configured shared JSON budget and as an accessible caution at or above 80%, with current size, limit, and a link to Data & privacy.
- Centralize status rendering and HTMX out-of-band response generation.
- Refresh it after full builder renders (including import, reset, add, and remove), CRUD persistence through `HtmxPresenter`, result materialization, and Sankey persistence/deletion.
- After card-order autosave succeeds, request a metadata-only status partial; do not return or recompute the full builder.
- Preserve the existing hard-limit error behavior at 100% and keep the caution non-blocking.

Files:

- `model_builder/templates/model_builder/model_builder_main.html`
- `model_builder/templates/model_builder/components/workspace_storage_status.html` (new)
- `model_builder/adapters/views/data_status.py`
- `model_builder/adapters/presenters/htmx_presenter.py`
- `model_builder/adapters/views/views.py`
- `model_builder/adapters/views/sankey_views.py`
- `theme/static/scripts/model_builder_main.js`
- `theme/static/scss/custom.scss`
- `theme/static/css/bs_main.css`
- `theme/static/css/bs_main.css.map`
- `js_tests/build_fixtures.py`
- `js_tests/model_builder_main.test.js`
- `tests/unit_tests/adapters/presenters/test_htmx_presenter.py` (new or extend the existing presenter test module)
- `tests/unit_tests/adapters/views/test_data_status.py`
- `tests/unit_tests/adapters/views/test_card_order_views.py`
- `tests/unit_tests/adapters/views/test_sankey_views.py`
- `tests/e2e/pages/model_builder_page.py`
- `tests/e2e/test_data_privacy.py` (new)

Acceptance:

- No quota indicator is visible below 80%; exactly at 80% the caution appears, remains non-blocking, and links to the detailed panel. The existing limit error remains authoritative at 100%.
- Initial/full render, CRUD, calculated-result persistence, Sankey changes, deletion/reset/import, and card reordering all leave the status correct.
- Size display is O(number of workspace slots), currently O(2), from existing integer metadata. No status path hydrates or serializes a model.
- The status region is announced accessibly without stealing focus, and repeated out-of-band updates do not duplicate it.
- One end-to-end flow proves the retention control and warning work together in the real builder.

Dependencies: Tasks 2 and 3.

## 5. Reconcile the release with Clever Cloud’s final written answers

This is deliberately the final task. Do not close it, finalize production privacy copy, or replace a known negative fact with an optimistic assumption until the outstanding provider answers have been received and checked against the running services.

Provider facts to close:

- Redis encryption at rest.
- Redis transport protection: TLS (`rediss://`) or a documented equivalent encrypted private path.
- Confirmation that Redis backups are disabled, including any persistence/snapshot behavior that remains.
- PostgreSQL backup encryption pricing: whether the quoted €100 is one-off or recurring, which backups/regions it covers, and whether encryption has actually been activated.

Implementation units:

- Record the dated written answers and distinguish provider confirmation from direct runtime checks.
- Reconcile production settings, environment documentation, and Data & privacy copy with the final state. If PostgreSQL backup encryption has not actually been activated, continue to say plainly that the seven-day backups are not encrypted at rest.
- Verify the deployed Redis baseline (`maxmemory` 128 MB, `allkeys-lru`), one-hour system TTL, memory headroom, cache hits/misses, evictions, rejected writes, and cleanup-worker logs. Treat eviction as resilience behavior, not as a retention guarantee.
- Verify that containers, Redis, and PostgreSQL are still hosted in Paris and that the documented operator, processor, and security contact remain accurate.
- Harmonize the architecture and save/load journey documentation with the verified release behavior and document PostgreSQL backups as required resilience for the forthcoming public-link sharing feature without implementing that feature here.
- Run the focused regression suites plus the critical end-to-end privacy/retention flow and consolidate the feature changelog entry.

Files:

- `e_footprint_interface/settings.py`
- `INSTALL.md`
- `docker/README.md`
- `model_builder/templates/model_builder/side_panels/data_privacy.html`
- `specs/architecture.md`
- `specs/design/journeys/save-and-load.html`
- `CHANGELOG.md`
- `tests/unit_tests/test_settings.py`
- `tests/unit_tests/adapters/views/test_views_support.py`
- `tests/e2e/test_data_privacy.py`

Acceptance:

- Every production privacy statement is traceable to a current provider answer or a recorded runtime check; unknowns remain labeled as unknown and generic encryption claims are absent.
- Redis transport, at-rest protection, and backup/persistence status are described separately and accurately.
- PostgreSQL live-data encryption and backup encryption/retention are described separately; paying for a custom setup is never presented as activation evidence.
- Production configuration and public copy agree on region, actors, contact, cookie age, hot-cache TTL, recovery choices, shared budget, and backup lifecycle.
- Operational checks confirm the deployed TTL/eviction/cleanup behavior without inspecting user payloads.
- All focused Python, JavaScript, rendered-fixture, and critical end-to-end tests pass, and the changelog and durable architecture/journey documentation match the shipped behavior.

Dependencies: Tasks 1–4 and all final Clever Cloud answers listed above.
