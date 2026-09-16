# Reference modeling of e-footprint-interface

> **Status:** working reference. The usage story and measurement contract are defined; benchmark values, deployment
> inventory and carbon results are still to be collected. Do not infer an optimization or AI break-even result from
> this document.

This folder is the durable home for modeling the operation of e-footprint-interface with e-footprint itself. It starts
with the usage story needed by the 2026 carbon break-even case, but is deliberately not tied to that article: the same
journeys, fixtures and measurements should be reusable for later optimization work and for changes such as adding a
generative-AI component to the application.

The current article concept is
[`ai-assisted-ecodesign-carbon-case.md`](../../../e-footprint/communications/articles/2026-09-ai-assisted-ecodesign-carbon-case/ai-assisted-ecodesign-carbon-case.md).
The product journeys from which this workload is derived live in [`../design/`](../design/README.md).

## The measurement contract

Keep three layers separate:

1. A **benchmark operation** is one complete, user-visible server operation on a fixed model fixture: save an edit,
   open results, build a cold Sankey, compare two models, and so on.
2. A **usage session** is a stated mix of those operations representing something a person came to accomplish.
3. A **traffic trajectory** says how many sessions occur over time and with which hourly distribution.

Benchmark observations belong to the first layer. Session composition and traffic are modeling assumptions and can be
changed without rerunning a benchmark. This prevents an uncertain launch forecast from contaminating the measured
per-operation evidence.

The primary functional unit for communication is **one active modeling session of a named type**. Supporting results
may also be reported per benchmark operation, per calendar year, for the complete horizon, and for the stationary year.

## Usage story

The design documentation has six journeys faithful to the deployed application: onboarding, build a model, view
results, audit a result, compare models, and save/load. For operational modeling, they combine into four user intents.
The counts below are initial hypotheses to exercise the model, not observed behavior. Replace them with privacy-safe
production aggregates after launch.

| ID | Session | What the person accomplishes | Initial operation mix |
|---|---|---|---|
| S1 | **Explore an example** | Starts modeling, selects a maintained template, reads its footprint and inspects where it comes from. | 1 template load; 1 Results opening; 1 cold Sankey; 1 warm Sankey refinement |
| S2 | **Build and refine a model** | Opens a model, changes assumptions and structure, checks the effect, audits selected values, then keeps a copy. | 1 load; 6 mutations with Results closed; 1 explicit Results opening; 2 mutations with Results open; 3 cold Sankeys; 1 warm Sankey refinement; 2 audit lookups; 1 model export |
| S3 | **Compare an alternative** | Duplicates or imports a second model, edits the alternative, and checks whether the change helps. | 1 load; 1 duplication/import; 3 saved mutations; 2 comparisons; 1 workspace export |
| S4 | **Audit and reuse a model** | Opens an existing model, traces evidence and derivations, exports sources, and saves the model or workspace. | 1 import; 1 Results opening; 3 audit lookups; 1 sources export; 1 model/workspace export |

An operation count means an actual server request that completes the named work. Purely client-side actions such as
changing chart granularity, closing a panel, switching a resident canvas, or dismissing comparison are not separate
compute jobs. Their downloaded assets and browser work may still belong in a whole-service assessment if material.

Landing-page-only visits are tracked separately from active sessions. They matter to total service traffic but are not
expected to explain the optimization savings. The visit-to-session conversion varies by launch case below. The initial
working mix among active sessions is 65% S1, 25% S2, 7% S3 and 3% S4.

These percentages are deliberately easy to replace. Do not present them as analytics.

### Prospective journeys

`analyse-results`, `audit-a-result-target`, `impact-on-canvas`, and `share-a-model` are target-state designs, not current
production traffic. Exclude them from the baseline. When one ships, express it as changes to the operation catalogue
and session recipes below. For example, an in-product GenAI assistant would add an external-API job to the affected
step; it would not erase the surrounding load, edit, results and export work.

## Benchmark operation catalogue

