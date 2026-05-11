# Step 4 — Prose content track: co-authored mkdocs pages

This document covers the **prose authorship** half of Step 4. The companion `step-04-mechanical.md` covers package code, registry, tests, resolver, nav, and CI guidance. The two tracks ship independently; this one is co-authored with the user, page by page, in dedicated interactive sessions.

Self-contained: a fresh context should be able to pick this up cold and start co-redacting.

**Repo:** e-footprint (library only). All pages live under `docs_sources/mkdocs_sourcefiles/`.

**Source material to lift from:**
- `04-efootprint-docs-overhaul.md` — the topic file with the original decisions and bucket breakdown.
- `03-web-vs-edge-modeling.md` — canonical seed for `web_vs_edge.md` and edge sub-bucket intros.
- `e-footprint/specs/adjacent_tools.md` — input for `measurement_tools.md`.
- `e-footprint/specs/mission.md`, `e-footprint/specs/architecture.md` — useful framing for `why_efootprint`-style FAQ answers.
- Current mkdocs nav in `e-footprint/mkdocs.yml` for placement context.

---

## Working agreement

- **Co-authored.** Claude drafts, user redlines, repeat until the page reads right. Pages are not "tasks" with a binary done state; each lands when both agree it's good enough to ship.
- **One page per session** (recommended). Concentration > parallelism for prose.
- **Commit per page** (or per natural pair, e.g. the two edge sub-bucket intros together). `[ADD]` for new files, `[UPDATE]` for rewrites of existing stubs. Same `tutorial-and-documentation:` scope as prior commits in this feature.
- **Stop and ask** whenever a sentence would require a domain claim Claude can't verify. The user is the domain authority; Claude is the drafter.

---

## Style rules

Apply uniformly across all pages in this track.

- **Plain English.** Short sentences. Active voice. No marketing register.
- **No UI mechanics.** Don't write `click`, `button`, `drag`. These are library docs.
- **Python references allowed.** This is the library side — code references and `{class:Foo}` placeholders are fine. (The interface adapter strips/transforms them on its end.)
- **Placeholders, not raw markdown links** for cross-references between docs/classes/params/calculated attributes. Syntax: `{kind:target}`.
  - `{class:Server}` → reference to the `Server` class page in the generated reference.
  - `{param:Server.power}` → reference to a specific param of a class.
  - `{calc:Server.hourly_energy}` → reference to a calculated attribute.
  - `{doc:web_vs_edge}` → reference to another mkdocs page (registry in `docs_sources/doc_utils/doc_topic_registry.py`, owned by the mechanical track).
  - `{ui:...}` — **forbidden** in library strings. If a page wants to mention the interface, do so in prose, not via placeholders.
- **Markdown formatting is fine in mkdocs pages** (headings, code blocks, lists). The "no markdown" rule applies only to in-class description strings (`param_descriptions` values, class docstrings, etc.) — those are out of scope for this track and live in Step 2.
- **English only.** No translation considered.
- **Citations live in `{class:Source}` entries** on the data side, not inline. Don't add bibliography sections to prose pages unless a single specific reference is load-bearing.

---

## Write order (anchor first)

1. **`web_vs_edge.md`** — write first. It's the cross-link anchor for every edge-flavoured page in the rest of the track. Until it exists, other pages can't `{doc:web_vs_edge}` it cleanly.
2. **The three How-to pages** — `database_modeling.md`, `machine_learning_workflow.md`, `server_to_server_interaction.md`. Order among the three is arbitrary; pick by author energy.
3. **The four FAQ pages** — short, can be batched. Order arbitrary.
4. **The two sub-bucket index files** — `hardware_edge_index.md`, `usage_edge_index.md`. These point at `web_vs_edge.md` and at the classes in their sub-bucket, so they go last.

Each How-to page is **paired with its modeling template** (mechanical track sub-step 4.7). The Python code block in the prose mirrors the authoring script. The prose can be drafted first with a placeholder code block; finalize once the authoring script lands. Or vice versa. Don't block either side waiting for the other; merge them at commit time.

---

