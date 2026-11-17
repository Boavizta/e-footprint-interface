# Decisions already made — ai-bootstrap-edge

- Two scopes only, `web` and `web_edge`; no edge-only variant.
- One AI model and one effort for both scopes: `zai-glm-5-3-flash` on Mistral at
  `reasoning_effort="low"`, as today. Mistral refuses `medium` for this model (supported: low, high,
  max). Chosen from sandbox runs; paid runs need the user's word for each run. Web only, 2026-11-17 (cases 01
  and 02, no retry): low 6/6 first-try success, 18–28 s, about USD 0.0012 a call; high 6/6, 22–44 s,
  about USD 0.0020–0.0025 a call (about twice the output tokens), at the production adapter's 45 s
  timeout; one further high call lost its connection before answering. The checks pass at both
  efforts, so on these cases high buys no measured gain for Web only.
- The sandbox gets its edge material back from git history: commit `6671a149` removed the edge
  paradigm section of `system_prompt.md`, the `edge_devices` / `edge_functions` / `edge_deployments`
  format and field notes, the edge part of the DSL builder in `dsl.py`, the edge checks and reports,
  and case `03_smart_building_edge.json` with `_handwritten_03_smart_building.json`. Read it with
  `git show 6671a149^:ai_sandbox/<path>`. The library's edge API has moved since (edge usage journeys
  hold edge functions, `RecurrentServerNeed`, `EdgeDeviceGroup` with `sub_group_counts` and
  `edge_device_counts`); the old builder is a starting point, not a drop-in.
- `EdgeDeviceGroup` is part of the Web + edge format, optional: the prompt says when to use it
  (devices deployed together per site, vehicle or building), and never requires it.
- The scope travels with the generate request and is re-rendered on a refused generation; nothing
  of it is persisted.
- The sandbox's Web + edge evaluator is `ai_sandbox/edge_dsl.py` and `--scope web_edge` of
  `ai_sandbox/run.py` (commit `65c5f108`), with cases 03 (groups relevant) and 04 (fleet totals
  only). It is the starting point of the production edge format; its `requires_device_group` check
  is informative only, `device_totals` is the correctness check.
- Cross-repository prerequisite, a library lot before the interface's: a `RecurrentServerNeed`'s
  volume is scaled by deployments but not by `EdgeDevice.total_nb_of_units`
  (`RecurrentServerNeed.unitary_hourly_volume_per_usage_pattern`, `Job.hourly_occurrences_per_usage_pattern`),
  against its own parameter description. Fix it in e-footprint; no interface guard.
- No installed base in this iteration. Every generated timeseries, web or edge, is an
  `ExplainableHourlyQuantitiesFromFormInputs` (the Growth projection editor), never a raw series: the
  interface's only editor for an hourly field prefills from `form_inputs` alone
  (`timeseries_builder_registry.py`), so a raw series opens empty and a save loses it. The sandbox's
  `existing_units` and its noon-of-day-1 spike in `edge_dsl.py` go, and its `device_totals` check,
  read in the first week, must be redefined against deployments per period and usage span. A stated
  fleet size becomes a deployment rate and, for a fleet already in service, a `start_date` in the
  past in the same form inputs, its derivation in the value's comment. The AI sets that start date;
  the plan settles how a past start lines up with the web usage patterns' fixed start and the
  modeling duration.
- Library edge defaults are sized for a PC (30 GB base storage, 1 GB base RAM, 5 W idle) and fail
  capacity checks on gateways and sensors; the sandbox builder caps them and fits a rolling storage
  buffer, and defaults the usage span to the shortest device lifespan (6 years at most).
- The Web + edge prompt is 8,570 characters against 5,157 for Web only.
- Web + edge, 2026-11-17 (cases 03 and 04, 3 repetitions, no retry): low 5/6 built on the first
  try, 8–27 s, about USD 0.0013 a call; high 6/6 built, 19–42 s, about USD 0.0021 a call. Checks:
  low missed the monthly report journey once (03) and the shared server once (04); high passed 03
  three times and missed the shared server on 04 three times. High buys no clear gain here either.
- What failed was the format and the prompt, not the effort. The schema refused an answer whose
  deployment stated an installed base and no growth; with no installed base the deployment rate is
  the required input, and the prompt must say how a stated fleet size becomes one. On case 04 the stations' server call reached the OCPP backend but not the
  database write behind it, so devices and the dashboard shared no server: the prompt must say that
  a server call lists every job it triggers, the database write included.
- Case 03's computed totals vary eightfold between repetitions (0.25 to 2.0 kt CO2-eq) with all
  checks passing: device-footprint assumptions are the next thing to inspect in the reports, after
  the library fix of server-call volumes.
