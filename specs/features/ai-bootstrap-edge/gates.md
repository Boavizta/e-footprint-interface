# AI bootstrap for edge systems — gates (for the user, after the run)

## Standing calls

- **One run, every lot.** The invocation granted full autonomy and approved the paid runs, so the
  four lots are delivered in one run and the decisions are handed over grouped by lot.
- **Gate sorting.**
  - `library-server-calls`: no user-held gate. It lands in `../e-footprint` on `dev`, with its own
    commit range; the map cannot see it and read the lot as delivered from the start.
  - `scope-and-format`: no user-held gate, no paid call.
  - `edge-builder`: an evidence gate, the paid runs of cases 03 and 04. The user's word for them
    was given at the invocation ("I approve the paid runs that need be done at the end of the
    implementation"), so the run makes them itself, at low effort, once the lot is reviewed. The
    raw readings are under "Evidence".
  - `scope-choice`: a validation by eye of the scope radio and its disclosure. The lot ships
    fully tested; the check is under "Checklist".
- **The `efootprint` dependency.** `pyproject.toml` and `poetry.lock` already pointed at the local
  checkout (`../e-footprint`, editable) before the run, uncommitted. The run leaves both files as
  it found them and commits neither.
- **The user's answers on the delivery page, read on 2026-11-18** (13 approved, 2 not read: the
  two paragraphs saying where the Web + edge prompt file shows up). Applied, range
  `9e74f2ac..91489c99`, built by an implementer and read by a reviewer:
  - the hourly editor's limit is 10 years / 120 months again ("Don't increase the hourly editor's
    limit. Beyond 10 years, web usage is cut and listed."); a deployment longer than it is refused;
  - both cost lines carry two significant figures (0.12 and 0.15 US cent);
  - asked in the conversation and answered there: a stated web volume is the one of 2027-01-01,
    discounted by its growth back to an earlier start (the point this file held as "not built");
    a usage span above its devices' shortest lifespan is cut and listed; a comment written as a
    number is read as text; nested groups ship as they are, with "explore stronger models once
    provider calls are asynchronous" added to `specs/features/ai-assistance/roadmap.md`.
- **Decided by the supervisor, for the user to refuse on the delivery page: the growth and
  recurrent editors accept any decimal.** The review of that range found that a generated value
  could open in the editor on a number the browser refused to save unchanged (a weekly volume not
  divisible by 7, in 28 of 96 recorded answers; a workload of 0.05; a call 0.33 times an hour),
  against the rule `generated-values-editable`, whose test posts the form and never met the
  browser. The inputs' `step` is now `any`, for every user of these editors; an imported modeling
  with such values was blocked the same way.
- **Open, asked in the conversation and not answered yet: a deployment that keeps installing for
  more than 10 years** (a fleet "since 2015" with no end) is refused. It could be split by the
  builder into consecutive deployments of 10 years at most, at the same rate, and listed.
- **After the run, on 2026-11-18: a fix and an addition, on the user's word.** The user tried Web +
  edge on the local interface, met a provider failure, then a building whose cabinet was not
  grouped. What followed, all asked or approved in the conversation ("ok for the paid runs, and yes
  log the provider failure kind too", "ok add the coupling as a small piece after the fix"): the
  provider failure's kind is logged; sandbox cases 05 and 06, three prompt edits and two builder
  changes for groups inside groups; the panel opens on Web + edge when Edge modeling is on. Each
  was built by an implementer and read by a reviewer; the range is `df9516c4..8949968d`.
- **Supervisor model.** The supervisor ran on `claude-fable-5-2`; `implementer-hard` pins
  `claude-fable-5-1[1m]`.

## Checklist

1. **The scope choice and its two disclosures, by eye.** Nothing downstream waits on it but the
   feature's archive. No paid call is made by these steps.
   1. `AI_BOOTSTRAP_ENABLED=1 MISTRAL_API_KEY=dummy poetry run python manage.py runserver`, open
      `http://localhost:8000/model_builder/`, then Modeling actions → Start with AI.
   2. Web only is checked, with its guidance and its cost and impact line. (With the navbar's
      Edge modeling toggle on, the panel opens on Web + edge instead: turn it on, start with AI
      again, and look.)
   3. Type a description, check Web + edge: the guidance and the cost and impact line change, the
      typed text stays. Read the Web + edge guidance and disclosure wording: both are new copy.
      The web part of the Web + edge guidance leaves out two hints the Web only text gives
      (users against visits, session or step durations).
   4. Do not submit: with the dummy key the provider refuses at no cost, but the description
      would still be sent to it.

   Verdict:
2. **A Web + edge generation, by eye, on the test fake** (the development server has no fake
   switch): `poetry run pytest tests/e2e/test_ai_bootstrap.py -k "web_edge_generation or scope_choice" --headed --slowmo 400`
   (prefix `PWDEBUG=1` to step through). It starts its own server and answers with handwritten
   answer 04. Look at the summary's edge checks after the web ones, the edge objects on the
   canvas, and the generated web usage pattern opening on 10 years from 2024-01-01, its 12 years cut
   and listed in the summary. In a real
   Web + edge generation, also read the summary's list "Changes made to the AI answer" (formerly
   "Catalog substitutions"): a device written among sub-groups reads "… → device … (moved)", a
   device no deployment runs reads "… → left out of the footprint (no deployment runs it)".

   Verdict:

