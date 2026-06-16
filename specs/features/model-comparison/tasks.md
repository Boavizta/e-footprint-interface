# Model comparison — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html) (rev 4, v1). **Plan:** [`plan.html`](plan.html).

Cross-repo feature. Task 1 lands in **`e-footprint`** (library); Tasks 2–5 land in **`e-footprint-interface`**. Task 1 delivers the library code, tests, and version bump; **the maintainer performs the PyPI release manually**, outside the implementation task. Interface tasks develop against the **local editable install** of `e-footprint` (workspace co-dev) and are not blocked on the publish — they only require Task 1's code to be complete. The released-version pin in `pyproject.toml` (no editable path on `main`, constitution §2.4) is a pre-merge requirement, satisfied once the maintainer has published.

---

## Task 1 — Library: `efootprint.comparison` capability + duplication helpers (e-footprint)

**Status:** Done

**Goal:** Add the domain-truth comparison computation and duplication helpers to the library, usable standalone from a notebook / coding agent, and release them to PyPI. The whole feature reduces to `a.compare_to(b)` and `duplicate_system(s)` for a standalone user; the interface becomes a thin adapter over this. No new modeling logic, no attribution/sensitivity claims (constitution §1.3).

**Files touched (in `e-footprint`):**
- `efootprint/comparison/` — new subpackage: `SystemComparison` computing KPI totals + Δ (abs/%), per-(category, phase) decomposition from each system's `total_energy_/fabrication_footprint_sum_over_period` dicts (already category-keyed and summing to the total, so bars sum to the headline Δ by construction; category SSOT = `OBJECT_CATEGORIES`), and aligned + cumulative time-series on a shared calendar axis/unit.
- `efootprint/comparison/` — input diff: walk `all_linked_objects`, split inputs from computed via `calculated_attributes`, **match by object id first, then by (name, type)**, emit changed-attribute rows (value+unit, source/confidence) + "only in A / only in B".
- `efootprint/comparison/` — `SystemComparison.plot_*()` simple matplotlib/plotly notebook plots (paired emissions-over-time, cumulative overlay, diverging decomposition), reusing existing deps + `EmissionPlotter` patterns. The web does not consume these.
- `efootprint/core/system.py` — `System.compare_to(other) → SystemComparison` notebook entry point, mirroring `System.plot_*`.
- `efootprint/api_utils/` (or the comparison subpackage) — `duplicate_system(system) → System` (serialize→deserialize round-trip via `system_to_json`/`json_to_system`, **mint a fresh System id, preserve all object ids**) and sibling `assign_fresh_system_id(system)` (re-id the System object only, leaving object ids intact).
- `pyproject.toml` — MINOR version bump (e.g. 22.1.0). The PyPI upload per `RELEASE_PROCESS.md` is done **manually by the maintainer**, not as part of this task.
- `specs/architecture.md` (e-footprint) — document the new `comparison` capability; `CHANGELOG.md`.

**Tests added/changed:**
- `tests/test_system_comparison.py` — Δ arithmetic; decomposition sums to the headline Δ; id-first diff with (name, type) fallback and "only in A/B"; aligned + cumulative series; `duplicate_system` (fresh System id, preserved object ids); plot helpers smoke-render.

**Acceptance:**
- `system_a.compare_to(system_b)` returns a `SystemComparison` whose per-(category, phase) deltas sum to the headline total delta.
- The input diff pairs objects by id first, falls back to (name, type), and lists unmatched objects as A-only / B-only; identical inputs are not emitted.
- `duplicate_system` produces a System with a new id whose object ids are unchanged.
- Notebook plot helpers render without error.
- Library suite green; `pyproject.toml` bumped to the new MINOR version. (PyPI publish is performed manually by the maintainer, outside this task.)

**Depends on:** none.

---

## Task 2 — Interface: workspace persistence layer + active-slot call-site sweep (e-footprint-interface)

**Status:** Done

**Goal:** Move the session from holding one model to holding a workspace of up to two per-slot blobs plus an active-slot pointer, **without any user-visible change**. After this task a session that never adds a second model behaves exactly as today (the per-slot repo defaults to the active slot). This is the "infrastructure landed but unused" milestone — the single-model no-regression path is the gate.

