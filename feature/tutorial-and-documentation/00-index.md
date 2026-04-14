# Tutorial & Documentation — exploration index

This folder holds the in-progress thinking for the e-footprint and
e-footprint-interface documentation and onboarding overhaul. It is structured
so the exploration can be resumed cold from these files alone, without the
chat context that produced them.

---

## Goal

Devise a strategy and then an implementation plan for:

1. The **onboarding UX** of the e-footprint-interface (currently nonexistent).
2. The broader question of how to **document e-footprint and its interface**
   so they are easy to understand and use.
3. Doing this in a way that keeps the documentation material **always up to
   date and maintainable by design**, with explanation content defined in
   **only one place** and **as close to the code as possible**.

Constraints stated up front by the user:
- The interface onboarding should be quite interactive.
- **No videos** — they are too hard to keep up to date.
- We can take the freedom to make structural changes if they make sense, but
  simplicity and iterativity are good.

---

## Files in this folder

| File | Topic |
|---|---|
| `00-index.md` | This file — navigation, current state, open questions |
| `01-single-source-of-truth.md` | Where explanation content physically lives so mkdocs and the interface both consume it without duplication |
| `02-interface-onboarding-ux.md` | First-run experience: starter templates, guided tour, contextual help, disabled-instead-of-error UX |
| `03-web-vs-edge-modeling.md` | Clarifying the web/edge conceptual distinction and where to surface it |
| `04-efootprint-docs-overhaul.md` | What to do about the empty mkdocs stubs, the auto-generated reference, and modeling templates |
| `05-maintainability-and-build.md` | CI checks, tests, and build pipeline that keep all of this honest |
| `99-implementation-plan.md` | **The implementation plan** — seven sequential steps, each with deliverables, open questions, and a pointer to its sub-implementation plan file |

---

## Current state observed in the repos

### e-footprint (library)

- mkdocs-based site, theme `material`, configured at `e-footprint/mkdocs.yml`.
- Source files in `e-footprint/docs_sources/mkdocs_sourcefiles/`.
- Object reference pages are **auto-generated** by
  `e-footprint/docs_sources/doc_utils/generate_object_reference.py` from a
  Jinja template at `obj_template.md`. The generator reads each object's
  `__init__` signature params and `calculated_attributes` and renders a page
  per class.
- The generator currently has no place to read a human description for a
  param or a calculated attribute. For numerical params it falls back to
  things like `"{label} in {units}"`, and for unknown shapes it writes
  literally `"description to be done"`.
- **Most Explanation, How-to, and FAQ files are empty stubs** (0 lines):
  `best_practices.md`, `build_process.md`, `database_modeling.md`,
  `design_deep_dive.md`, `evolution_across_time.md`,
  `machine_learning_workflow.md`, `measurement_tools.md`, `only_CO2.md`,
  `server_to_server_interaction.md`. Only `why_efootprint.md`,
  `methodology.md`, `get_started.md`, `explanation_overview.md`, `index.md`,
  `object_reference.md` have real content.
- Tutorial content: `e-footprint/tutorial.ipynb` and a separate
  `docs_sources/doc_utils/docs_tutorial.ipynb` that drives the mkdocs Tutorial
  page via `format_tutorial_md.py`. These remain as the Python-only path and
  are out of scope for this overhaul.
- **No GitHub Actions CI workflow** — only `dependabot.yml` and issue
  templates exist under `.github/`. Tests are run locally only.

### e-footprint-interface

- Django + HTMX app, Clean Architecture: domain / application / adapters /
  templates. Documented in `e-footprint-interface/CLAUDE.md`.
- `model_builder/adapters/ui_config/` already holds three flat per-concern
  JSONs read by provider classes:
  - `class_ui_config.json` — keyed by class name; entries hold `label`,
    `more_descriptive_label_for_select_inputs`, `type_object_available`, etc.
  - `field_ui_config.json` — keyed by field/param name with a list of
    `modeling_obj_containers`.
  - `object_category_ui_config.json` — category metadata.
- `model_builder/domain/reference_data/` holds default data JSONs
  (`default_countries.json`, `default_devices.json`, `default_networks.json`,
  `default_system_data.json`).
- Per-action creation prerequisites encoded on web classes as
  `get_creation_prerequisites`, invoked inside the creation path (raises at
  creation time today — step 1 refactors this into a queryable predicate).
- `SystemValidationService` drives the "Get results" button state.
- **Zero onboarding scaffolding exists today.** No welcome screen, no tour,
  no help drawer, no template picker.

### Relationship between the two repos

- The interface depends on `efootprint` as a Python package (editable install
  for local co-dev). Dependency only goes interface → library, never the
  reverse.