## Page 1 — `web_vs_edge.md` (Explanation, new)

**File:** `docs_sources/mkdocs_sourcefiles/web_vs_edge.md` (new).

**Seed:** `03-web-vs-edge-modeling.md`, "The mental model (canonical)" section. Lift the framing; rewrite for an external audience.

**Required content, in order:**

1. **One-paragraph framing.** "e-footprint has two paradigms for sizing environmental impact." Define web (demand-driven, infrastructure adapts to usage) and edge (deployment-driven, impact = units × per-unit behaviour) in plain English. No code yet.
2. **When to use which.** Bullet list:
   - Web for centralized services consumed by humans (SaaS, e-commerce, content streaming).
   - Edge for deployed hardware fleets (IoT, industrial PCs, smartphones from a manufacturer's perspective — any decentralized hardware whose impact scales with units shipped).
   - Mixed when a deployed fleet calls home to web infrastructure.
3. **Where they meet.** `{class:RecurrentServerNeed}` is the bridge: per-unit weekly recurrent pattern × deployed unit count → hourly demand on web jobs. One short description (no code block; the reference page carries the API).
4. **Anchors in the code** for skeptical readers:
   - `{calc:EdgeUsagePattern.hourly_edge_usage_journey_starts}` — hourly rate of device come-online events, not user clicks.
   - `{param:EdgeUsageJourney.usage_span}` — defaults to 6 years (fleet lifetime, not a session).
   - `{class:EdgeDeviceGroup}` — explicit fleet hierarchy (root groups, sub-groups, effective counts).
5. **Cross-links.** `{doc:methodology}` for the broader methodology framing. Optionally `{doc:database_modeling}` etc. if a sentence naturally calls for an example.

**Audience.** A technical reader landing here from the Explanation nav. Assume familiarity with the modeling concept of "sizing impact," but not with edge-vs-web as a distinction.

**Length target.** ~300–600 words. Long enough to ground the mental model; short enough to read in one sitting.

**Nav placement** (handled by mechanical track 4.1): under `Explanation:`, after `methodology.md`.

---

## Pages 2–4 — How-to guides

Each follows the same skeleton:

```
# How to model <X>

## Why this matters
1–2 paragraphs on the motivating use case.

## The model in plain language
Objects you'll create and how they connect. Use {class:Foo} placeholders.

## Python construction
Code block showing the System being built. Hand-copied from the authoring
script in efootprint/modeling_templates/how_to/_authoring/<slug>.py.

## Notable parameters and pitfalls
What's easy to get wrong. Cross-link to {class:Foo} pages for canonical
descriptions; this section's job is to highlight, not duplicate.

## Try this interactively
> Load this scenario in the e-footprint interface: [<template name>](<interface_base_url>/<slug>)
```

The "Try this interactively" line uses `{{ config.extra.interface_base_url }}` (mkdocs Jinja) — wired by mechanical track sub-step 4.8.

### Page 2 — `database_modeling.md`

**File:** rewrite of `docs_sources/mkdocs_sourcefiles/database_modeling.md` (currently a stub).

**Scenario:** a web service backed by a relational database.

**Model shape to describe:**
- A `{class:Server}` running the application.
- A `{class:Storage}` attached to it for the database files.
- `{class:Job}` instances representing read and write operations, with appropriate `data_transferred` and `data_stored` values.

**Why this matters seed:** databases are present in nearly every web product; modelers regularly ask how to split storage vs compute and how to handle the read/write asymmetry.

**Pitfalls to call out:**
- Confusing `data_transferred` (per-call payload) with `data_stored` (durable footprint).
- Forgetting that storage has both fabrication and idle/operational energy components.
- Read/write ratio: model it via job mix (different `{class:Job}` per operation type), not via a single average.

**Template pairing:** `efootprint/modeling_templates/how_to/database_modeling.json` (mechanical track 4.7).

### Page 3 — `machine_learning_workflow.md`

**File:** rewrite of `docs_sources/mkdocs_sourcefiles/machine_learning_workflow.md`.

**Scenario:** training + inference for an ML system.

**Model shape:**
- Training: a one-shot `{class:GPUJob}` on a `{class:GPUServer}`. High compute, infrequent.
- Inference: recurrent `{class:GPUJob}` instances driven by `{class:UsagePattern}`. Per-call compute, scales with usage.
- Optional contrast with `{class:EcoLogitsGenAIExternalAPI}` for hosted-API workloads (no infrastructure of your own).

**Why this matters seed:** ML footprint is a frequent ask and easy to get wrong (training dominates intuition; inference dominates the actual total at scale).

**Pitfalls to call out:**
- Modeling training as recurrent (it's typically a one-shot or rare event).
- Ignoring the carbon intensity of the training region versus the inference region.
- Skipping inference entirely on the assumption training is the whole story.

**Template pairing:** `efootprint/modeling_templates/how_to/machine_learning_workflow.json`.

### Page 4 — `server_to_server_interaction.md`

**File:** rewrite of `docs_sources/mkdocs_sourcefiles/server_to_server_interaction.md`.

**Scenario:** a service whose `{class:Job}` triggers a downstream `{class:Job}` on another service (microservices, API fan-out, async queue worker).

**Model shape:** the "shared job" pattern — the same `{class:Job}` object referenced from multiple upstreams, or a chain of jobs linked by usage patterns.

**Why this matters seed:** real systems aren't monoliths; jobs cascade. Many users don't realize e-footprint supports this directly and end up double-counting or under-counting.

**Pitfalls to call out:**
- Double-counting when the same downstream job is included in two upstream models.
- Underestimating fan-out when one upstream call triggers N downstream calls.
- Forgetting cross-region carbon intensity differences.

**Template pairing:** `efootprint/modeling_templates/how_to/server_to_server_interaction.json`.

---

## Pages 5–8 — FAQ

Short prose, ~150–400 words each. No modeling templates. No code blocks expected (unless a single short snippet is genuinely the answer).

### Page 5 — `best_practices.md`

**File:** rewrite of `docs_sources/mkdocs_sourcefiles/best_practices.md`.

**Question framing:** "What are the best practices for building a trustworthy e-footprint model?"

**Points to make:**
- Prefer measured `{class:Source}` entries over hypotheses; cite the source explicitly.
- Keep `default_values` only for ranges you actually trust; override at the param level when you have better data.
- Build incrementally: start with one usage pattern + one server, verify the numbers feel right, then add complexity.
- Sanity-check the dominant contributors via the Sankey / repartition view before drawing conclusions.

### Page 6 — `development_process.md`

**File:** new file at `docs_sources/mkdocs_sourcefiles/development_process.md` (replaces the stub `build_process.md`, which was misleadingly titled — it suggested e-footprint's own release process, but the intended content is about modeling **the user's** development process).

**Question framing:** "Should I model the development process of my service, and how?"

**Points to make:**
- Default: dev load is usually negligible vs. production — leave it out of the model.
- Triggers that flip the default: heavy ML experimentation, heavy coding-agent use, small production surface (internal tools, prototypes), expensive CI.
- For the small-production case, also flag the iterative-methodology corollary: a small order of magnitude means stop modeling, not chase precision.
- How to model it: no special "development" concept exists in e-footprint. A CI runner is a `{class:Server}`, a training sweep is a `{class:GPUJob}`, coding-agent usage is `{class:EcoLogitsGenAIExternalAPI}`. Add a `{class:UsageJourney}` for the dev workload and attach it like any other.
- Out of scope: office buildings, commuting, team travel — corporate carbon accounting territory.
- Cross-link `{doc:methodology}` for the start-coarse-refine-only-if-it-matters posture.

Status: drafted 2026-05-18 (co-authored, pending commit). Stub `build_process.md` deleted; `mkdocs.yml` FAQ nav entry updated. When the mechanical track's `{doc:}` registry lands, register the `development_process` key.

### Page 7 — `measurement_tools.md`

**File:** rewrite of `docs_sources/mkdocs_sourcefiles/measurement_tools.md`.

**Question framing:** "What's e-footprint's relationship to measurement tools like Boavizta, EcoLogits, etc.?"

**Points to make:**
- e-footprint is a **modeling** tool, not a measurement tool. It predicts impact from a structural description of a system.
- It consumes measurement data from upstream tools:
  - Boavizta — hardware fabrication and usage emission factors (`{class:BoaviztaCloudServer}` integration).
  - EcoLogits — generative AI inference impact (`{class:EcoLogitsGenAIExternalAPI}` integration).
- Pin to `e-footprint/specs/adjacent_tools.md` for the canonical list and positioning.

### Page 8 — `only_CO2.md`

**File:** rewrite of `docs_sources/mkdocs_sourcefiles/only_CO2.md`.

**Question framing:** "Why does e-footprint only report CO₂e?"

**Points to make:**
- Multi-impact (water, abiotic resource depletion, etc.) is a real and recognized need.
- Today the data quality and consistency across upstream sources is best for CO₂e; expanding to other impacts requires upstream coverage first.
- Pin to `{doc:methodology}` for the broader methodology discussion.
- Acknowledge it as a roadmap item if appropriate (check `roadmap.md` for current state).

---

## Pages 9–10 — Sub-bucket index files

Hand-written `index.md` files for the Hardware/Edge and Usage/Edge sub-buckets. Locked-in decision: not injected by the auto-generator. The generator stays per-class.

### Page 9 — `hardware_edge_index.md`

**File:** `docs_sources/mkdocs_sourcefiles/hardware_edge_index.md` (new).

**One short paragraph** describing edge hardware concepts in e-footprint:
- The objects in this sub-bucket model decentralized hardware fleets.
- Devices (`{class:EdgeDevice}`), components (`{class:EdgeRAMComponent}` etc.), and groups (`{class:EdgeDeviceGroup}`) compose into a fleet description.
- The fabrication and operational impact of the fleet is the model's primary output.

**Deep-link to `{doc:web_vs_edge}`** as the next read for context.

**Length target:** ~80–150 words. This is a landing page, not an article.

### Page 10 — `usage_edge_index.md`

**File:** `docs_sources/mkdocs_sourcefiles/usage_edge_index.md` (new).

Same shape, for edge usage:
- Patterns (`{class:EdgeUsagePattern}`), journeys (`{class:EdgeUsageJourney}`), and recurrent needs (`{class:RecurrentServerNeed}`, `{class:RecurrentEdgeDeviceNeed}`, etc.) describe what deployed devices do over their lifetime.
- The recurrent + deployment-count model contrasts with the demand-driven web `{class:UsagePattern}`.

**Deep-link to `{doc:web_vs_edge}`**.

---

## Done criteria (per page)

A page is done when:

1. The page covers the required content for its slot above.
2. All `{kind:target}` placeholders resolve (the mechanical track's `{doc:}` registry and Step 2's class/param/calc validation catch this; running `mkdocs build --strict` locally is the manual check).
3. No UI-mechanic vocabulary (`click`, `button`, `drag`).
4. The user has reviewed and accepted the prose.
5. For How-to pages: the Python code block matches the matching authoring script (the structure-equal round-trip test in mechanical track 4.9 enforces this for the template itself; the prose code block is hand-copied and consistency is reviewed by eye at commit time).

---

## Done criteria (track)

The prose track is done when:

- All ten pages are written, reviewed, and committed.
- `mkdocs build --strict` passes locally with the three new pages, the seven rewrites, and the two index files in place (assuming the mechanical track's `{doc:}` resolver has landed).
- The mechanical track's nav additions (`web_vs_edge.md`, the two sub-bucket index files) point at existing files.
- No `{doc:}` placeholders in any page point at a missing file.

---

## Not in this track

For absolute clarity, the following are **mechanical track** concerns even though they touch documentation:

- Stub deletions (`design_deep_dive.md`, `evolution_across_time.md`).
- `mkdocs.yml` nav edits.
- The `{doc:}` topic registry and resolver.
- The `extra.interface_base_url` config.
- The modeling template JSONs and their authoring scripts.
- Tests.
- `CONTRIBUTING.md` mkdocs-strict note.

See `step-04-mechanical.md` for those.