**Files touched:**
- `model_builder/domain/interfaces/` — new `IWorkspaceRepository` (`list_slots`, `active_slot`, `set_active_slot`, `add_slot(system_data) → slot`, `remove_slot`, `repository_for(slot) → ISystemRepository`); keeps `ISystemRepository` single-model.
- `adapters/repositories/session_system_repository.py` — slot-aware: constructed for a slot (defaults to active); `_cache_key → system_data:{session_key}:{slot}` for all slots; one-release legacy unsuffixed-key read-fallback with write-through; per-slot `clear()`; reports its with-calc payload size (the per-payload cap relocates to the workspace budget).
- `adapters/repositories/session_workspace_repository.py` — new: implements `IWorkspaceRepository` over the Django session; stores the tiny index (slot ids + active + each slot's last-saved with-calc byte size); vends `SessionSystemRepository` bound to a slot; **owns the shared payload budget** (rejects a save/add when the summed with-calc size over all slots would exceed `MAX_PAYLOAD_SIZE_MB`, sibling sizes read from the index — no re-serialization of the untouched slot); **single enforcement point for the distinct-system-id invariant** (the add-to-slot path mints a fresh system id whenever an incoming model's id already exists in another slot — covers import, workspace import, template, blank, duplicate).
- `adapters/repositories/in_memory_system_repository.py` + in-memory workspace — mirror slot-awareness for the integration harness (constitution §1.2 interchangeability).
- `version_upgrade_handlers.py` — home for the legacy-key migration note (remove the read-fallback next release; documented inline).
- ~25 `ModelWeb(SessionSystemRepository(request.session))` call sites across `views.py`, `views_addition/edition/deletion/dict_mutation/onboarding`, `sankey_views.py` — mechanical sweep to resolve the active-slot repository (one sweep per the systematic-edits convention).
- `pyproject.toml` — develop against the local editable `efootprint` (`poetry add ../e-footprint --editable`); pin to the released version before merging to `main` (no editable path on `main`, constitution §2.4). Same applies to Tasks 3–5.
- `specs/architecture.md` (interface) — new "Workspace / multi-slot session" subsection; `specs/mission.md` — amend the singular "the current model lives in the Django session" line.

**Tests added/changed:**
- Unit — slot-aware cache-key + legacy read-fallback; workspace index lifecycle (add / switch / remove); the **shared-budget guard** (summed with-calc size capped, not per slot); the distinct-system-id invariant (incoming id colliding with another slot is re-minted).
- Integration — in-memory workspace add/switch/remove at the repository level; "import the same file/template into both slots" gets distinct system ids; **single-model no-regression** (a session that never adds a second model behaves exactly as today); Clean-Architecture no-Django-in-domain guard stays green.

**Acceptance:**
- Existing unit + integration suite green with no behavioural change for single-model sessions.
- Cache keys are symmetric (`…:{slot}`) for all slots; an in-flight unsuffixed slot-0 payload is read once and written through.
- Summed with-calc weight of both slots is enforced against `MAX_PAYLOAD_SIZE_MB`; two slots can never hold the same system id.

**Depends on:** Task 1's code (`assign_fresh_system_id`), consumed via the editable local install. The released-version pin is a pre-merge requirement, not a blocker for starting.

---

## Task 3 — Interface: two-model builder — tabs, resident canvases, switch / add / remove (e-footprint-interface)

**Goal:** The first user-visible milestone — two independent models coexist in one session, each with the full builder, one active for editing, switchable with no network round-trip. The user can add the second model by duplication, import, or blank/template, and remove it to return to single-model mode. Solves the headline DOM-collision risk via the `web_id` system-id prefix chokepoint.

