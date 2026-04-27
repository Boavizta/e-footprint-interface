# Implementation Plan — Tutorial & Documentation

High-level, iterative plan for the tutorial and documentation overhaul. Each step is small enough to be reviewed independently and builds on the one before. The step ordering maximises early UX wins while ensuring each successive step has its prerequisites in place.

Each step gets a dedicated sub-implementation plan file (linked below) written and reviewed before implementation begins. This file stays intentionally high-level; the topic files (`01`–`05`) hold the design decisions and rationale.

---

## Step overview

| # | Title | Repos touched | Sub-plan |
|---|---|---|---|
| 1 | Disabled-instead-of-error UX | interface + lib CI | `step-01-disabled-ux.md` |
| 2 | SSOT metadata in e-footprint | library | `step-02-ssot-library.md` |
| 3 | Surface SSOT in the interface | interface | `step-03-ssot-interface.md` |
| 4 | Docs overhaul + library modeling templates | library | `step-04-docs-library-templates.md` |
| 5 | Web vs edge in the interface | interface | `step-05-edge-interface.md` |
| 6 | Introductory templates + guided tour | interface | `step-06-templates-tour.md` |
| 7 | Maintainability and build review | both | `step-07-build-review.md` |

---

## Step 1 — Disabled-instead-of-error UX

**Goal:** Replace after-the-fact errors with preemptively disabled buttons and hover tooltips that tell the user what to do next. Highest-value UX change with the smallest scope of new content; no SSOT plumbing needed.

**Deliverables — interface**
- Refactor `get_creation_prerequisites` into a queryable predicate `can_create(model) -> (bool, reason_str)` on each web class that has prerequisites. The existing prerequisite logic moves into the predicate; the creation use case still calls the predicate as its last line of defence, so the two call sites share one implementation.
- Templates and presenter updated to call the predicate when rendering action buttons: disabled state + hover tooltip when `enabled == False`.
- Tooltip copy is plain English; it references what object to create first, not how to click UI elements.
- Existing tests that assert raising behaviour updated to assert the predicate form.
- New unit tests: for every class with prerequisites, `can_create` returns `(False, non_empty_string)` when the prerequisite is absent and `(True, "")` when present.

**Deliverables — library (parallel, independent)**
- Create `.github/workflows/ci.yml` for the e-footprint library: run the existing pytest suite on every push. Python 3.12.

**Open questions before starting:** None — decisions are locked in `02-interface-onboarding-ux.md`.

**Draws from:** `02-interface-onboarding-ux.md` (Disabled-instead-of-error UX section), `05-maintainability-and-build.md` (`can_create` predicate tests).

---

## Step 2 — SSOT metadata in e-footprint

**Goal:** Add the structured description metadata defined in Topic 1 to every concrete e-footprint class, and write the tests that enforce completeness. This is the authorship step that steps 3, 4, and 6 all depend on.

**Deliverables — library**
- `param_descriptions` dict on every concrete class. Keys must exactly cover `__init__` params minus `self` and `name`. Values are plain English strings — no markdown, no `{ui:...}` placeholders.
- Class docstring on every concrete class that lacks one.
- Docstring on every `update_<attr>` method (one sentence per calculated attribute).
- `disambiguation`, `pitfalls`, `interactions` class attributes added where warranted (optional; absent means section not rendered by consumers).
- `param_interactions` dict where warranted (optional, sparse).
- `tests/test_descriptions.py` covering all seven checks from Topic 1: docstring presence, `param_descriptions` coverage, `update_<attr>` docstrings, `param_interactions` subset, placeholder resolution, unknown-kind rejection, and ban-word check. Hard failures from day one — tests drive content authorship.
- `generate_object_reference.py` upgraded to read the new attributes and render them in `obj_template.md`. Replaces `"description to be done"` and `"{label} in {units}"` fallbacks. Resolves `{kind:target}` placeholders during generation. `{ui:...}` and unknown kinds in library strings are rejected.

**Open questions before starting:** Finalize the ban-word list (starting point: `click`, `button`, `drag`, `instantiate`, `import`, backtick). Lock the list when the first content is written; tune based on what real sentences naturally want to say.

**Draws from:** `01-single-source-of-truth.md` (shape of content, placeholder syntax, tests).

---

## Step 3 — Surface SSOT in the interface

**Goal:** Make library-side metadata visible in the interface via the `DescriptionProvider` port. Deliver info icons on fields and class cards as the first tangible UX improvement from the SSOT investment.

