# specs/design/

Design strategy hub — the canonical, **visual** record of how the main usage journeys of e-footprint-interface work, and of the design decisions that become code. **[`index.html`](index.html) is the navigable entry point** to every artefact here; this README carries the strategy and rationale behind them.

**Visual artefacts are HTML.** Journeys (and, later, tokens and the component inventory) are authored as self-contained HTML files — rendered, navigable, *seeable* — the same posture this repo already uses for `spec.html` / `plan.html` review docs (see [`../workflow.md`](../workflow.md)). No build step, no framework, no CDN: open the file in a browser.

**What's live now:** [`journeys/build-a-model.html`](journeys/build-a-model.html) — the core editing loop — is authored and is the **reference implementation** (its `<style>` block is the shared toolkit every other journey copies). The remaining five journeys are scoped in [`index.html`](index.html) with a build order. **Tokens** and the **component inventory** are pre-staged and remain placeholders until that work starts.

> Engineer-first context: the maintainer is an engineer with no formal design background. This folder exists so design decisions land as durable repo artefacts that survive past any one conversation, rather than evaporating into chat history.

## Guiding principle

**Version artefacts that code depends on or risks drifting from. Link out to the rest.**

Hi-fi mockups, moodboards, design conversations, and exploratory sketches live in the tools that produce them (Figma, design chats, image files). What lands in this folder is the small, load-bearing subset that *engineering reads to know what to build* and *design reads to know what already exists*.

## What lives here

Three artefact types, in order of how often they change:

### 1. Journey docs — `journeys/<journey>.html`

One HTML doc per core user journey. Each captures:

- **Who & why** — which user (the non-technical product person is the primary audience; see [`../mission.md`](../mission.md)), what they're trying to do, what success looks like.
- **Screen sequence** — numbered steps, one desktop browser-window mock per step, real structure and real copy. Intent-level + UI-faithful, not pixel-perfect.
- **Key states** — empty, disabled-with-reason, loading, error, edge cases that change the screen materially. Each state sits next to the screen it changes.
- **Decisions taken** — the design calls made, with one-line rationale and the why-not-X notes, **each citing the real file**.

Journeys slot into the four-stage SDD workflow ([`../workflow.md`](../workflow.md)) between `spec.html` and `plan.html` for feature work. Spec says *what the product does*; journey says *how the user moves through it*; plan says *how code delivers it*.