The first benchmark campaign should prioritize B3–B7 because they are the likely source of material differences
between the historical and optimized implementations. The remaining operations make the session and whole-service
model complete.

| ID | Benchmark operation | Boundary and cache state | Existing reference |
|---|---|---|---|
| B0 | **Provisioned idle hour** | Complete production stack with no user request; include periodic maintenance separately. | Clever Cloud deployment inventory; production logs |
| B1 | **Hydrate builder** | Load a fixed session model and render the canvas; no result calculation. | Memory profiler `hydrate` scenario |
| B2 | **Load/import model** | Validate, deserialize, recompute as required, persist, then render the usable canvas. Test template and uploaded-file variants. | Onboarding and save/load journeys |
| B3 | **Save a mutation, Results closed** | Open/edit is setup; time the POST through invalidation, persistence and all response fragments. Use a change that affects calculated state. | Build-a-model journey; full-journey E2E |
| B4 | **Save a mutation, Results open** | Same change as B3, but include the regenerated standard-results response. Count the following Sankey request separately as B6. | Results recomputation E2E |
| B5 | **Open standard results** | Hydrated model to completed yearly/cumulative result response, before attribution/Sankey. Record calculated-state cold and cached variants. | Memory profiler `results`; `result-chart/` |
| B6 | **Generate cold attribution/Sankey** | Empty relevant calculation cache; complete attribution and render-ready payload. | Memory profiler `cold-sankey`; `sankey-diagram/` |
| B7 | **Refine warm attribution/Sankey** | Same hydrated model with its attribution matrix already computed; change one analysis setting. | Memory profiler `warm-sankey`; Sankey E2E |
| B8 | **Compare two models** | Both fixed models hydrated and computable; build a fresh dashboard and chart payloads. | Compare-models journey; `compare/` |
| B9 | **Audit one value** | Open one calculated explanation and then its calculus graph, distinguishing cached and uncached states if they differ. | Audit-a-result journey |
| B10 | **Export** | Measure model JSON, two-model workspace JSON, and sources xlsx separately. | Save/load and view-results journeys |
| B11 | **Maintenance hour** | Session cleanup and any other recurring worker work, measured independently of idle. | Production Supervisor configuration |

Opening an edit panel is a useful latency regression check, but it should become a carbon-model job only if measurement
shows non-trivial server work. Likewise, warm Sankey work must remain distinct from the cold calculation: combining
them would hide both the expensive first use and the cheap cached interaction.

Every request reconstructs `ModelWeb`, so B2–B10 already include their own hydration and rendering overhead. B1 is a
diagnostic decomposition, not another operation to add to every session. B4 likewise includes standard-results work;
do not add B5 for the same mutation response. The browser's following Sankey request remains B6 because it is a distinct
request and computation.

### Composite load tests

After isolated operations are stable, replay complete S1–S4 sessions and a weighted mix. Test concurrency at 1, 2, 4
and 8 active sessions against the production-shaped single-worker stack. Record queueing and throughput rather than
pretending concurrent requests execute in parallel. The existing
[`run_full_journey_in_parallel.py`](../../tests/e2e_perf/run_full_journey_in_parallel.py) is a useful seed, but its
create-from-scratch test workflow and one total elapsed time are not yet the canonical benchmark.

## Fixture portfolio

Every historical/current comparison uses the same semantic scenario. Prefer byte-identical input when both versions
accept it. When schemas differ, generate version-specific serializations from one canonical scenario manifest and
verify that object topology, modeled duration and user-supplied values match. Serialized file size alone is not a
useful complexity measure.

| ID | Purpose | Starting point | Decision before measurement |
|---|---|---|---|
| F1 | Small, understandable web baseline | Maintained **Classical e-commerce** introductory template | Freeze an article-specific copy and record topology/duration |
| F2 | Richer web and external-API topology | Maintained **AI chatbot** introductory template | Freeze a copy; do not count the modeled chatbot's emissions as emissions caused by running this interface |
| F3 | Mixed web/edge coverage | Maintained **Industrial IoT** introductory template | Freeze a copy and use it for ordinary mixed-system paths |
| F4 | Memory-stress boundary | Current smart-building shared-pattern scenario | Replace the untracked external file with a publishable, deterministic fixture or generator before it becomes article evidence |

