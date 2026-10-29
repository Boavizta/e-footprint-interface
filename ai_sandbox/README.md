# AI sandbox: structure generation experiments

Local experiment runner for the AI-assistance exploration described in
[`specs/ai-assistance/README.md`](../specs/ai-assistance/README.md). It tests one facet only:
**from a complete user description, can an LLM produce a useful e-footprint model structure, at what cost?**

Scope is web modeling only (usage journeys, servers, GenAI APIs), as if the interface's edge toggle were off. Edge
modeling was removed on 2026-10-29 to keep the prompt and DSL small: it is a different problem (device counts and
ratios, embodied footprints), and the two serious semantic errors of the last run that had it were both edge
mistakes. If it returns, it is a separate assistant reusing the server and job vocabulary.

Nothing here is part of the Django application. Run outputs under `runs/` are git-ignored.

## How it works

1. `prompts/system_prompt.md` teaches the model the e-footprint mental model and a compact JSON DSL
   (objects, relationships, optional numbers, a `comments` sentence per stated number that becomes the value's comment in the model).
2. `cases/*.json` hold a realistic product-person prompt, facts available if asked (for later clarification
   experiments), expected properties for expert review, and machine checks.
3. `providers.py` calls Anthropic, OpenAI or Mistral with the same system prompt and user prompt, and records
   tokens, latency, cost (prices captured 2026-10-27, see the module docstring).
4. `dsl.py` validates the output against the DSL (pydantic) and builds a real `System` with `from_defaults`,
   so every unstated value falls back to the library default.
5. `run.py` computes the system, exports it to the interface JSON format (`*.e-f.json`, importable through
   *Open file* in the interface or the report's *Open in interface* link), reloads it to prove it round-trips, runs the
   structural checks, and writes one record per call. `report.py` turns a run dir into `summary.md` and `summary.html`.

The interface's experimental assistant (`AI_ASSISTANT_ENABLED`, dev app only) imports this folder: on an empty model
it runs the same stages and loads the built system; on a non-empty model `edit.py` reads the model back into the DSL
(`system_to_dsl`), the request is sent with `prompts/edit_prompt.md` appended to the system prompt, and the answer's
changed, added and removed objects are applied to the live model through the same builders and field tables
(`apply_edits`), with the session persisted once at the end. Removals are the interface's delete use case.

Stages recorded per call: JSON parse (first attempt vs repaired) → schema valid → build → compute → export.
A failure at any stage is recorded with the error, never raised. When parse, schema, build or compute fails, the
model is called again with its previous output and the error (`--retries`, default 1; export failures are ours and
are not retried). The record holds the last attempt at top level, summed tokens, latency and cost, `first_try_ok`,
and the earlier attempts under `attempts`; the reports show tries per record and first-try success per model.
`--replay` re-evaluates the last attempt only.

## Commands

```bash
# free: check keys and model ids
poetry run python ai_sandbox/providers.py

# pipeline check without an LLM
poetry run python ai_sandbox/run.py --dry-run ai_sandbox/cases/_handwritten_01_recipe_app.json

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
  GenAI API, then the declared servers and APIs, with field comments muted under their object. It shows what the model said, not the effective values after
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

## Models

| Model | Provider | USD in / out per M tokens | Default run |
|---|---|---:|---|
| claude-haiku-5-5 | Anthropic | 0.10 / 0.50 | yes |
| gpt-6-luna | OpenAI | 0.10 / 0.50 | yes |
| claude-sonnet-5-5 | Anthropic | 2.00 / 10.00 | `--models` |
| gpt-6.1-terra | OpenAI | 1.00 / 5.00 | `--models` |
| mistral-small-latest | Mistral | 0.15 / 0.60 | `--models` |
| mistral-medium-latest | Mistral | 1.50 / 7.50 | `--models` |
| mistral-large-4 | Mistral | 1.36 / 4.18 | `--models` |
| claude-opus-5-5 | Anthropic | 4.00 / 20.00 | `--models`, reference |
| zai-glm-5-3-flash | Z.ai via Mistral | 0.15 / 0.50 | yes, open weights |
| deepseek-v4-1-flash-1017 | DeepSeek via Mistral | 0.30 / 1.20 | yes, open weights |
| zai-glm-5-3 | Z.ai via Mistral | 1.40 / 4.40 | yes, open weights |

The first full run (`runs/20261028-164221`, 3 cases x 7 models x 2 reps) narrowed the default to Haiku and Luna:
Sonnet and Large 4 cost 10x for no structural gain, Medium and Small take the user count as the journey volume.
The three open-weight models were added afterwards through the Mistral platform (one key, same adapter); GLM
reasoning cannot be switched off, so they run at effort `low` unless `--effort` says otherwise. They joined the
default run on 2026-10-29.

## Design choices worth challenging

- **Structure DSL, not library JSON.** The library format for the e-commerce example is 26 KB; its authoring
  script is 5.7 KB. The DSL is smaller still and lets the model omit any number. The cost is a builder to
  maintain (`dsl.py`, about 250 lines) and a vocabulary that is not the library's.
- **No provider-side schema enforcement.** All providers get the same "JSON only" instruction (plus JSON mode
  where it is free: OpenAI and Mistral). Validity is checked locally so results are comparable. Strict
  structured outputs are a separate knob to test later.
- **One year horizon, constant volumes.** `MODELING_START_DATE` and `MODELING_DURATION_YEARS` in `dsl.py`. Fine
  for structure comparison, not for final numbers.
- **Catalog choices are resolved in code, not in the prompt.** `catalogs.py` snaps a GenAI `provider`/`model_name`
  to the EcoLogits catalog and a `cloud_provider`/size to a real Boavizta instance (general-purpose families only,
  specs cached in `catalogs/boavizta_instance_specs.json`, refresh with `poetry run python ai_sandbox/catalogs.py refresh`).
  Every non-exact resolution is recorded in the run record, so hallucinated names stay measurable.
- **Every CPU server is a cloud instance.** A server with no `cloud_provider` is sized on `DEFAULT_CLOUD_PROVIDER`
  (aws) in `catalogs.py`. The library's plain `Server` default is a whole physical machine, 30-40x the footprint of
  a small instance, so whether a model happened to name a provider swung the server total (Luna never names one, the
  open-weight models always guess one). GPU servers keep the library `GPUServer` default.
- **Numbers are asked for, not left out.** The first prompt said to leave unstated numbers to library defaults.
  Models that obeyed answered "does video or ML dominate" with a default payload for a 30-minute video stream.
  The prompt now asks for an order-of-magnitude estimate whenever
  the description implies one, with the derivation in a per-field `comments` entry that becomes the value's
  comment in the model.
- **No questions during generation.** Clarification is a separate UX step before generation (the user refines the
  description, then the model is generated), so the prompt no longer asks for `open_questions` (removed 2026-10-29).
  The questions it produced also rarely targeted the dominant driver: in the recipe case, 1 of about 50 asked about
  session length, which drives the phone footprint. Cases keep `facts_if_asked` for that clarification step.
- **Checks are coarse.** They catch missing object kinds, missing sharing, missing low-volume batch journeys.
  Semantic quality still needs expert review of `summary.md` and of the exported model in the interface.