**Deliverables — interface**
- `DescriptionProvider` protocol in `model_builder/domain/interfaces/`.
- `EfootprintDescriptionProvider` adapter in `model_builder/adapters/` reading library-side class attributes and `class_ui_config.json` via introspection. Returns placeholder-resolved strings; the interface domain layer never sees raw `{kind:target}` tokens.
- `{ui:token}` registry: a small module mapping tokens to UI element display names and/or selectors. Tokens appear only in `class_ui_config.json` `interactions` fields.
- `class_ui_config.json` extended with optional `interactions` field for relevant classes.
- Info icons on every field (param) and on class cards, rendering tooltip content from `param_descriptions` and class docstring respectively.
- Help drawer (slide-in panel) rendering class description, `disambiguation`, `pitfalls`, and `interactions` for the selected object type. Linked from class cards.
- New tests:
  - `{ui:token}` resolution: every token appearing in any description string has a registered handler entry.
  - `class_ui_config.json` completeness: every key is a known class; every class in `MODELING_OBJECT_CLASSES_DICT` either has an entry or is in an explicit exclusion list.
  - `DescriptionProvider` round-trip: construct provider, call each method on a representative class, assert non-None for present fields.

**Open questions before starting:** Help drawer visual form (slide-in panel vs modal) — decide at implementation start by inspecting existing templates.

**Draws from:** `01-single-source-of-truth.md` (DescriptionProvider port, placeholder syntax, interface-side tests), `05-maintainability-and-build.md` (Step 1 interface checks).

---

## Step 4 — Docs overhaul + library modeling templates

**Goal:** Fill the empty mkdocs stubs, add `web_vs_edge.md`, delete dead stubs, and create the library-owned how-to modeling templates with their registry. Wire mkdocs CI.

**Deliverables — library**

*mkdocs content*
- Delete `design_deep_dive.md` and `evolution_across_time.md`.
- Write `web_vs_edge.md` (Explanation): defines the two paradigms, explains when to use each, describes `RecurrentServerNeed` as the bridge. Opening sentences of the `Hardware/Edge` and `Usage/Edge` reference sub-bucket index pages deep-link here.
- Write the three How-to stubs: `database_modeling.md`, `machine_learning_workflow.md`, `server_to_server_interaction.md`. Each ends with a nominal "Try this interactively" deep-link to the matching interface template (a configured URL in mkdocs config — no library → interface import).
- Write the four FAQ stubs: `best_practices.md`, `build_process.md`, `measurement_tools.md`, `only_CO2.md`.
- Add `mkdocs build --strict` to library CI. Use a soft check on feature branches during content writing; hard on `main`.
- `Hardware/Edge` and `Usage/Edge` reference sub-buckets get hand-written `index.md` intro files (not injected by the auto-generator) that deep-link to `web_vs_edge.md`.

*Modeling templates (library-owned)*
- Create `efootprint/modeling_templates/` as a proper Python package (ships with the PyPI package).
- `how_to/` sub-package: `database_modeling.json`, `machine_learning_workflow.json`, `server_to_server_interaction.json` (serialized `System` JSONs produced via `system_to_json`), plus `registry.py` with typed metadata per template: `name`, `description`, `category`, `doc_path`.
- Public API: `from efootprint.modeling_templates import list_how_to_templates, get_template`.
- `tests/test_modeling_templates.py`: for each registered template, assert JSON exists, loads via `json_to_system`, computes emissions without error, metadata schema is valid, and `doc_path` points at an existing `docs_sources/` file.
- Run-as-script authoring helper: the test file (or a sibling script) can be run directly to regenerate a template JSON from a Python constructor, following the existing interface run-as-script pattern.

**Open questions before starting:**
- How-to page Python snippet strategy: hand-copy code first; upgrade to build-time rendering from JSON only if drift becomes a real problem.
- Reference sub-bucket intros: confirmed as hand-written `index.md` per sub-bucket.

**Draws from:** `04-efootprint-docs-overhaul.md`, `03-web-vs-edge-modeling.md` (library-side decisions), `05-maintainability-and-build.md` (library CI, Steps 3–4 checks).

---

## Step 5 — Web vs edge in the interface

**Goal:** Add the edge modeling toggle to the navbar and edge badges to object cards. Makes edge discoverable for users who need it without putting it in the way of web-only users.

**Deliverables — interface**
- **Navbar toggle** "Edge modeling: off / on":
  - Off (default): edge object types absent from add-menus.
  - On: edge types appear in add-menus alongside web types.
  - Latched on (disabled + tooltip) when the model contains at least one edge object. Tooltip draft: "Edge modeling is in use in this model. Remove all edge objects to turn it off."
  - Toggle tooltip (both states): one-liner defining edge + deep-link to `web_vs_edge.md`.
  - Toggle placement to be confirmed at implementation start (left, right, or settings cluster in navbar).
- **Edge badges** on object cards: small icon or coloured dot for edge objects. Visual only, no functional gating.
- `has_edge_objects` property on `ModelWeb` driving the latch (not a session flag or UI-only state).
- New unit tests: `has_edge_objects` returns `False` for a web-only model and `True` when any edge object is present. Latch driven by this property.