**Authoring one:** follow [`journey-authoring.md`](journey-authoring.md) — the method (ground every screen in the real templates/views, not just the spec), the shared HTML/CSS template (copy [`journeys/build-a-model.html`](journeys/build-a-model.html)'s `<style>` block), and the conventions. The journey set — **all authored** (build-a-model is the reference; the rest were built against it):

- `journeys/build-a-model.html` — **the core loop, and the reference.** The three-column canvas → add an object via the side panel → edit → delete, with disabled-instead-of-error gating and in-place OOB canvas patches. Covers **both web and edge** (the Edge toggle adds object types, not a new loop) and the dedicated **Relationships** section unifying every connection shape (single link, list link, weighted dict, nested edge groups). Documented first because it exercises the most recurring UI regions; everything else reuses its components.
- `journeys/onboarding.html` — first run: home → *Start modeling* → the template picker (templates / start from scratch / load a file) → land on the canvas → the guided tour and help drawer. (The web/edge toggle lives in `build-a-model`, Phase E — it's part of the build loop, not first-run onboarding.)
- `journeys/view-results.html` — the Results panel: yearly & cumulative emission charts and the *Impact repartition* Sankey (+ "Analyse by" chips), the Sources tab and xlsx export. (Trusting the numbers is its companion, `audit-a-result`.)
- `journeys/audit-a-result.html` — **methodology & auditability.** Trace any number to its inputs: *provenance* (every value's source & confidence, the Sources view) and *derivation* (the inline formula → the calculus graph → cited inputs). Surfaces are reached from `view-results` (Sources) and `build-a-model` (the edit panel's *Calculated attributes*); this journey is their canonical home as auditability becomes first-class.
- `journeys/compare-models.html` — the second model slot and the comparison dashboard (KPI strip, decomposition, paired & cumulative charts, diff table), reached via the ⇄ Compare tab; non-destructive, dismiss in place.
- `journeys/save-and-load.html` — export / open a single model or the two-model workspace (`.e-f.json`, routed by content, UI config included), and the recovery page when a session model fails to deserialize.

### 2. Design tokens — `tokens.html` (+ implementation in `theme/static/scss/`)

Colors, type scale, spacing, radii. The values are the **single source of truth in code** — `theme/static/scss/custom.scss` defines `--new-primary #2D4675` (navy), the `--gray-50 … --gray-500` ramp, `--new-light-primary #e8eaf4`, the orthogonal `--edge-paradigm-accent #7B5DC7`, and the four-level confidence palette (`--conf-*`), layered on Bootstrap 5 (compiled to `bs_main.css`; never hand-edit the CSS — edit the SCSS).

**Live** — [`tokens.html`](tokens.html) *renders* those values (swatches, the gray ramp, fluid type specimens, breakpoints, radii) with the rationale. It mirrors the SCSS; refresh a swatch when a token changes there. The journeys also bake the same palette into each `<style>` block as local CSS vars.

### 3. Component inventory — the recurring UI primitives

A catalogue of the primitives that recur across journeys — the object cards, the dynamic form fields, the right-docked side panel, the modals, the disabled-with-tooltip add button — grouped Canvas · Chrome · Side panel & forms · Relationships · Overlays.

**Live** — [`components.html`](components.html). Since a static page can't render the real Django templates, each primitive is a **faithful mock** (reusing the shared toolkit) next to a **code pointer** to its template; the canonical markup stays the template, the canonical styling the toolkit in `build-a-model.html`. This is the single biggest lever against design drift; keep a mock in step when its template changes.

**Live counterpart — the `/design` route.** The interface also serves a live, intentionally-**unlinked** catalogue at `/design` (`e_footprint_interface/views.py::design_catalogue` → `theme/templates/design/catalogue.html`), reachable only by direct navigation and communicated to contributors out of band. It renders the **real tokens** (the app's compiled CSS custom properties) and the **real component partials** with sample context, so it can't drift from what ships — the truthful complement to the static, version-controlled mocks here. Context-heavy primitives (cards, forms, the canvas) link to the live model builder rather than being mocked. Promote a primitive to a sample-data card in the catalogue when it earns its keep.

## What we deliberately do not version here

- **Hi-fi mockups.** Link to Figma or attach images in PR descriptions; never embed them in repo markdown — they rot the moment design iterates.
- **Screenshots in docs.** Same reason. A live render (the component inventory) tells the truth; a screenshot lies the first time the code changes.
- **Exhaustive motion / micro-interaction specs.** Skip unless the motion is load-bearing. Most lives in CSS/HTMX and is fine to evolve in code.
- **Design conversation transcripts.** Conversations produce decisions; record the decisions in the journey doc, drop the transcript.

## Sync protocol with design work

The handoff fails when design output is mood-board-shaped and engineering has to re-translate every time. Push design output to map cleanly onto the three artefact types above:

| Design output | Lands as |
|---|---|
| Token change | Diff against current values in `tokens.html` + the SCSS implementation. |
| New journey or journey revision | Screen-by-screen + state list → `journeys/<name>.html`. |
| New or revised component | Variants × states matrix + prose → the component inventory, rendered from the real template. |

Anything that doesn't fit one of those buckets is exploration — keep it in the design tool, don't drag it into the repo.

## Workflow for growing the set

1. Author journeys in the build order in [`index.html`](index.html), starting from `build-a-model` (done — it constrains everything else).
2. Each new journey copies `build-a-model.html`'s `<style>` block, reuses its class vocabulary, and only adds a class for a genuinely new UI element.
3. Stand up `tokens.html` the first time a token group changes on purpose; audit the touched surfaces against it.
4. Grow the component inventory from what the authored journeys actually use, not speculatively.

**Trap to avoid.** Don't build a 40-component design system before there are polished screens. The journey set + a couple of token decisions is enough to start; the component inventory grows from what the journeys need.

## Doc-sync expectation

When design work introduces or materially changes a journey, a token group, or a cross-cutting component pattern, update the corresponding artefact in this folder in the **same PR**. This follows the standard doc-sync rule in [`../../AGENTS.md`](../../AGENTS.md): new conventions and changed invariants trigger doc updates; one-off tweaks don't.
