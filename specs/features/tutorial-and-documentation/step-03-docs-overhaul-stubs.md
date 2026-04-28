# Step 3 — Docs overhaul (stubs + `web_vs_edge.md` + mkdocs CI)

Detailed implementation plan for making the e-footprint mkdocs site coherent and complete enough to ground a communication strategy. This is the docs-side counterpart to Step 2: Step 2 wrote the SSOT metadata that powers the auto-generated reference; this step makes the rest of the mkdocs site honest by deleting dead stubs, adding the canonical `web_vs_edge.md` Explanation page, populating placeholder stubs for the still-empty pages, and wiring `mkdocs build --strict` in CI.

**Repo:** e-footprint (library only).

**Draws from:** `04-efootprint-docs-overhaul.md` (stub triage, Explanation/How-to/FAQ structure), `03-web-vs-edge-modeling.md` (mental model owned by `web_vs_edge.md`), `05-maintainability-and-build.md` (mkdocs CI phasing).

**Scope boundary:** How-to and FAQ pages are placeholder stubs only in this step. Their full prose is written in Step 5 after the Step 4 communication strategy informs the angle. The library-side modeling templates (`efootprint/modeling_templates/`) are also Step 5.

---

## Deliverables overview

1. Delete `design_deep_dive.md` and `evolution_across_time.md`.
2. Write `web_vs_edge.md` (full Explanation page).
3. Hand-written `index.md` files for the `Hardware/Edge` and `Usage/Edge` reference sub-buckets, deep-linking to `web_vs_edge.md`.
4. Placeholder stub content for the three How-to pages and four FAQ pages.
5. Update `mkdocs.yml` nav: remove deleted entries, add `web_vs_edge.md`, add the two new sub-bucket index entries.
6. `.github/workflows/docs.yml` running the docs build pipeline + `mkdocs build --strict` on every push, hard failure from day one.

All deliverables live in the e-footprint repo. No interface changes.

---

## Sub-step 3.1 — Delete dead stubs and prune nav

### What to delete

- `docs_sources/mkdocs_sourcefiles/design_deep_dive.md` — empty, decision in `04-efootprint-docs-overhaul.md` is to drop the page entirely.
- `docs_sources/mkdocs_sourcefiles/evolution_across_time.md` — empty, same decision.

Both files are 0 lines today. No content is being lost.

### Nav changes

Remove from `mkdocs.yml`:

```yaml
- e-footprint design choices deep dive: design_deep_dive.md
- How to model the evolution of a system across time: evolution_across_time.md
```

After deletion, the `Explanation` section ends with `methodology.md` (until 3.2 adds `web_vs_edge.md`). The `How-to guides` section loses one entry and keeps the three remaining stubs.

---

## Sub-step 3.2 — Write `web_vs_edge.md`

The canonical mental-model page. Topic 3 (`03-web-vs-edge-modeling.md`) defines the content; this sub-step is the authorship.

### File location

`docs_sources/mkdocs_sourcefiles/web_vs_edge.md` (hand-written, copied verbatim into `generated_mkdocs_sourcefiles/` by the existing `main.py` build pipeline).

### Required sections

1. **Two paradigms.** Web (demand-driven) and Edge (deployment-driven). Causality in each direction (usage → infrastructure vs units × per-unit behaviour → impact).
2. **When to use each.** Web product teams default to web; industrial / IoT / fleet deployments default to edge; mixed systems are legitimate.
3. **The bridge: `RecurrentServerNeed`.** How a deployed edge fleet calls web infrastructure. Reference `recurrent_volume_per_edge_device` (168-hour weekly pattern) and `jobs: List[JobBase]`.
4. **Anchors in the code (for contributors).** Cite `EdgeUsagePattern.hourly_edge_usage_journey_starts`, `EdgeUsageJourney.usage_span` defaulting to 6 years, `EdgeDeviceGroup` fleet hierarchy, `RecurrentServerNeed.recurrent_volume_per_edge_device`. These anchors keep the explanation grounded in the codebase rather than vibes.

### Content guidelines

- Plain English first; cite class names where they ground the prose.
- Cross-link to the relevant reference pages with `{class:X}` placeholders so the SSOT placeholder resolver expands them at build time. Examples: `{class:RecurrentServerNeed}`, `{class:EdgeDeviceGroup}`, `{class:UsageJourney}`.
- No code snippets in this step; concrete code-level guidance lives in the How-to pages (Step 5).

### Nav entry