F1 is the initial default for complete user sessions. F2 and F3 check that results do not depend on one object family.
F4 is a capacity and reliability case, not a proxy for the average user. A minimal test fixture may be retained as F0
for smoke checks but must not support an environmental claim.

Run each fixture in at least these states where applicable: fresh process/cold calculation cache, warm worker/cold
calculation cache, and warm worker/warm calculation cache. The state is part of the benchmark identity.

### Baseline compatibility

Only common functionality supports a direct historical/current A/B. If a current operation did not exist in the
historical application, do not treat its historical cost as zero. Either select the nearest reproducible
pre-optimization implementation of that operation or model a clearly labeled counterfactual range. Report the
like-for-like common-operation result separately from the footprint of today's complete product mix.

The same rule applies when an old version cannot load a current object family. Reduce the shared fixture to the largest
semantically equivalent topology both versions support, then retain the richer current fixture as a present-day
capacity result rather than folding it into the A/B ratio.

## Deployment and machine conditions

### Production-shaped reference

The relevant constraint is the capacity visible to the process, not the commercial label of the plan. The Docker image
currently runs Supervisor, nginx, one preloaded Gunicorn worker and the Django application; PostgreSQL and Redis/cache
services must be inventoried as separate resources when they are actually provisioned.

- Record the exact image digest, git SHAs for both repositories, Python/dependency versions and architecture.
- Model the production Docker container with its operator-reported allocation of **4 vCPU**. Keep measured job CPU
  occupancy separate from this capacity ceiling.
- Record `memory.max` or its cgroup-v1 equivalent on every run.
- Use **2,926 MiB** as the constrained reference until a lower observed production capacity supersedes it. Recent
  deployments of the nominal 4 GB environment exposed about 2,926–3,176 MiB, including a 2,975 MiB observation.
- Keep the current 85% computation guard and 60% post-request recycling thresholds in the record. They affect
  reliability and worker lifetime, not the amount of useful work performed.
- Record the Clever Cloud region, host/instance information available to the tenant, add-on plans and replication,
  but mark provider details that cannot be observed as assumptions.

The 4 GiB local container remains useful for reproducibility, but it is not a substitute for the smaller production
cgroup. At minimum, run a 4,096 MiB reference and a 2,926 MiB constrained case.

### Developer-machine reference

Use the developer machine for stable, interleaved historical/current A/B runs and direct energy measurement if a sound
tool is available. Record hardware model, CPU architecture/core count, installed RAM, operating-system version, power
mode, background-load policy and whether the app is native or containerized.

Local and hosted wall times are not interchangeable. Use local ratios to establish the implementation difference, and
hosted runs to calibrate absolute latency, memory headroom, queueing and feasibility on the real deployment. If both
historical and current versions can run on the hosted environment, repeat the A/B there. If the historical version
cannot complete inside 2,926 MiB, record that as a capacity result; do not replace it with an extrapolated latency.

## What to record

For every operation/repetition, retain machine-readable raw data and a compact reviewed summary:

- fixture, topology, modeled duration, code/image versions and cache state;
- wall time and process CPU time;
- direct energy where measurable, with tool, sampling resolution and idle subtraction method;
- worker RSS, container current/working-set peak, post-request/post-GC memory and cgroup capacity;
- request/response bytes and persistent/cache bytes read or written where material;
- status, timeout/OOM/guard interruption, worker recycle and time until a replacement worker is ready;
- concurrency, throughput and p50/p95 response time for composite load tests.

