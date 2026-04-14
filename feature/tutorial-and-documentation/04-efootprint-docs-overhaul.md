# Topic 4 — e-footprint docs overhaul

What to do about the mkdocs site: the empty stubs, the auto-generated
reference, the How-to guides, and how example systems stay honest
across library and interface. Self-contained so the exploration can
resume cold from this file alone.

---

## Scaffold

**Keep Diátaxis.** The current mkdocs nav is already roughly
Diátaxis-shaped (Tutorial / Explanation / How-to / Reference / FAQ)
and the mapping is good.

Alternatives considered and rejected:

- **Task-oriented only** (everything is a How-to, reference hidden):
  works for hands-on APIs but e-footprint has too much conceptual
  depth (methodology, web vs edge, repartition semantics) for
  explanations to hide.
- **Audience-split subsites** ("for product teams" / "for industrial
  modelers" / "for contributors"): tempting given the web-vs-edge
  audience split from Topic 3, but duplicates prose, rots fast, and
  fights the Topic 1 SSOT principle.
- **Docs-as-code / literate programming**: e-footprint already does
  this for the reference layer, and Topic 1 extends it. Pushing
  Explanation/How-to into code annotations too is overkill.

Diátaxis is the right fit.

---

## Stub triage

### Delete

- `design_deep_dive.md`
- `evolution_across_time.md`

### Keep and write (How-to)

Each backed by a matching **How-to modeling template** on the library
side (see below).

- `database_modeling.md`
- `machine_learning_workflow.md`
- `server_to_server_interaction.md`

### Keep and write (FAQ)

Short prose, no modeling template needed.

- `best_practices.md`
- `build_process.md`
- `measurement_tools.md`
- `only_CO2.md`

### Already has real content (no action)

`why_efootprint.md`, `methodology.md`, `get_started.md`,
`explanation_overview.md`, `index.md`, `object_reference.md`,
`tutorial.md`.

### New content to add

- **`web_vs_edge.md`** (Explanation) — canonical mental model page,
  owned by Topic 3. Referenced from the Hardware/Edge and Usage/Edge
  reference sub-bucket intros.

---

## Reference section

- **Strictly auto-generated.** No hand-written tails, no per-class
  prose injected into reference pages. All longer-form prose lives
  in the Explanation section and is cross-linked from there.
- **Augmented with Topic 1 SSOT metadata.** The reference generator
  (`docs_sources/doc_utils/generate_object_reference.py`) is
  upgraded to read the new class attributes defined in Topic 1
  (`param_descriptions`, `disambiguation`, `interactions`,
  `pitfalls`) plus `update_<attr>` method docstrings, and render
  them into the `obj_template.md` output. The placeholder syntax
  (`{kind:target}`) is resolved during generation, with `doc` and
  `ui` placeholders forbidden in library-side strings (also per
  Topic 1).
- This replaces today's `"description to be done"` and
  `"{label} in {units}"` fallbacks with real content pulled from
  the class files.

---

## Modeling templates: the runnable scenarios

Each concrete modeling scenario used anywhere in the docs or the
interface is a **modeling template** — a serialized `System` JSON
accompanied by typed metadata. Templates are the single source of
truth for "here is a real, working example model of X."

### Three categories

- **`introductory`** — the onboarding starter templates (e-commerce,
  AI chatbot, IoT). Purpose: something mutable to poke at on first
  run. Tightly coupled to guided-tour logic. **Owned by the
  interface.**
- **`how_to`** — each tied to exactly one How-to doc page. Purpose:
  a deep dive on a specific modeling question. Not necessarily a
  good starting point. **Owned by the library**, because the How-to
  narrative lives in mkdocs on the library side and the template is
  its runnable backbone.
- **`other`** — useful examples that aren't good first-run
  templates and aren't narrative deep-dives. Honest catch-all.
  **Owned by the interface** (grab-bag authored where it's
  discovered and used).

Scenarios can belong to a **primary category + optional extra tags**.
A good scenario can pull double duty — e.g. a how-to template tagged
`showcases:edge` — but it has exactly one category that determines
its home.

### Storage shape

Each template has two things:

1. **A serialized `System` JSON** produced by
   `efootprint.api_utils.system_to_json`. Pure system snapshot, no
   UI-only metadata inside.
2. **Metadata in a Python registry** alongside: display name, short
   description, category, optional extra tags, path to the JSON file,
   and — for how-to templates — the mkdocs doc path the template
   backs. Keeps JSON clean and gives consumers a typed import point.

### Physical layout

Library side (ships with the `efootprint` PyPI package):

```
efootprint/modeling_templates/
├── __init__.py            # public API: list_how_to_templates(), get(...)
├── how_to/
│   ├── database_modeling.json
│   ├── machine_learning_workflow.json
│   ├── server_to_server_interaction.json
│   └── registry.py        # metadata for the above
```

Interface side:

```
model_builder/domain/reference_data/modeling_templates/
├── introductory/
│   ├── ecommerce.json
│   ├── ai_chatbot.json
│   ├── iot_industrial.json
│   └── registry.py
└── other/
    ├── ...
    └── registry.py
```

`default_system_data.json` (today) either migrates into
`introductory/` as one of the starter templates or stays as the blank
baseline — to confirm during implementation.

### Discovery across the two repos

- The library exposes a public API, e.g.
  `from efootprint.modeling_templates import list_how_to_templates`,
  that returns the registered how-to templates with their metadata
  and loadable JSON paths.
- The interface's template browser imports this list at runtime and
  merges it with its own introductory + other registries. This is a
  normal runtime use of the library dependency — no build step, no
  file copying, no parity test. `pip install efootprint` ships the
  how-to templates alongside the library code.
- Directionality is preserved: the library knows nothing about the
  interface; the interface consumes a stable public API of the
  library.

### CI checks

- Every registered template (library side and interface side) loads
  via `json_to_system`, instantiates without error, and produces
  computed emissions through the standard pipeline. A broken
  template fails CI immediately.
- Every how-to template's `doc_path` points at an existing mkdocs
  source file, and every How-to page that claims a backing template
  references a registered one. Cross-check runs in CI.
- Metadata schema is validated: required fields present, category
  is one of the three values, tags are strings.

---

## How-to pages: authoring and maintenance

- **Hand-written prose.** Narrative stays human. The scenario keeps
  the code examples honest via the CI load-and-compute check above,
  not via prose auto-generation.
- **Code blocks reference the template.** A How-to page that shows
  "how to build this model in Python" can either hand-copy the code
  or load the JSON at mkdocs build time and render the resulting
  Python via a small codegen helper. Start with hand-copy; upgrade
  to build-time rendering only if drift becomes a real problem.
- **Nominal pointer to the interface.** Each how-to page ends with a
  small "Try this interactively" note that deep-links to the
  matching modeling template in the interface. The link is a
  configured URL in mkdocs config; it is a nominal mention, not an
  import, so directionality is unaffected.
- **Cross-cutting How-to sync.** The CI load-and-compute check is
  how we keep How-to guides from drifting as the library evolves. If
  a class rename or API change breaks a how-to template, the CI
  failure points at the exact template, and updating the serialized
  JSON (via a one-shot script that re-runs a Python scenario
  constructor through `system_to_json`) fixes both the template and
  the page that references it.

---

## Explanation section

Sections in order, after the overhaul:

1. `explanation_overview.md` (exists) — short index.
2. `efootprint_scope.md` (exists).
3. `why_efootprint.md` (exists).
4. `get_started.md` (exists).
5. `methodology.md` (exists).
6. **`web_vs_edge.md` (new, from Topic 3)**.

`design_deep_dive.md` is deleted. Further Explanation pages are added
only when a specific reader question justifies them.

---

## FAQ section

Kept as-is in shape. Short prose answers to recurring questions. Each
file gets real content; nothing fancy.

- `best_practices.md`
- `build_process.md`
- `measurement_tools.md`
- `only_CO2.md`

---

## Decisions locked in

- Keep Diátaxis.
- Delete `design_deep_dive.md` and `evolution_across_time.md`.
- Write the three How-to stubs and the four FAQ stubs listed above.
- Add `web_vs_edge.md` to Explanation (from Topic 3).
- Reference stays strictly auto-generated, augmented with Topic 1
  SSOT metadata; `generate_object_reference.py` is upgraded to read
  `param_descriptions`, `disambiguation`, `interactions`, `pitfalls`,
  and `update_<attr>` docstrings, and to resolve `{kind:target}`
  placeholders.
- Modeling templates as the SSOT for runnable example scenarios,
  in three categories:
  - `how_to` owned by the library, shipped with the package.
  - `introductory` owned by the interface, tour-coupled.
  - `other` owned by the interface, grab-bag.
- Each template: serialized `System` JSON + Python registry
  metadata.
- Library exposes `efootprint.modeling_templates` as a public API;
  interface imports at runtime. No file copying, no parity test.
- How-to prose is hand-written; CI checks that every template
  loads, computes, and that cross-references between templates and
  doc pages are consistent.
- How-to pages end with a nominal deep-link to the matching
  interface template. No library → interface dependency.

---

## Open questions

- **Codegen for Python snippets in How-to pages.** Hand-copy first;
  decide later whether to upgrade to build-time rendering from JSON.
- **Migration of `default_system_data.json`.** Does it become one of
  the introductory templates, stay as a blank baseline, or get
  deleted? Answer during implementation.
- **Scenario authoring ergonomics.** Authoring a new modeling
  template means either (a) writing a Python constructor and
  running `system_to_json`, or (b) editing the interface to the
  desired state and exporting. Both should work; the interface
  route is probably friendlier. Document whichever we recommend.
- **Tag vocabulary for extra tags.** Free-form or a closed enum
  (e.g. `showcases:edge`, `audience:industrial`)? Lean closed enum
  validated in CI, but defer until tags are actually used.
- **Reference sub-bucket intros.** The Hardware/Edge and Usage/Edge
  reference sub-buckets should have a short hand-written intro that
  deep-links to `web_vs_edge.md`. Are those intros hand-written
  `index.md` files per sub-bucket, or injected into the auto-
  generator? Lean hand-written sub-bucket index files; the auto-
  generator stays per-class.
- **How-to for web vs edge overall.** `web_vs_edge.md` is
  Explanation. Does it also need a dedicated How-to ("How to decide
  whether your project needs edge modeling") or is the Explanation
  page enough on its own? Probably enough.

---

## How this topic connects to the others

- **Topic 1 (SSOT).** The auto-generated reference consumes the
  class-level description metadata defined in Topic 1. Topic 1's
  `DescriptionProvider` port is the library-side half of the SSOT;
  this topic is the mkdocs-side half.
- **Topic 2 (interface onboarding).** Introductory modeling
  templates are interface-owned and coupled to guided-tour logic.
  Topic 2's template picker also surfaces the library-side how-to
  templates via the merged registry. The `template_*.json` +
  `templates_manifest.json` names from Topic 2 are superseded by
  this topic's `modeling_templates/introductory/` +
  `registry.py` scheme; Topic 2 is updated for consistency.
- **Topic 3 (web vs edge).** `web_vs_edge.md` is delivered here and
  cross-linked from the reference sub-bucket intros. The IoT
  introductory template showcased in Topic 2 and Topic 3 is the
  interface-owned representative of edge modeling for first-run
  users.
- **Topic 5 (maintainability and build).** The CI checks listed
  above (template load/compute, cross-reference consistency,
  metadata schema, reference-generator extensions, placeholder
  resolution) all live in Topic 5's build pipeline.