**Open questions before starting:**
- Badge visual design (icon, dot, stripe): minor; decide at implementation start.
- Latch tooltip wording: confirm the draft above or revise when writing the template.

**Draws from:** `03-web-vs-edge-modeling.md` (interface decisions), `02-interface-onboarding-ux.md` (disabled-instead-of-error principle applied to the latch), `05-maintainability-and-build.md` (edge toggle latch test).

---

## Step 6 — Introductory templates + guided tour

**Goal:** Deliver the full first-run onboarding experience: a template picker, pre-loaded working systems, and a guided tour that orients the user to the interface's structure and recommended modeling order.

This step has three sub-phases. Each sub-phase should be planned in its sub-implementation plan and reviewed before implementation begins; they are listed separately here because their prerequisites differ.

**Sub-phase A — Introductory template JSONs + registry**
- Serialized `System` JSONs for `ecommerce.json`, `ai_chatbot.json`, `iot_industrial.json` under `model_builder/domain/reference_data/modeling_templates/introductory/`.
- `registry.py` with per-template metadata: display name, short description, icon token, showcased concepts (class/concept tokens from the placeholder registry, not free-form strings), path to JSON.
- `other/` sub-folder and `registry.py` created as an empty but wired-up placeholder; templates added ad hoc as needed.
- Load-and-compute tests for each introductory template, following the pattern from Step 4.
- The IoT template ships with the edge toggle pre-enabled (the loaded system contains edge objects, so the Step 5 latch fires automatically). **Requires Step 5.**
- Open question: confirm the fate of `default_system_data.json` (becomes the blank baseline, migrates into introductory templates, or gets deleted) before writing JSONs.

**Sub-phase B — Template picker**
- First-run screen: replaces or overlays the blank model_builder on first visit. Shows introductory templates (from sub-phase A), library how-to templates (via `efootprint.modeling_templates.list_how_to_templates` — requires Step 4), and "Start from scratch".
- Help menu with replay entry points: "Replay tour" and "Open templates". Menu placement confirmed at implementation start.
- First-run state tracked in user profile (authenticated) and localStorage (fallback).

**Sub-phase C — Guided tour**
- Two flavors:
  - Template tour: overlaid on the pre-loaded system. Points at real cards and panels.
  - Blank tour: same orientation content, placeholder cards, suggests the first concrete action ("create a usage journey").
- Tour scope: interface orientation (columns, panels, results area), recommended modeling order (usage journey → infrastructure → usage patterns), contextual help discoverability (info icons, help drawer).
- Domain explanations are not in the tour — they live in contextual help and mkdocs deep-links.
- Tour step content lives in a small JSON or Python module on the interface side. Uses `{kind:target}` placeholder syntax from Topic 1.
- Tour auto-runs on first-ever visit only; replay entry point in the help menu from sub-phase B.

**Open questions before starting sub-phase A:**
- Fate of `default_system_data.json`.
- Help menu placement (to be confirmed at implementation start for sub-phase B).

**Draws from:** `02-interface-onboarding-ux.md`, `04-efootprint-docs-overhaul.md` (template storage scheme and registry), `05-maintainability-and-build.md` (template tests, Step 3 checks).

---

## Step 7 — Maintainability and build review

**Goal:** Gap-check. Graduate any CI checks still in warning mode to hard failures, confirm all checks from steps 1–6 are wired, and close any residual open questions from the topic files.

**Deliverables — both repos**
- Reference generator smoke test graduates to hard failure: zero `"description to be done"` strings in any generated reference page.
- `mkdocs build --strict` confirmed hard on `main` in library CI.
- Cross-reference consistency check: every how-to template's `doc_path` points at an existing mkdocs source file; every How-to page that claims a backing template references a registered one.
- Interface CI audit: confirm all checks from steps 1–6 are present and passing.
- Audit of open questions still flagged in topic files; each is either resolved or carried forward as an explicit tracked issue.
- Any remaining ban-word violations or missing `param_descriptions` treated as bugs, fixed here or tracked as follow-up issues.

**Draws from:** `05-maintainability-and-build.md` (phasing table, final phase checks).

---

## Relationship to topic files

| Topic file | Primary step(s) |
|---|---|
| `01-single-source-of-truth.md` | Steps 2 and 3 |
| `02-interface-onboarding-ux.md` | Steps 1 and 6 |
| `03-web-vs-edge-modeling.md` | Step 4 (library side) and Step 5 (interface side) |
| `04-efootprint-docs-overhaul.md` | Steps 4 and 6 |
| `05-maintainability-and-build.md` | All steps (each step's CI/test section), finalized in Step 7 |