## Post-run operations

1. **Release the library before the interface's deployment commit.** The lot `library-server-calls`
   changed `efootprint` on `dev` (`../e-footprint`, range `afc60887..f9ad5688`): a server need's
   volume now counts every unit of its device, and its attribute is renamed
   `hourly_volume_per_usage_pattern`. The interface's Web + edge bootstrap needs that release: on
   the published `27.0.1` a grouped device sends one unit's calls. The interface's narrative and
   sandbox tests read the renamed attribute, so they go red on the published pin until then. Follow
   `../e-footprint/RELEASE_PROCESS.md` (its `## [Unreleased]` section of `CHANGELOG.md` is
   written), then restore the published pin here as `RELEASE_PROCESS.md` says.
2. **The release must move the version number.** A modeling saved with its computed state at
   `27.0.1` on the local checkout, holding a grouped device with a server need, keeps its stale
   server volume while the version is unchanged; any version change, a patch included, discards
   the stored state and recomputes. Only local sessions on the editable checkout are concerned.

## Evidence

### Paid runs of cases 03 and 04 (lot `edge-builder`)

Made by the run on the user's word given at the invocation. Command, from the repository root:
`poetry run python -m ai_sandbox.run --scope web_edge --cases 03 04 --models zai-glm-5-3-flash --effort low --reps 3 --max-cost-usd 0.5`.
The raw readings are local and git-ignored, under `ai_sandbox/runs/<run>/` (`summary.md`, one json
a call).

**Run `20261118-003854`**, on the build at `e8949fc1` (the lot as reviewed, before the prompt edit
that follows). Total cost USD 0.0096.

| Case | Rep | Built first try | Checks | In tok | Out tok | Reasoning tok | Latency s | Cost USD | Total kg CO2e | Devices in service as 2027 opens |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 03 | 1 | yes | 10/10 | 2,678 | 2,158 | 5 | 10.47 | 0.0015 | 704,008 | 1,474 gateways, 58,960 sensors |
| 03 | 2 | yes | 8/10 | 2,678 | 2,571 | 453 | 16.11 | 0.0017 | 542,569 | 2,998 gateways, 119,920 sensors |
| 03 | 3 | yes | 8/10 | 2,678 | 2,430 | 492 | 14.63 | 0.0016 | 258,352 | 2,206 gateways, 88,240 sensors |
| 04 | 1 | yes | 7/8 | 2,704 | 2,696 | 565 | 18.76 | 0.0018 | 1,826,819 | 5,240 controllers |
| 04 | 2 | yes | 7/8 | 2,704 | 2,462 | 536 | 19.56 | 0.0016 | 1,087,527 | 6,224 controllers |
| 04 | 3 | yes | 8/8 | 2,704 | 1,980 | 240 | 12.83 | 0.0014 | 828,182 | 4,434 controllers |

Stated fleets: 1,500 gateways and 60,000 sensors (03), 4,200 controllers (04). The six failed
checks are the device totals of four calls; every other check passed on every call (a server
shared by devices and people, groups, a usage pattern for every journey, server calls). What the
four answers wrote: a fleet that reaches its stated size at the end of 2024, on 2025-01-01 or on
2026-01-01, then the stated growth from that date to the end of 2027. Three of the six answers
also dated a usage pattern the description does not date.

**Run `20261118-004330`**, on the build at `4224af9b` (the prompt now dates the description's
present to 2027-01-01 and tells the answer to leave a usage pattern's start date out unless the
description gives one). Total cost USD 0.0091. This is the build the lot `scope-choice` discloses.