- Per the workspace `CLAUDE.md`: no need for backward compatibility, no other
  external callers, keep things lean.

---

## Decisions made (summary)

Full decisions with rationale live in the topic files. This is a quick-reference
summary.

### Single source of truth (Topic 1)
- Class semantics → class docstring in efootprint.
- Param semantics → `param_descriptions` dict on the class in efootprint.
- Calculated attribute semantics → `update_<attr>` method docstring in efootprint.
- `disambiguation`, `pitfalls`, `interactions` (Python-facing) → optional class
  attributes in efootprint.
- "How to interact in the interface" → optional `interactions` field in
  `class_ui_config.json` in the interface.
- Narrative content (methodology, how-to guides) → hand-written mkdocs pages;
  the interface deep-links to them.
- Placeholder syntax: `{kind:target}` — kinds are `class`, `param`, `calc`,
  `doc`, `ui`. `{ui:...}` forbidden in library-side strings.
- Interface consumes via `DescriptionProvider` port + adapter (CA-clean).

### Interface onboarding UX (Topic 2)
- Primary audience: non-technical product person. Technical users: depth on demand.
- Primary mode: starter template + guided tour + contextual help. No wizard, no video.
- Template picker with blank as a first-class option; templates: e-commerce,
  AI chatbot, IoT (edge).
- Two tour flavors (template, blank); scope is interface orientation +
  recommended modeling order + contextual-help discoverability. Domain
  explanations stay in contextual help / mkdocs, not in the tour.
- Auto-run on first visit only; replay + templates re-entry in a help menu.
- Disabled-instead-of-error UX: `get_creation_prerequisites` refactored into
  `can_create(model) -> (bool, reason)` predicate; buttons disabled + tooltipped
  ahead of time.

### Web vs edge modeling (Topic 3)
- No object hierarchy reorganization; no mkdocs nav restructure.
- Add canonical `web_vs_edge.md` Explanation page; `Hardware/Edge` and
  `Usage/Edge` sub-bucket intros deep-link there.
- Interface: navbar toggle (off / on / latched). Off by default for web
  templates; IoT template ships with toggle latched on. Edge badges on cards
  (visual only). No separate edge column.

### e-footprint docs overhaul (Topic 4)
- Keep Diátaxis. Delete `design_deep_dive.md` and `evolution_across_time.md`.
- Write three How-to stubs and four FAQ stubs. Add `web_vs_edge.md`.
- Reference stays strictly auto-generated, augmented with Topic 1 SSOT metadata.
- Modeling templates: three categories — `how_to` (library-owned, ships with
  PyPI), `introductory` (interface-owned, tour-coupled), `other` (interface-
  owned, grab-bag). Each template: serialized `System` JSON + Python registry.
- Library exposes `efootprint.modeling_templates` as a public API; interface
  imports at runtime.

### Maintainability and build (Topic 5)
- Tests baked in at each implementation step per the phasing in
  `05-maintainability-and-build.md`. Library CI created in Step 1. Final
  gap-check in Step 7.

---

## Open questions

These questions remain open and are flagged at the top of their respective
step in `99-implementation-plan.md`.

- **Ban-word list finalization** (Step 2): starting list is `click`, `button`,
  `drag`, `instantiate`, `import`, backtick. Lock when first content is written.
- **Help drawer visual form** (Step 3): slide-in panel vs modal — decide at
  implementation start by inspecting existing templates.
- **How-to Python snippet strategy** (Step 4): hand-copy first; upgrade to
  build-time rendering only if drift becomes real.
- **Fate of `default_system_data.json`** (Step 6A): becomes the blank baseline,
  migrates into introductory templates, or gets deleted. Decide before writing
  template JSONs.
- **Help menu placement** (Step 6B): navbar, floating button, or side panel —
  confirm at implementation start.
- **Badge visual design** (Step 5): icon, coloured dot, or corner stripe —
  minor; decide at implementation start.

---

## How to resume from cold context

1. Read this file end to end.
2. Read `99-implementation-plan.md` for the seven-step implementation plan and
   the open questions gating each step.
3. Read the topic file(s) relevant to the step you are about to implement for
   the full design decisions and rationale:
   - Steps 2, 3 → `01-single-source-of-truth.md`
   - Steps 1, 6 → `02-interface-onboarding-ux.md`
   - Steps 4, 5 → `03-web-vs-edge-modeling.md`
   - Steps 4, 6 → `04-efootprint-docs-overhaul.md`
   - All steps → `05-maintainability-and-build.md`
4. Create the sub-implementation plan file for the step (e.g.
   `step-01-disabled-ux.md`) and review it before starting implementation.