Use at least seven interleaved repetitions for historical/current comparisons and report the median plus distribution;
fresh containers are required for cold-process cases. Randomize or alternate versions to reduce thermal and temporal
bias. Preserve failures in the dataset.

Do **not** multiply a latency ratio by a peak-memory ratio and call the product an environmental saving. CPU/energy
reduction and infrastructure-capacity consequences are separate results. A memory improvement matters environmentally
when it changes provisioning, prevents retries/restarts, or enables consolidation; a response-path improvement matters
when it reduces actual compute or energy, not merely when work moved elsewhere.

## Mapping the evidence into e-footprint

Build two otherwise identical systems as sibling models in one interface workspace per adoption scenario: the current
optimized application in the Reference slot and the reproducible no-AI, low-optimization counterfactual in the
Comparison slot. Keeping the scenario pair in one `.e-f.json` file makes the comparison directly loadable and prevents
traffic assumptions from drifting between separately handled files.

The maintained implementation profiles live in
[`optimizations/implementation-profiles.json`](optimizations/implementation-profiles.json). Usage scenarios are shared;
the profile changes only implementation-dependent job duration, transferred bytes and the container tier selected from
the reconstructed maximum-request memory. This prevents traffic edits from drifting between the current and
counterfactual systems. The spreadsheet inventory remains a review surface, while the profile JSON is the generator's
machine-readable source of truth.

- Represent the production application and its backing services explicitly in infrastructure. Keep unobserved provider
  layers as sourced ranges.
- Map each material benchmark operation to a `Job` with measured request duration, CPU need, RAM need and transferred or
  stored data. A multi-request operation may use several jobs when cache/database/network costs are measured separately.
- Map S1–S6 to `UsageJourney` objects whose steps invoke the benchmark jobs with the counts above.
- For each geography, use one full-horizon human `UsagePattern` weighted across S1–S5 and one automated pattern linked
  to S6. Human weights are horizon-wide averages chosen to preserve every journey's cumulative occurrence total; this
  deliberately smooths the hypothetical pre-/post-launch mix change while retaining the exact human volume curve.
- Represent idle provisioned capacity and recurring maintenance explicitly; neither should disappear when traffic is
  zero.
- Keep components unchanged by the optimization visible but identical in both models. Report both total service impact
  and the avoided operational impact.

### Temporary minimum-instance workaround

Until autoscaling servers support an explicit minimum-instance floor, model the production deployment with one
continuous logical keep-alive thread, represented as contiguous one-hour job segments with minimal non-zero compute
and RAM demand. Its positive raw demand makes autoscaling round the provisioned instance count up to one in every
otherwise idle hour, while real jobs can still drive additional instances. A single multi-year `Job` must not be used:
the concurrency convolution extends its result beyond the input series and introduces FFT noise at this duration.

Keep the synthetic demand negligible and identical in the historical and current systems. Report it as a modeling
workaround: it slightly reduces available capacity and contributes a small dynamic-load footprint. The future
first-class requirement is parked in
`../e-footprint/specs/features/improved-autoscaling-modeling/README.md`.

Peak RAM is not automatically the `ram_needed` of an average request. Use the isolated incremental working set when it
is defensible, and use a separate capacity scenario for cold peaks that determine whether the deployment can serve the
operation at all.

For an isolated CPU-bound request, derive average `compute_needed` as process CPU seconds divided by measured service
time, expressed in CPU cores. Use service time rather than load-test queueing time. Keep the raw CPU seconds, wall time
and derivation attached as sources so the mapping can be challenged or replaced by direct energy evidence.

## Launch traffic cases

No production usage evidence exists yet, so these figures are structured scenarios rather than forecasts. Adoption
reach and automation intensity are separate axes. Post-launch usage is derived from the stock of active teams and the
activity generated by their maintained models rather than from an unexplained aggregate growth percentage.