| Case | Rep | Built first try | Checks | In tok | Out tok | Reasoning tok | Latency s | Cost USD | Total kg CO2e | Devices in service as 2027 opens |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 03 | 1 | yes | 8/10 | 2,825 | 2,226 | 281 | 20.25 | 0.0015 | 148,768 | 1,536 gateways, 61,440 sensors |
| 03 | 2 | yes | 9/10 | 2,825 | 1,838 | 282 | 10.30 | 0.0013 | 471,299 | 1,536 gateways, 61,440 sensors |
| 03 | 3 | yes | 10/10 | 2,825 | 2,513 | 530 | 15.14 | 0.0017 | 213,818 | 1,536 gateways, 61,440 sensors |
| 04 | 1 | yes | 8/8 | 2,851 | 1,854 | 419 | 12.38 | 0.0014 | 704,500 | 4,293 controllers |
| 04 | 2 | yes | 8/8 | 2,851 | 2,529 | 598 | 31.05 | 0.0017 | 661,000 | 4,275 controllers |
| 04 | 3 | yes | 7/8 | 2,851 | 2,167 | 181 | 17.19 | 0.0015 | 1,314,876 | 5,293 controllers |

Failed checks: 03 rep 1, the number of journeys and the low-volume journey (the answer holds
placeholder keys such as `journeys_2_placeholder`, dropped as unknown, and one journey); 03 rep 2,
the server shared by devices and people; 04 rep 3, the device total (108 a month from 2024-09-01
and 75 a month from 2024-07-01, both to 2026-12-31, then 80 a month from 2027-01-01). No answer
dates a usage pattern. The prompt was not edited again.

What the two runs do not settle, read by the lot's reviewer on the raw answers of the first run:
the computed totals spread threefold on each case with the checks passing. On case 03 device
manufacturing dominates and the sensor's manufacturing footprint ranges from 0.1 to 5 kg (the
case's facts: 30 g of electronics), the gateway's from 25 to 60 kg. On case 04 station
electricity dominates and the controller's power ranges from 5 to 15 W (the facts: 8 W). Lifespans
and usage spans of 8 to 10 years against the facts' 5 to 8 lengthen every horizon.

