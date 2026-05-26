# EcoLogits video-generation integration

**Status:** Spec — under review.
**Date:** 2026-05-22.

## 1. Problem and audience

Generative-AI **video** services (Sora, Veo, Kling, Seedance, Runway, …) are
the fastest-growing class of high-impact AI workloads e-footprint users want
to size. e-footprint already integrates EcoLogits for **LLM** inference but
has no equivalent surface for video generation. EcoLogits has just shipped
`impacts_video_generation`, a per-call impact estimator covering ~11 catalogued
video models.

- **Who:** sustainability-aware product teams sizing AI-assisted video
  pipelines, plus the Vivatech 2026 demo on `dev.e-footprint.boavizta.org`.
- **Frequency / severity:** acute now — without this, users have to hand-roll
  video impacts or omit them entirely, which biases totals downward by a large
  factor for any system that includes video generation.
- **Why now:** EcoLogits' methodology has just been finalized (private branch
  `samuelrince/ecologits-private @ feat/video-generation`); the partnership
  window with Samuel Rincé closes after Vivatech 2026, after which the
  methodology releases publicly and the integration becomes a normal upstream
  bump (see `PRIVATE_INTEGRATION.md`).

## 2. Success criteria

Each criterion is independently testable.

1. A user can declaratively describe a generative-AI video service in
   e-footprint — pick a provider and model from the EcoLogits video catalog,
   size individual calls by **resolution**, **duration**, and **with/without
   audio**. The datacenter assumptions (location, PUE, WUE) are inferred from
   the EcoLogits per-provider config, not user inputs.
2. Every per-call quantity surfaced (energy, embodied GWP, usage GWP,
   generation latency) carries the same explainability tree contract as the
   existing EcoLogits LLM integration: traceable formula, source URL, ancestor
   inputs.
3. The resulting model server exposes hourly fabrication footprint, energy,
   and energy-use footprint identical in shape to what the existing LLM API
   produces — so the new classes feed system-wide aggregation, results
   charts, and JSON persistence without special casing.
4. The UI in `e-footprint-interface` lets users add a video-generation API
   and jobs through the standard model-builder flow, only surfaces valid
   provider/model/resolution combinations, saves a model that round-trips
   through the JSON serialization layer, and shows the resulting carbon
   footprint in the existing results charts.
5. A regression test guards against EcoLogits' internal frame-count formula
   drifting away from our integration's assumption.
6. Standard library quality gates are met: full pytest suite passes against
   the privately pinned `ecologits`; JSON round-trip preserved; new
   `ModelingObject` classes registered; `CHANGELOG.md` entry added; mkdocs
   reference picks up the new classes.

## 3. Scope

### In scope

- A new declarative surface for AI **video** generation, mirroring the
  capability shape already provided by the EcoLogits LLM integration
  (`EcoLogitsGenAIExternalAPI` family): a virtual server that aggregates
  Server-level hourly footprints, an API object that picks the model and
  carries datacenter assumptions, and a Job object sized by the per-call
  inputs (resolution, duration, audio).
- **Carbon impact only**, consistent with current e-footprint scope: per-call
  GWP (usage + embodied) and energy. Generation latency is exposed because it
  drives the job's request duration. EcoLogits' broader output dictionary
  (ADPe, primary energy, water) is computed and cached but not surfaced as
  e-footprint attributes.
- **Interface (`e-footprint-interface`) work** to make the new classes
  reachable from the model-builder UI, with provider → model and model →
  resolution dropdowns that only allow valid combinations, and JSON
  persistence round-tripping through the standard save/load flow.
- Tests at the appropriate layers (library unit + integration; interface
  unit + integration + one E2E flow).
- Documentation: class-level docstrings and `param_descriptions` so the
  mkdocs reference and the interface help drawer pick up the new classes
  automatically; `CHANGELOG.md` entry.

### Out of scope (this iteration)

- **Non-GWP environmental impact categories** (ADPe, primary energy, water).
  Mission-aligned: these are tracked for future Boavizta API integration.
- **Image generation, audio-only generation, multimodal text-to-text** —
  EcoLogits has separate or yet-to-land estimators; this iteration is
  video-only.
- **Video-specific UI redesigns** — no dedicated video-pipeline builder,
  no custom result charts segmenting by model/resolution, no preview of the
  generated video. The interface work is the minimum to surface the new
  classes via the existing model-builder conventions.

## 4. UX (conceptual)

A user declares an external video-generation API once (provider, model,
optional DC assumptions) and attaches one or more jobs to it, each sized by
the per-call parameters that drive impact. From there, jobs participate in
the existing usage-pattern / hourly-aggregation machinery, and the
underlying virtual server contributes to the standard system footprint
just like any other infrastructure element. In the interface, this surfaces
as a new entry in the External API catalog and a standard model-builder
form.

## 5. Constraints

- **Mission alignment:** carbon-only, consistent with e-footprint's current
  scope. Non-GWP impact categories are deferred (see §3 out of scope).
- **Constitution:** new code lives in `builders/`, respects three-layer
  separation, no backwards-compatibility shims, mkdocs builds clean, JSON
  round-trip preserved, classes registered in `all_classes_in_order.py`,
  `CHANGELOG.md` updated. Doc-as-code SSOT applies: descriptions live in
  class docstrings and `param_descriptions`, nowhere else.
- **Private-dependency window.** Library-side work happens on the
  `ecologits-video` branch of `e-footprint`, with `ecologits` pinned to a
  commit on `samuelrince/ecologits-private`. See `PRIVATE_INTEGRATION.md`
  for the branch / remote / deploy-key constraints. Post-Vivatech, this
  pin is swapped for the public PyPI release in a separate commit and the
  branch merges back to `dev`.
- **Cross-repo feature, driven from `e-footprint-interface`** per the
  workspace `CLAUDE.md`. Spec, plan, and the unified `tasks.md` live here.
- **Test assertions on EcoLogits outputs must be structural** (units,
  presence, non-negative, monotonicity in duration), not literal numerical
  magnitudes — EcoLogits may re-fit its regression and we don't want silent
  test churn on every upstream bump.

## 6. Resuming from cold context

1. Read this file.
2. Read [`plan.md`](plan.md) for the design — module layout, class shapes,
   parameter names, internal hypotheses, and refactor steps.
3. Read [`tasks.md`](tasks.md) (when written) for ordered, independently
   shippable steps.
4. Cross-reference the existing EcoLogits LLM integration at
   `efootprint/builders/external_apis/ecologits/ecologits_external_api.py`.
5. Read `PRIVATE_INTEGRATION.md` for the branch / remote / pinned-dep
   constraints during the Vivatech 2026 window.
