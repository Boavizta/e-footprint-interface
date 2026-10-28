# AI sandbox: structure generation experiments

Local experiment runner for the AI-assistance exploration described in
[`specs/ai-assistance/README.md`](../specs/ai-assistance/README.md). It tests one facet only:
**from a complete user description, can an LLM produce a useful e-footprint model structure, at what cost?**

Nothing here is part of the Django application. Run outputs under `runs/` are git-ignored.

## How it works

1. `prompts/system_prompt.md` teaches the model the e-footprint mental model and a compact JSON DSL
   (objects, relationships, optional numbers, one `assumption` per judgement call, a few `open_questions`).
2. `cases/*.json` hold a realistic product-person prompt, facts available if asked (for later clarification
   experiments), expected properties for expert review, and machine checks.
3. `providers.py` calls Anthropic, OpenAI or Mistral with the same system prompt and user prompt, and records
   tokens, latency, cost (prices captured 2026-10-27, see the module docstring).
4. `dsl.py` validates the output against the DSL (pydantic) and builds a real `System` with `from_defaults`,
   so every unstated value falls back to the library default.
5. `run.py` computes the system, exports it to the interface JSON format (`*.e-f.json`, importable through
   *Open file* in the interface or the report's *Open in interface* link), reloads it to prove it round-trips, runs the
   structural checks, and writes one record per call. `report.py` turns a run dir into `summary.md` and `summary.html`.

Stages recorded per call: JSON parse (first attempt vs repaired) → schema valid → build → compute → export.
A failure at any stage is recorded with the error, never raised.

## Commands

```bash
# free: check keys and model ids
poetry run python ai_sandbox/providers.py

# pipeline check without an LLM
poetry run python ai_sandbox/run.py --dry-run ai_sandbox/cases/_handwritten_03_smart_building.json

# experiments (ANTHROPIC_API_KEY, OPENAI_API_KEY, MISTRAL_API_KEY read from .env)
poetry run python ai_sandbox/run.py --cases 01 --models claude-haiku-5-5 mistral-small-latest --reps 1
poetry run python ai_sandbox/run.py --reps 2 --effort medium         # all cases x DEFAULT_MODELS
poetry run python ai_sandbox/run.py --replay ai_sandbox/runs/<dir>    # re-evaluate recorded outputs, no API call
poetry run python ai_sandbox/report.py ai_sandbox/runs/<dir>
```

## Browsing results

Every run (and `--replay`) ends by writing `summary.md`, `summary.html` and `runs/index.html`; `report.py <run dir>`
regenerates them. Open `ai_sandbox/runs/index.html` in a browser: it lists the runs and links to each `summary.html`,
which holds the sortable comparison table (filter by case or model), the per-model aggregates, and one section per
record with:

- a **structure tree** rendered from the DSL JSON the model wrote: usage patterns → journey → steps → jobs → server or
  GenAI API, edge deployments → functions → device and server calls, then the declared servers, APIs and edge
  devices, with assumptions muted under their object. It shows what the model said, not the effective values after
  library defaults filled the gaps;
- **structural warnings** computed from the DSL (dangling references, unused objects, jobs with no target), the
  record's checks, counts, totals by category, catalog resolutions (non-exact ones highlighted), cost, and the case's
  rubric;
- previous/next links across the other outputs for the same case, and the raw output in a collapsible block;
- an **Open in interface** link. It targets `/dev/load-file/?path=<export path>` on a locally running interface
  (`poetry run python manage.py runserver`, `http://localhost:8000` by default, override with
  `EFOOTPRINT_INTERFACE_URL`). That route exists only when Django `DEBUG` is true, only opens files under
  `ai_sandbox/runs/`, and replaces the active model in the browser session without confirmation, exactly like the docs'
  "Load this scenario" deep link.

`--max-cost-usd` (default 3) stops launching calls past that total. `--effort` maps to
`output_config.effort` (Anthropic), `reasoning.effort` (OpenAI) and `reasoning_effort` (Mistral); omitted means
the provider default, which is recorded in `request_params`.

## Models compared by default

| Model | Provider | USD in / out per M tokens |
|---|---|---:|
| claude-haiku-5-5 | Anthropic | 0.10 / 0.50 |
| claude-sonnet-5-5 | Anthropic | 2.00 / 10.00 |
| gpt-6-luna | OpenAI | 0.10 / 0.50 |
| gpt-6.1-terra | OpenAI | 1.00 / 5.00 |
| mistral-small-latest | Mistral | 0.15 / 0.60 |
| mistral-medium-latest | Mistral | 1.50 / 7.50 |
| mistral-large-4 | Mistral | 1.36 / 4.18 |

`claude-opus-5-5` is configured as an optional reference model (pass it with `--models`).

## Design choices worth challenging

- **Structure DSL, not library JSON.** The library format for the e-commerce example is 26 KB; its authoring
  script is 5.7 KB. The DSL is smaller still and lets the model omit any number. The cost is a builder to
  maintain (`dsl.py`, about 250 lines) and a vocabulary that is not the library's.
- **No provider-side schema enforcement.** All providers get the same "JSON only" instruction (plus JSON mode
  where it is free: OpenAI and Mistral). Validity is checked locally so results are comparable. Strict
  structured outputs are a separate knob to test later.
- **One year horizon, constant weekly profiles.** `MODELING_START_DATE` and `MODELING_DURATION_YEARS` in
  `dsl.py`; edge needs are flat 168-hour arrays. Both are fine for structure comparison, not for final numbers.
- **Catalog choices are resolved in code, not in the prompt.** `catalogs.py` snaps a GenAI `provider`/`model_name`
  to the EcoLogits catalog and a `cloud_provider`/size to a real Boavizta instance (general-purpose families only,
  specs cached in `catalogs/boavizta_instance_specs.json`, refresh with `poetry run python ai_sandbox/catalogs.py refresh`).
  Every non-exact resolution is recorded in the run record, so hallucinated names stay measurable.
- **Checks are coarse.** They catch missing object kinds, missing sharing, missing low-volume batch journeys.
  Semantic quality still needs expert review of `summary.md` and of the exported model in the interface.