**After the run, 2026-11-18: groups inside groups.** Every count below is of first attempts, since
production makes one request; all at low effort unless said. Case 05 is the user's description,
verbatim ("A smart building in France, with 7 floors, and in each floor 5 sensors + an electrical
cabinet with an industrial PC and 5 merging units…"): right is Cabinet in Floor, Floor × 7 in
Building, one building, 35 sensors, 7 PCs, 35 merging units, no web usage. Case 06 is held out (a
growing chain of stores: a server at the store's root, 3 lanes of a scanner and a terminal, a cold
room of 4 probes); no prompt example has its shape.

| Build | Run | 05 fully right | 05, the misses | 03, 04, 06 |
|---|---|---|---|---|
| `a6c7fe59`, before the fix | six calls with production's parameters, one through the dev server | 0 of 6 (the user's answer and five more) | no answer groups the cabinet; 2 of 5 count 35 / 7 / 35; one refused (the floor names its building as a sub-group); one floor alone; one building a month | not run |
| `becc50e2`, first prompt edit | `20261118-075313` | 1 of 3 | two answers give a function to the PC alone, so sensors and merging units are left out; one of them refused first (a device written as a sub-group) | 03: 2 of 3. 04: 1 of 3, one answer writing the country fleets as groups (17.9 million controllers) |
| `2cbe1e46`, second edit, builder repair | `20261118-080103` | 2 of 4 | one without the Building group; one inventing a web usage on screens (1.3 million kg) and a fourth device | 03: 3 of 4. 04: 3 of 4, no group in any |
| `8a11e0dc`, third edit | `20261118-090032`, `-090921`, `-091235` | 2 of 4 | two without the Building group, one of them deploying from 2017 with no end; no web usage in any | 03: 5 of 8 (one refused, a comment written as a number; one fleet deployed from 2027; one server not shared). 04: 2 of 3 (one refused, a start date in 2028). 06: device counts right in 4 of 4, the cold room grouped in 0 of 4, one refused first and written in Spanish |
| `8a11e0dc`, high effort | `20261118-091749` | 2 of 4 | two refused (a usage span above a device's lifespan) | 06: 1 of 4 fully right, counts right in 2 of 4 first attempts, two refused; 16 to 107 s a call, about twice the cost |

Medium effort is refused by the model (HTTP 400). High effort brings no gain and half its calls pass
production's 45 s timeout, as the spec's "Not doing" already held for cases 03 and 04. What three
prompt edits did not move: the outermost group of a single site left out in one answer of four to
two of four, and (case 06) a container holding one sub-group of its kind flattened into its parent.
The prompt's nested example (trains, cars, racks) has case 05's shape, which is why 06 exists.
Read by the reviewer on the raw answers, not built: at high effort three answers of eight set a
usage span above a device's lifespan and were refused; the builder could cut the span and list it.

Cost of these calls: USD 0.095 (0.009 for the seven reproduction calls, then 0.0165, 0.0173,
0.0057, 0.0103, 0.0128 and 0.0237 a run).

## Watch in normal use

- **A Web + edge generation, at the summary's "Device characteristics" check.** The answers'
  device figures drive the result and vary between calls on the same description (a sensor's
  manufacturing footprint from 0.1 to 5 kg, a controller's power from 5 to 15 W in the paid runs).
  Nothing in the code can catch it; the check is where a user does.
- **A generated web usage pattern of a fleet in service for years.** Its period is cut at the
  editor's 10 years, from its start, and the summary lists the cut: the last devices then outlive
  the web usage. With a stated growth, its comment gives both volumes ("1,000 a month on
  2027-01-01 as stated: 260 a month on 2023-01-01 at 40 % a year."): read it once on a real answer.
- **A description of a declining usage.** A negative growth is set to 0 and listed; whether the
  editor should accept one is asked in the plan (`#deployments-over-time`).
- **A provider failure ("The AI provider could not complete the request").** The user met one on
  2026-11-18. The application log now holds one line per failure, `AI provider failure: <kind>
  after <seconds> s` (timeout, HTTP status, unfinished answer, or the error's class), and nothing
  of the prompt or the answer. On that day the provider answered three of some forty calls with
  HTTP 429 "not enough capacity", dropped one, and took 50 and 72 s on two, past production's 45 s
  timeout: read the log before suspecting the code.
- **A description with groups inside groups**, at the summary's "Devices per group" check and its
  "Changes made to the AI answer" list. Measured under "Evidence": about half of the answers on
  the user's building are fully right, the others leaving out the outermost group (a floor is then
  deployed where a building is described); a container holding one sub-group of its kind is often
  flattened, with the right device counts.

## Parked

## Leads for the global review

### library-server-calls

- Added in the library: a server, a storage, a job and a server need in the edge-device-group
  integration fixture (`tests/integration_tests/integration_edge_device_group_base_class.py`),
  its reference `edge_device_group_system.json` regenerated; the test helper
  `_contain_in_one_usage_pattern` in `tests/usage/edge/test_recurrent_server_need.py`.
- Renamed: `RecurrentServerNeed.unitary_hourly_volume_per_usage_pattern` to
  `hourly_volume_per_usage_pattern`; the two job sites multiply it by the job weight only. The
  printed cell output of the library's `tutorial.ipynb` still shows the old name until the release
  refreshes it.
- The library's `CHANGELOG.md` `## [Unreleased]` already holds a `Fixed` and a `Changed` line for
  this lot: the end of the run adds the interface's entry only, and writes the library's no second
  time.
- **Predates this work, not acted on**: building a new `EdgeDeviceGroup` around an
  already-computed device left that device's `total_nb_of_units` stale until a later edit, in the
  reviewer's scratch run (`new_group.py` in the session scratchpad, gone after a reboot). The AI
  bootstrap builds every object before the system, so it is not reached here; whether the
  interface's own "add a group" path reaches it was not checked.

### scope-and-format

- Two `Scope` dataclasses: the service's (prompt file, schema) and the sandbox's in
  `ai_sandbox/run.py` (system prompt, validate, build), whose `_production` reaches into the
  service's table.
- The scope strings `"web"` and `"web_edge"` are literals in the view, the summary template, the
  tests and the sandbox; the scope-choice radio adds one more place.
- The view defaults an absent scope to `"web"`. Once the radio always posts the field, that
  default guards a request nothing real sends, against the plan's "no guard": settled in the lot
  `scope-choice`.
- `specs/architecture/layers-and-wrappers.html` says the response context carries "the
  description and summary metrics"; it now carries the scope too.
- `validate_tolerating_extras` changes the dict it is given (predates the run), and
  `ai_sandbox/run.py` depends on that before it builds.
- Misses seen in the measured sandbox runs (`ai_sandbox/runs/20261117-224245`, local and
  git-ignored) that the plan's record does not name, so the prompt was not edited for them: a
  group used as a country fleet (case 04, 17.7 million controllers), sensors running no edge
  function and so never deployed (case 03), a journey with no usage pattern (case 04). The paid
  runs of `edge-builder` read whether the shipped prompt still makes them.
- A replay of a run recorded under the removed sandbox scope `web_edge_hw` now raises `KeyError`.
  Local runs only.
- The map's `help` verb crashes (`comprehension-harness/map.mjs:571`: `fileURLToPath` is called
  with no import from `node:url`). Tooling, outside the feature, not fixed.

### edge-builder

- The hourly editor's duration limit was written in three places (the template's `max`, the
  script `usage_pattern_timeseries.js`, the preview view); the lot's review fix gives it one
  source. Check that no fourth literal is left.
- When the hourly editor opens on a stored duration above its limit, the script rewrites the
  value to the limit and shows an error, so a save that looks unchanged stores the cut value. The
  builder no longer emits such a period; a hand-imported one still meets it. Predates the run,
  left as found.
- A save from the hourly editor rewrites the form inputs as strings (`'38'`, `'60.0'`), so an
  unchanged save is a real change that recomputes. Predates the run.
- New private helpers in the bootstrap DSL module: `_weekly`, `_duration`, `_reserve`,
  `_deployment_spans`. New public constants: `WEB_YEAR_START`, `WEB_YEAR_END`,
  `MAX_DEFAULT_SPAN_YEARS`; the sandbox reads `WEB_YEAR_START`.
- Test helpers `HourlyEditorInputs`, `as_numbers` and `at_web_year_start` live in the narrative
  test file; the browser tests of `scope-choice` may want them.
- The Web only schema accepts a `start_date` on a usage pattern, which its prompt never offers.
- The shared start is the earliest date of anything dated: a dated usage pattern earlier than
  every deployment pulls the undated deployments with it. It matches the plan's clause and the
  prompt; the spec's rule speaks of "the earliest deployment start".
- Handwritten answer 04 deploys Germany at 75 a month from 2024-01-01; the prompt's rule now gives
  80 a month, the stated rate, from about 2024-03-09. The fleet narrative case asserts the 75.
- With fleet totals and no group (case 04), the summary's "Devices per group" check points at
  nothing the user can open.
- A replay of a sandbox run recorded before the format moved drops the removed fields and fails
  the device totals. Local, git-ignored runs only.

### scope-choice

- The scope strings `web` and `web_edge` are written out in the view's start route, the input
  template (two radios, four `data-ai-scope` blocks), the summary template, the stylesheet rule
  and the service's table. A third scope would touch all of them.
- The `checked_scopes` regex of the narrative tests depends on the order of the radio's
  attributes; it fails loudly if they move.
- No test posts an absent scope; an unknown one (`edge_only`) is tested and both reach the same
  lookup failure.
- The journey page's screen 6 describes the edge checks in a state row only, with no mock.
- The sandbox's `summary.md` states no impact of a call: its "total kg CO2e" column is the
  generated modeling's footprint. The disclosure's "below 1 g CO2-eq" was recomputed with
  `estimate_call` on each call's tokens and latency (0.21 to 0.40 g).

## End-of-run gate

Known red before the run's first product commit:

- Library: `tests/builders/hardware/test_boavizta_utils.py::test_web_api_and_package_dependency_calls_return_same_results`
  (`'2.5.0' != '2.6.0'`: the installed `boaviztapi` against the version the hosted API reports).
  Left as found: its fix is a dependency bump with the cloud-instance snapshot regenerated, not
  this feature's.
- Interface: `tests/unit_tests/adapters/test_ai_provider.py::test_evaluation_flash_delegates_to_bounded_adapter`
  (`'high' != 'low'`): the test still expected the flash entry to ignore an explicit effort, which
  commit `4c57a120` changed on purpose. Fixed at the global review in its own commit `00bbad94`,
  which names no piece: the test now reads the pin on a call with no effort and the explicit
  effort on a call that gives one.

The full gate, run on `f475b6c1` on 2026-11-18:

| Suite | Command | Result |
|---|---|---|
| JavaScript | `npm run build:js:dev`, then `npm run jest` | 304 passed, 24 suites |
| Python, no browser | `poetry run pytest tests --ignore=tests/e2e -q` | 1201 passed, 6 xfailed |
| Browser, AI bootstrap | `poetry run pytest tests/e2e/test_ai_bootstrap.py -q` | 7 passed |
| Browser, the rest | `poetry run pytest tests/e2e -n 4 --deselect tests/e2e/test_ai_bootstrap.py -q` | 165 passed, 1 xfailed, 2 failed |
| Library | `poetry run pytest -q` in `../e-footprint` | 1688 passed, 1 failed (the known `boaviztapi` test) |

The two browser failures reproduced alone and were the run's own: 
`tests/e2e/test_timeseries.py::TestTimeseriesValidation::test_modeling_duration_validation_with_day_and_month_units`
and `::test_edit_usage_pattern_with_month_unit_validation` typed 15 years, 150 months and 25
months as values above the hourly editor's limit, which the run raised to 20 years and 240
months. The product lost no validation; the tests' values and expected messages moved to the new
limit in `a99d2660`, nothing weakened, and the file then passed whole (5 passed). The full browser
suite was not run again after that commit, which touches that one test file. No test was flaky.

**After the user's answers, on `91489c99` (2026-11-18).** jest 306 passed; non-browser pytest 1215
passed, 6 xfailed; the whole browser suite 175 passed, 1 xfailed. The library's suite was not run
again: nothing changed in `../e-footprint` since `f9ad5688`.

## Spend

```
Usage snapshot: 591 requests · USD API-equivalent (tokens only) · rates 2026-09-30
Known subtotal: 40.8548; unpriced: 74; unattributed: 0
Known tokens: input 2,828; cached 85,081,296; write 2,260,232; output 569,225
Coverage: 0 source errors; 1 registered intervals missing measurements. Standard mode assumed for 0 requests.
  gate: 0.0058 (follow-up 0.0000); 2 requests; claude-haiku-5-5; effort medium
  implementer: 5.0594 (follow-up 0.0000); 92 requests; claude-fable-5-1, claude-haiku-5-5, claude-opus-5-5; effort high, medium
  implementer-easy: 0.2659 (follow-up 0.0000); 49 requests; claude-haiku-5-5; effort high
  implementer-hard: 10.7702 (follow-up 0.8499); 37 requests; claude-fable-5-1; effort high
  light: 0.0128 (follow-up 0.0000); 15 requests; claude-haiku-5-5; effort medium
  reviewer: 18.3912 (follow-up 8.6262); 303 requests; claude-opus-5-5; effort high
  reviewer-global: 6.3495 (follow-up 1.9032); 19 requests; claude-fable-5-1; effort high
  supervisor: 0.0000 (follow-up 0.0000); 74 requests; claude-fable-5-2; effort high
Unassigned-to-task overhead: 40.8548. No inference about completed-task quality or subscription limits.
  Unpriced: claude-fable-5-2: unknown model (74 requests)
```

The supervisor's 74 requests are unpriced, the ledger's rates not knowing `claude-fable-5-2`, so
the subtotal of USD 40.85 leaves them out. The paid sandbox calls are outside the ledger: twelve
calls, USD 0.019 (under "Evidence").

**After the run (2026-11-18, the fix and the coupling).** The same report, collected again:

```
Usage snapshot: 823 requests · USD API-equivalent (tokens only) · rates 2026-09-30
Known subtotal: 52.7979; unpriced: 145; unattributed: 0
  implementer: 8.9775 (follow-up 1.3023); 161 requests; claude-fable-5-1, claude-haiku-5-5, claude-opus-5-5; effort high, medium
  reviewer: 26.4162 (follow-up 14.6897); 395 requests; claude-opus-5-5; effort high
  supervisor: 0.0000 (follow-up 0.0000); 145 requests; claude-fable-5-2; effort high
```

The fix and the coupling cost USD 11.94 of sub-agents (the other roles unchanged), the supervisor
still unpriced, and USD 0.095 of paid sandbox calls.

**After the user's answers (2026-11-18).** Collected again: known subtotal USD 62.20 over 992
requests (implementer 12.77, reviewer 32.03, the other roles unchanged; the supervisor's 172
requests unpriced). Applying the answers and the editor fix cost USD 9.41 of sub-agents and no
paid call.
