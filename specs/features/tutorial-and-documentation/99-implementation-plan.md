# Implementation Plan — Tutorial & Documentation

High-level, iterative plan for the tutorial and documentation overhaul. Each step is small enough to be reviewed independently and builds on the one before. The step ordering maximises early UX wins while ensuring each successive step has its prerequisites in place.

Each step gets a dedicated sub-implementation plan file (linked below) written and reviewed before implementation begins. This file stays intentionally high-level; the topic files (`01`–`05`) hold the design decisions and rationale.

---

## Step overview

| # | Title | Repos touched | Sub-plan |
|---|---|---|---|
| 1 | Disabled-instead-of-error UX | interface + lib CI | `step-01-disabled-ux.md` |
| 2 | SSOT metadata in e-footprint | library | `step-02-ssot-library.md` |
| 3 | Docs overhaul (stubs + `web_vs_edge.md` + mkdocs CI) | library | `step-03-docs-overhaul-stubs.md` |
| 4 | Communication strategy (articles, LinkedIn) | content (no code) | `step-04-communication-strategy.md` |
| 5 | Refined how-to/FAQ content + library modeling templates | library | `step-05-docs-refine-and-templates.md` |
| 6 | Surface SSOT in the interface | interface | `step-06-ssot-interface.md` |
| 7 | Web vs edge in the interface | interface | `step-07-edge-interface.md` |
| 8 | Introductory templates + guided tour | interface | `step-08-templates-tour.md` |
| 9 | Maintainability and build review | both | `step-09-build-review.md` |

**Reorder rationale (2026-04-27):** Step 3 was originally "Surface SSOT in the interface" and Step 4 was a single "Docs overhaul + modeling templates" step. The library-side docs work moved earlier so the canonical `web_vs_edge.md` Explanation page and the upgraded auto-generated reference exist before any communication strategy work. The single old Step 4 split into three: (3) stubs + `web_vs_edge.md` + mkdocs CI, (4) communication strategy, (5) refined how-to/FAQ prose + library modeling templates. Refinement is paired with template authoring because the how-to templates are the runnable backbone of the How-to pages — fleshing out the prose and authoring the JSON-serialized scenarios go hand in hand.

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

**Goal:** Add the structured description metadata defined in Topic 1 to every concrete e-footprint class, and write the tests that enforce completeness. This is the authorship step that all downstream steps (3 onward) depend on.

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

## Step 3 — Docs overhaul (stubs + `web_vs_edge.md` + mkdocs CI)

**Goal:** Make the e-footprint mkdocs site coherent and complete enough to ground a communication strategy. Deliver the canonical Explanation page (`web_vs_edge.md`), wire the auto-generated reference end-to-end, fix the empty-stub problem, and enforce build correctness in CI. How-to and FAQ pages get **placeholder stubs only** (one paragraph each describing what the page will eventually cover) — they are refined in Step 5 after the communication strategy informs the angle.

**Deliverables — library**
- Delete `design_deep_dive.md` and `evolution_across_time.md`. Update `mkdocs.yml` nav accordingly.
- Write `web_vs_edge.md` (Explanation, full content): defines the two paradigms, when to use each, describes `RecurrentServerNeed` as the bridge. Lands in the Explanation section.
- Hand-written `index.md` files for the `Hardware/Edge` and `Usage/Edge` reference sub-buckets, deep-linking to `web_vs_edge.md`. Adjust `mkdocs.yml` so each sub-bucket has its index entry.
- Placeholder stub content for the three How-to pages (`database_modeling.md`, `machine_learning_workflow.md`, `server_to_server_interaction.md`) and the four FAQ pages (`best_practices.md`, `build_process.md`, `measurement_tools.md`, `only_CO2.md`). One paragraph each, marked clearly as placeholder. Goal: mkdocs renders without warnings and the comms strategy can see what's in scope.
- `.github/workflows/docs.yml` running `mkdocs build --strict` on every push. Hard failure from day one — Step 2's reference generator output is already fully populated.

**Open questions before starting:** None — placeholder stub wording and `index.md` exact prose are content choices made in implementation.

**Draws from:** `04-efootprint-docs-overhaul.md`, `03-web-vs-edge-modeling.md` (library-side decisions), `05-maintainability-and-build.md` (mkdocs CI).

---

## Step 4 — Communication strategy (articles, LinkedIn)

**Goal:** Use the now-coherent library docs (auto-generated reference from Step 2 + `web_vs_edge.md` from Step 3) as raw material for an external communication plan: which audiences, which articles, which LinkedIn posts, which messages. The output of this step informs how the How-to and FAQ pages are written in Step 5.

**Deliverables — content (no code changes to either repo)**
- Audience map: who the e-footprint comms is targeting (web product teams, industrial users, sustainability researchers, …) and where each audience hangs out.
- Article backlog: list of article titles + one-paragraph abstracts, each annotated with which mkdocs page(s) it would be paired with as deep-link.
- LinkedIn post backlog: shorter-form posts mapped to the same mkdocs deep-link targets.
- Cross-reference matrix: which mkdocs pages are anchors for which comms artefacts. This drives the angle for Step 5's How-to and FAQ refinement.

**Open questions before starting:** None at the planning level — the work is the content authorship itself.