**Files touched:**
- `modeling_object_web.py` — prefix the object-card `web_id` (`{class}-{efootprint_id}`) with the **system id**, once at the root (every derived id, HTMX/hyperscript selector, leaderline anchor, mirrored-card ref flows from it; canvas templates need no edits; routing/form-field names are independent of `web_id`). `__hash__`/`__eq__` become system-scoped.
- `adapters/views/views.py` — `model_builder_main`, `render_model_builder`, `load_system_into_session`, `reset_model` become slot-aware; render the tab strip + **both** resident canvases (active visible); per-model `download_json`/`upload_json` operate on a target slot (upload routes through the workspace add-to-slot path, inheriting the distinct-id guard + remaining-budget check).
- `adapters/views/views_workspace.py` — new endpoints: `switch-model` (flip active slot server-side), `add-model` (duplicate / import / blank), `remove-model`. (`compare` endpoint deferred to Task 4.)
- `model_builder/urls.py` — register the new kebab-case routes.
- `adapters/views/views_onboarding.py`, `exception_handling.py` — template picker / recovery become slot-aware (target slot; per-slot raw download in recovery).
- Duplication wiring (use case / view) — calls library `duplicate_system`; proposes `"Copy of {system name}"` (user-editable).
- `oob_regions.py` — the `model_canvas` region emits the **active** slot's `#model-canva-{slot}` (OOB first-match-by-id correctness).
- `templates/model_builder/model_builder_main.html` — tab strip above the builder; two `#model-canva-{slot}` containers (active shown); shared `#sidePanel`, `#helpDrawer`, results panel stay singletons.
- `templates/model_builder/components/model_tab_strip.html` — new: Model A · Model B · ＋Add menu (Duplicate / Import / Blank) · ⇄Compare (**disabled** until Task 4 ships the dashboard).
- `theme/static/scripts/` — leader-line build/teardown keyed on tab visibility (skip the hidden canvas); tab toggle mirroring the Results/Sources `d-none/d-block` pattern (hyperscript/vanilla, no SPA).

**Tests added/changed:**
- Integration — two-model add/switch/remove via the endpoints; mutation-on-B-while-A-resident targets the active canvas (OOB); per-model export/import round-trip into a target slot.
- E2E (Playwright) — duplicate → edit B → refresh preserves both models + active selection → remove B returns to single-model mode.
- Jest/E2E — no DOM id appears twice across the two resident canvases.

**Acceptance:**
- From a single-model session the user can add a second model three ways, switch between them with no round-trip, edit each independently, and remove the second to return to today's flow.
- No DOM id collides across the two resident canvases; leader lines build only for the visible canvas.
- Both models, names, and active selection survive a refresh.
- ⇄Compare remains disabled (enabled in Task 4).

**Depends on:** Task 2 (slot-aware repos), Task 1 (`duplicate_system`).

---

## Task 4 — Interface: comparison dashboard — adapter, view, charts (e-footprint-interface)

**Goal:** The payoff milestone — the ⇄Compare tab renders the §4.2 dashboard: KPI strip with delta, the "what explains the difference" decomposition, the paired emissions-over-time and cumulative charts (shared scales/legends), and the assumptions diff. Re-rendered fresh on every visit (no stale results). The interface stays a thin adapter over the library `SystemComparison` (constitution §1.3).

**Files touched:**
- `domain/services/comparison_service.py` — new thin adapter: calls `model_a.system.compare_to(model_b.system)` and shapes the `SystemComparison` into Chart.js JSON (paired bars, cumulative overlay, decomposition), KPI-strip values, and the diff-table view model. No modeling logic; no Django imports.
- `adapters/views/views_workspace.py` — `compare` endpoint rendering the dashboard.
- `templates/model_builder/compare/dashboard.html` + partials — KPI strip, decomposition, paired chart, cumulative, assumptions diff (the §4.2 canonical layout; static markup + chart JSON from `ComparisonService`).
- result-charts TS source → `theme/static/bundles/result_charts.js` — new Chart.js variants: paired bars (one shared y-axis + one capsule legend driving both series), cumulative overlay with shaded gap, horizontal diverging decomposition bars; rebuilt via `npm run build:result-charts`.
- `templates/model_builder/components/model_tab_strip.html` — enable ⇄Compare once two models exist (disabled-instead-of-error tooltip until then).
- `specs/architecture.md` (interface) — document the thin `ComparisonService` adapter + the new chart variants.