In `mkdocs.yml`, add under Explanation, after `methodology.md`:

```yaml
- Web vs edge modeling: web_vs_edge.md
```

---

## Sub-step 3.3 — Sub-bucket index pages

The `Hardware/Edge` and `Usage/Edge` sub-buckets in the reference nav are currently bare section headers with no intro page. Topic 4 calls for hand-written intros that deep-link to `web_vs_edge.md`.

### Files to create

- `docs_sources/mkdocs_sourcefiles/hardware_edge_index.md`
- `docs_sources/mkdocs_sourcefiles/usage_edge_index.md`

### Content shape (per file)

- Two-to-four sentences. Names what's in this sub-bucket and explains that all of these classes belong to the edge paradigm.
- Deep-links to `web_vs_edge.md` with markdown link syntax (the linked page is in the same generated docs tree, so a relative link works).
- No new mental-model content here; the page is a navigation aid, not a second copy of the explanation.

### Nav changes

Update the `Hardware → Edge` and `Usage → Edge` sections in `mkdocs.yml` so the index page is the first entry. Example for the Hardware/Edge section:

```yaml
- Edge:
    - About edge hardware: hardware_edge_index.md
    - Edge device:
        - Edge device (base object): EdgeDevice.md
        ...
```

And for Usage/Edge:

```yaml
- Edge:
    - About edge usage modeling: usage_edge_index.md
    - Edge usage pattern: EdgeUsagePattern.md
    ...
```

This avoids needing the mkdocs-material `navigation.indexes` theme feature; we just add the page as a leading nav entry.

---

## Sub-step 3.4 — Placeholder stubs for How-to and FAQ pages

The seven empty pages (three How-to, four FAQ) need content so `mkdocs build --strict` does not warn about empty files and so the Step 4 communication strategy can see the page scope at a glance.

### Files

How-to (in `docs_sources/mkdocs_sourcefiles/`):
- `database_modeling.md`
- `machine_learning_workflow.md`
- `server_to_server_interaction.md`

FAQ (in `docs_sources/mkdocs_sourcefiles/`):
- `best_practices.md`
- `build_process.md`
- `measurement_tools.md`
- `only_CO2.md`

### Stub shape

Each file is a small, self-contained placeholder with a fixed structure so a future grep can find them all and confirm none ship to production unfilled:

```markdown
# {{ Page title matching the nav entry }}

> **Status: placeholder.** This page will be written in Step 5 of the
> documentation roadmap, after the communication strategy clarifies the
> intended angle. See `specs/features/tutorial-and-documentation/99-implementation-plan.md`.

This page will cover:

- {{ bullet 1 — the question or scenario }}
- {{ bullet 2 }}
- {{ bullet 3 }}
```

### Suggested bullet content (per file)

- `database_modeling.md`: how to size a database server, repartition between read/write jobs, what storage class to model.
- `machine_learning_workflow.md`: training vs inference, GPU server vs external API, batch vs interactive.
- `server_to_server_interaction.md`: modeling job-to-job calls, when to keep them on one server vs split, repartition implications.
- `best_practices.md`: common modeling pitfalls, what to do when you do not have all the data, when to use defaults.
- `build_process.md`: how to scope a model, where to start (usage journey or infrastructure), iteration cadence.
- `measurement_tools.md`: what e-footprint measures vs other tools (Boavizta, Greenly, Climatiq, …), when to combine them.
- `only_CO2.md`: why the default scope is CO2-equivalent only, how other indicators (water, biodiversity, depletion) relate.

These are illustrative — actual bullets are a content choice during implementation, but each page must have at least three bullets so the comms strategy in Step 4 has something concrete to react to.

### Step 5 marker

Each placeholder includes the explicit `Status: placeholder.` line so:

- A grep `git grep -l "Status: placeholder."` returns the exact set of files Step 5 must rewrite.
- Anyone reading the rendered site immediately understands the page is a stub.

---

## Sub-step 3.5 — mkdocs CI workflow

Wire `mkdocs build --strict` on every push so dead links, missing files, and broken nav fail CI immediately.

### File location