**Draws from:** `04-efootprint-docs-overhaul.md` (mkdocs structure), Step 2 deliverables (auto-generated reference content), Step 3 deliverables (`web_vs_edge.md`).

---

## Step 5 — Refined how-to/FAQ content + library modeling templates

**Goal:** Replace the placeholder stubs from Step 3 with real How-to and FAQ prose, informed by Step 4's communication strategy. Author the library-owned how-to modeling templates that back the How-to pages, with their registry and CI checks.

**Deliverables — library**

*mkdocs content (refined)*
- Replace placeholder stubs in the three How-to pages with full content. Each page ends with a nominal "Try this interactively" deep-link to the matching interface template (configured URL in mkdocs config — no library → interface import).
- Replace placeholder stubs in the four FAQ pages with full content, written with the comms strategy's angle in mind.
- `mkdocs build --strict` already hard from Step 3; remains green.

*Modeling templates (library-owned)*
- Create `efootprint/modeling_templates/` as a proper Python package (ships with the PyPI package).
- `how_to/` sub-package: `database_modeling.json`, `machine_learning_workflow.json`, `server_to_server_interaction.json` (serialized `System` JSONs produced via `system_to_json`), plus `registry.py` with typed metadata per template: `name`, `description`, `category`, `doc_path`.
- Public API: `from efootprint.modeling_templates import list_how_to_templates, get_template`.
- `tests/test_modeling_templates.py`: for each registered template, assert JSON exists, loads via `json_to_system`, computes emissions without error, metadata schema is valid, and `doc_path` points at an existing `docs_sources/` file.
- Run-as-script authoring helper: the test file (or a sibling script) can be run directly to regenerate a template JSON from a Python constructor, following the existing interface run-as-script pattern.

**Open questions before starting:**
- How-to page Python snippet strategy: hand-copy code first; upgrade to build-time rendering from JSON only if drift becomes a real problem.

**Draws from:** `04-efootprint-docs-overhaul.md`, `05-maintainability-and-build.md` (library CI, modeling template checks), Step 4 (comms strategy informs prose angle).

---

## Step 6 — Surface SSOT in the interface

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

## Step 7 — Web vs edge in the interface

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

## Step 8 — Introductory templates + guided tour

**Goal:** Deliver the full first-run onboarding experience: a template picker, pre-loaded working systems, and a guided tour that orients the user to the interface's structure and recommended modeling order.

This step has three sub-phases. Each sub-phase should be planned in its sub-implementation plan and reviewed before implementation begins; they are listed separately here because their prerequisites differ.

**Sub-phase A — Introductory template JSONs + registry**
- Serialized `System` JSONs for `ecommerce.json`, `ai_chatbot.json`, `iot_industrial.json` under `model_builder/domain/reference_data/modeling_templates/introductory/`.
- `registry.py` with per-template metadata: display name, short description, icon token, showcased concepts (class/concept tokens from the placeholder registry, not free-form strings), path to JSON.
- `other/` sub-folder and `registry.py` created as an empty but wired-up placeholder; templates added ad hoc as needed.
- Load-and-compute tests for each introductory template, following the pattern from Step 5.
- The IoT template ships with the edge toggle pre-enabled (the loaded system contains edge objects, so the Step 7 latch fires automatically). **Requires Step 7.**
- Open question: confirm the fate of `default_system_data.json` (becomes the blank baseline, migrates into introductory templates, or gets deleted) before writing JSONs.

**Sub-phase B — Template picker**
- First-run screen: replaces or overlays the blank model_builder on first visit. Shows introductory templates (from sub-phase A), library how-to templates (via `efootprint.modeling_templates.list_how_to_templates` — requires Step 5), and "Start from scratch".
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

## Step 9 — Maintainability and build review

**Goal:** Gap-check. Graduate any CI checks still in warning mode to hard failures, confirm all checks from steps 1–8 are wired, and close any residual open questions from the topic files.

**Deliverables — both repos**
- Reference generator smoke test graduates to hard failure: zero `"description to be done"` strings in any generated reference page.
- `mkdocs build --strict` confirmed hard on `main` in library CI.
- Cross-reference consistency check: every how-to template's `doc_path` points at an existing mkdocs source file; every How-to page that claims a backing template references a registered one.
- Interface CI audit: confirm all checks from steps 1–8 are present and passing.
- Audit of open questions still flagged in topic files; each is either resolved or carried forward as an explicit tracked issue.
- Any remaining ban-word violations or missing `param_descriptions` treated as bugs, fixed here or tracked as follow-up issues.

**Draws from:** `05-maintainability-and-build.md` (phasing table, final phase checks).

---

## Relationship to topic files

| Topic file | Primary step(s) |
|---|---|
| `01-single-source-of-truth.md` | Steps 2 and 6 |
| `02-interface-onboarding-ux.md` | Steps 1 and 8 |
| `03-web-vs-edge-modeling.md` | Step 3 (library side, `web_vs_edge.md`) and Step 7 (interface side) |
| `04-efootprint-docs-overhaul.md` | Steps 3 (stubs + reference + CI), 5 (refined prose + modeling templates), and 8 (interface-side template picker) |
| `05-maintainability-and-build.md` | All steps (each step's CI/test section), finalized in Step 9 |