**Tests added/changed:**
- Unit — `ComparisonService` shapes a known `SystemComparison` into the expected chart JSON / KPI values / diff-table view model.
- Jest — the new chart variants' data-shaping (shared-scale paired bars, cumulative overlay).
- E2E — open Compare → see the headline Δ (extends Task 3's flow: duplicate → edit B → open Compare → see Δ).

**Acceptance:**
- With two models present, ⇄Compare is enabled and renders the full §4.2 dashboard: headline totals + Δ (abs/%), decomposition bars summing to the Δ, paired + cumulative charts on shared scales/legends, assumptions diff (id-first match, differences only).
- An edit to either model is reflected the next time Compare is opened (no stale results).

**Depends on:** Task 3 (two models + tab strip host), Task 1 (`System.compare_to`).

---

## Task 5 — Interface: combined workspace file — export / import both models (e-footprint-interface)

**Goal:** Add the additive workspace file that bundles both models, restoring them in one action, and the two-granularity Download/Upload menu (this model / whole workspace). The single-model file format stays byte-for-byte unchanged and circulates freely between single- and two-model sessions, both directions.

**Files touched:**
- `download_workspace` / `upload_workspace` — new endpoints (`views.py` / `views_workspace.py`) producing/consuming the §2.7 envelope (`efootprint_workspace_version`, `active_slot`, `models[]` of two byte-for-byte single-model documents, no calculated attributes; recomputed on import, then the shared budget + distinct-system-id invariant apply). Filename `"{datetime} UTC workspace ({name A} vs {name B}).e-fw.json"`.
- `model_builder/urls.py` — `download-workspace` / `upload-workspace` routes.
- Content-based detection: a top-level `models` key ⇒ workspace file; `.e-fw.json` extension is a UX hint only. Cross-format robustness: "Open workspace file" fed a single-model file loads it into the active slot; "Replace this model" fed a workspace file errors with guidance (honest-error / disabled-instead-of-error) rather than corrupting state.
- `templates/.../upload_download_reboot_model_tooltips.html` — Download/Upload gain the two granularities (this model / whole workspace) per §4.1.
- `CHANGELOG.md` in both repos (constitution §2.6).

**Tests added/changed:**
- Integration — per-slot + workspace export/import round-trips, including the single-model-file-into-workspace and workspace-file-into-single-slot cross-format paths; combined-budget rejection on duplicate/import; distinct-system-id enforced after a workspace import whose two models share an id; the single-model file format is unchanged (round-trips with single-model sessions both directions).

**Acceptance:**
- The user can export both models as one `.e-fw.json` workspace file and re-import it to restore both slots + the active pointer in one action.
- Any single-model file imports into either slot; any per-slot export opens in a plain single-model session — full round-trip compatibility.
- The combined file never alters the single-model format; cross-format mismatches fail safely with guidance.

**Depends on:** Task 3 (per-model slot-aware import/export + workspace add-to-slot path + budget guard). Independent of Task 4.

---

## Ordering rationale

The ordering edge is **cross-repo but soft on the publish**: Task 1 must land the library `comparison` capability and `duplicate_system`/`assign_fresh_system_id` first, but the interface tasks consume it via the **local editable install**, so they can begin as soon as Task 1's code is complete — they do not wait on the PyPI upload (which the maintainer performs manually). The released-version pin in `pyproject.toml` is required only before any interface task reaches `main` (constitution §2.4, guarded by the pyproject-parsing test).

Within the interface, the split follows behavioural pause points, not layer boundaries:

- **Task 2 is "infrastructure landed but unused."** The workspace repository, slot-aware cache, shared budget, distinct-id invariant, and the ~25 call-site sweep are tightly coupled — the slot-aware repo is inert until the call sites resolve through it, and the sweep is precisely what proves the default-to-active-slot behaviour preserves single-model flows (its acceptance gate is the existing suite, green). No user-visible change yet.
- **Task 3 is the first user-visible change** — two models coexist and are independently editable. The `web_id` system-id prefix (the headline correctness risk) must land with the two-canvas rendering: splitting them would leave an intermediate with colliding DOM ids. Per-model slot-aware import/export rides along because it completes the spec's "three ways to add a model" (import being one of them) and there is no behavioural pause point between the canvas plumbing and wiring its toolbar.
- **Task 4 is the second user-visible change** — comparison itself. The adapter, the dashboard template, and the three Chart.js variants serve one view; splitting them would create review boundaries with no demoable pause point (the dashboard doesn't work until all three land). It is kept separate from Task 3 because "two models coexist" and "now compare them" are genuinely independent, separately demoable milestones, and merging them would produce a single review spanning persistence-adapter + DOM rendering + chart JS that is too large to review well.
- **Task 5 is file circulation** — the additive combined workspace file, an independent capability from the comparison view. It depends only on Task 3's slot machinery, so it and Task 4 can land in either order after Task 3.