| Year-end | Niche active teams | Central active teams | Breakout active teams |
|---|---:|---:|---:|
| 2026 | 5 | 10 | 20 |
| 2027 | 15 | 30 | 100 |
| 2028 | 30 | 90 | 400 |
| 2029 | 45 | 180 | 1,000 |
| 2030 | 50 | 260 | 1,600 |
| 2031 | 50 | 295 | 1,950 |
| 2032 | 50 | 300 | 2,000 |

Public exploratory sessions outside identified teams scale with this adoption curve to 250/month for niche reach,
2,000/month for central reach, and 15,000/month for breakout reach. The activity regimes are:

| Regime | Models/team | Interactive sessions/team/month | Automated S6 runs/model/month | Team occurrences/month at maturity |
|---|---:|---:|---:|---:|
| Human-led | 4 | 6 | 0.5 | 8 |
| Team-integrated | 10 | 8 | 4 | 48 |
| Agent-intensive | 20 | 10 | 30 | 610 |

The automation frequency ramps to the regime target over the first 24 months after public launch. Public exploratory
sessions use a 70% S1, 20% S2, 3% S3, 2% S4 and 5% S5 mix. Team-interactive sessions use 5% S1, 35% S2, 25% S3, 15%
S4 and 20% S5. S6 is added separately from the models-per-team automation calculation.

Five combinations are maintained as the canonical range:

| Scenario | Mature occurrences/month | Mature occurrences/year |
|---|---:|---:|
| Niche, human-led | 650 | 7,800 |
| Central, human-led | 4,400 | 52,800 |
| Central, team-integrated | 16,400 | 196,800 |
| Breakout, team-integrated | 111,000 | 1,332,000 |
| Breakout, agent-intensive | 1,235,000 | 14,820,000 |

The model runs from Sep 2025 through Dec 2033. Before the Oct 2026 launch it assigns 50 development occurrences per
month using the pre-launch journey mix. Active-team anchors are interpolated monthly through Dec 2032; their final
values are then held for all of 2033, providing one genuinely complete stationary year. This explicit plateau is a
scenario boundary, not a claim that real adoption must stop then.

Until production aggregates establish a real hourly shape, run two timing sensitivities: a uniform 24/7 distribution
and a Europe-centered office-hours pattern with 70% of sessions Monday–Friday 08:00–18:00 Europe/Paris and 30% spread
across all other hours. The latter is a provisional audience hypothesis, not a claim about future users.

S6 is an agent-triggered maintenance run: import, update one assumption, compute results, inspect one explanation, and
export. It carries no human device time. These scenarios measure the resulting e-footprint-interface load only; the AI
agent's own inference and execution footprint remains outside the model until provider, model, token, region, and host
evidence is available.

The article's most robust output is a threshold, not a forecast:

`break-even active sessions = additional development impact / avoided impact per weighted active session`

Also show time to break even under each traffic case and the result when idle infrastructure does not scale down. This
makes the conclusion useful even if actual adoption differs sharply from all three projections.

### Replace forecasts with evidence after launch

Collect only privacy-safe aggregates needed to update the model: daily counts by normalized route, status and coarse
latency/memory bucket; template/import choice; cold/warm attribution; exports; comparisons; guard interruptions; and
concurrent-request/queueing indicators. Do not log model names, serialized content, calculated values, source labels,
session identifiers or IP addresses. Define a short observation window after launch, publish the aggregation rules,
then replace the provisional conversion, mix and cache-hit assumptions with ranges supported by those aggregates.

## Next artifacts

Keep this README as the stable method and usage story. Add, without overwriting prior evidence:

- `fixtures/` — frozen publishable inputs or deterministic generators plus topology manifests;
- `benchmarks/` — the replay runner and a versioned operation manifest;
- `benchmarks/results/` — reviewed compact evidence and summaries; per-run request traces stay local and Git-ignored;
- `models/` — historical/current e-footprint model files for each traffic and lifetime case.

The next stage is to freeze F1–F3, select reproducible historical and current SHAs, and implement B1–B10 as an
instrumented operation runner. Optimization comparison comes only after that common workload is reviewable.