`.github/workflows/docs.yml` (separate from the test workflow created in Step 1's `ci.yml` so the two can fail independently and reviewers can tell at a glance which one broke).

### Workflow shape

```yaml
name: docs

on:
  push:
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install Poetry
        run: pipx install poetry
      - name: Install dependencies
        run: poetry install --with dev
      - name: Regenerate generated_mkdocs_sourcefiles
        run: poetry run python docs_sources/doc_utils/main.py
      - name: Build mkdocs (strict)
        run: poetry run mkdocs build --strict
```

### Key points

- **Regenerate before build.** `docs_sources/doc_utils/main.py` wipes and regenerates `generated_mkdocs_sourcefiles/` (object reference + tutorial conversion + copy of hand-written sources). The CI run rebuilds from scratch — committed files in `generated_mkdocs_sourcefiles/` are not trusted by CI; the regeneration step is the source of truth in the workflow.
- **Hard from day one.** The reference generator output is fully populated as of Step 2 and the new content from sub-steps 3.1–3.4 means there are no known broken links or missing files. `--strict` should pass on the first run; if it does not, fix the underlying issue rather than relax the flag.
- **No separate "soft mode" first.** The phasing in `05-maintainability-and-build.md` originally suggested a soft warn-only pass during content writing. We can skip that here because Step 2 already populated the reference and Step 3's hand-written content is small and self-contained — there is no protracted authoring period to shield from CI.

### Smoke check before committing the workflow

Before adding the workflow file, run the same commands locally:

```bash
poetry run python docs_sources/doc_utils/main.py
poetry run mkdocs build --strict
```

If both pass, commit the workflow. If either fails, fix the root cause (missing nav entry, broken link, unresolved placeholder, etc.) before pushing.

---

## Implementation order

```
3.1 (delete dead stubs + nav prune) ─┐
                                     ├── all four content sub-steps independent
3.2 (web_vs_edge.md) ────────────────┤
3.3 (sub-bucket index pages) ────────┤
3.4 (placeholder stubs) ─────────────┘
                                     │
                                     ▼
                          3.5 (CI workflow, last so the smoke check is green)
```

Recommended sequence:

1. **3.1** — Delete dead stubs and prune nav. Smallest change; gives a clean baseline.
2. **3.4** — Placeholder stubs. Small mechanical edits across seven files; gets the empty-file warnings out of the way.
3. **3.2** — Write `web_vs_edge.md` and add to nav. Most authoring work in this step.
4. **3.3** — Sub-bucket index pages and nav update. Small, depends on 3.2 only for the deep-link target.
5. **3.5** — CI workflow. Run the build locally first; commit only when green.

A single commit (or a small handful of commits, one per sub-step) is fine — the unit of review is the whole step.

---

## Decisions and scoping

### What's in scope

- Library-side mkdocs content listed above plus mkdocs CI.

### What's deferred

- **How-to and FAQ full prose** — Step 5, after Step 4's communication strategy.
- **Library-owned modeling templates** (`efootprint/modeling_templates/`) — Step 5.
- **Cross-reference consistency check** between how-to templates and doc pages — Step 5 (no templates yet to cross-check).
- **Reference-generator changes** — done in Step 2.
- **Interface-side surfacing** of any of this content — Step 6.

### Resolved open questions

- **Sub-bucket intros: hand-written `index.md` per sub-bucket vs auto-generator injection** — locked as hand-written, per `04-efootprint-docs-overhaul.md` and consistent with the auto-generator staying per-class.
- **mkdocs CI phasing: warn-only vs strict** — locked as strict from day one; see Sub-step 3.5 rationale.
- **Placeholder stub format** — locked: each stub has a `Status: placeholder.` admonition + bullet list of intended content. Greppable, unambiguous to readers.

### Open questions (none blocking)

- The exact bullet content of each placeholder stub is a content call made during implementation. Defaults proposed in 3.4 are starting points, not commitments.
- Wording of the two sub-bucket index pages (3.3) is a content call made during implementation.

---

## Acceptance criteria

The step is done when:

1. `design_deep_dive.md` and `evolution_across_time.md` no longer exist in `docs_sources/mkdocs_sourcefiles/` and are not referenced in `mkdocs.yml`.
2. `web_vs_edge.md` exists in `docs_sources/mkdocs_sourcefiles/` with the four sections from 3.2 and is the last entry in the Explanation nav section.
3. `hardware_edge_index.md` and `usage_edge_index.md` exist and are the first entry under their respective Edge sub-buckets in `mkdocs.yml`.
4. The seven How-to / FAQ pages each contain a `Status: placeholder.` admonition and at least three bullets of intended content.
5. `poetry run python docs_sources/doc_utils/main.py && poetry run mkdocs build --strict` runs to completion with zero warnings locally.
6. `.github/workflows/docs.yml` exists, runs the same two commands, and passes on the first push.
